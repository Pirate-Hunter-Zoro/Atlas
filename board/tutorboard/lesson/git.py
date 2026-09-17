"""The repository underneath a lesson: whether it has anything uncommitted, and
what happens when somebody presses save.

Saving compiles the write-up first, because a LaTeX error found at push time
is found by the student, on the board, at the moment they were trying to
leave.
"""

import glob as _glob
import json
import os
import subprocess
import sys
import time

from .. import atlas, leaving, paths, worktree
from ..course import homework


# Keyed by workspace root. One process serves one board, so in practice this
# holds one entry -- but a key that is not the workspace is a cache that answers
# about the wrong workspace the first time anything asks twice, and this now
# lives in a repository where "the wrong workspace" is nine other people's
# afternoons.
_DIRTY = {}
DIRTY_TTL = 8.0


def repo_dirty(repo):
    """How many files are uncommitted IN THIS WORKSPACE, or None if it cannot be told.

    This exists so the board can show that there is something to save. Leaving a
    session is silent -- a lid closes, an app is swiped away -- and the student
    should be able to see, before they go, that going now loses something.

    **Scoped to the workspace**, which is the whole of what the move to one
    repository changed here. `git status --porcelain` at the root of a monorepo
    answers about every workspace in it, so a board on Galois Theory would show
    an unsaved-work badge because somebody's afternoon on TRD-EHR is
    uncommitted -- a warning about work the person looking at it cannot see,
    attached to the button that would then commit it. The pathspec is the fix
    and it is one argument.

    `run_push` is deliberately NOT scoped the same way: see its own note.
    """
    now = time.time()
    key = os.path.realpath(repo.root)
    hit = _DIRTY.get(key)
    if hit and hit[1] is not None and now - hit[0] < DIRTY_TTL:
        return hit[1]
    value = None
    if worktree.git_dir(repo.root):
        try:
            # `--no-optional-locks`, because this is a BADGE. An ordinary
            # `git status` takes `.git/index.lock` to write back the index it
            # just refreshed -- a kindness to the next command, and the wrong
            # trade entirely for a poll that runs every eight seconds in a
            # repository whose slate pages are being rewritten while somebody
            # draws on them. Killed at the timeout below, it leaves the lock
            # behind and closes every route to a commit in here. It also means
            # the badge keeps answering while somebody else holds the lock,
            # instead of going blank at the moment it has most to say.
            p = subprocess.run(["git", "--no-optional-locks", "status",
                                "--porcelain", "--", repo.root], cwd=repo.root,
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                               timeout=10)
            if p.returncode == 0:
                lines = [l for l in p.stdout.decode("utf-8", "replace").splitlines()
                         if l.strip()]
                value = len(lines)
        except (OSError, subprocess.TimeoutExpired):
            value = None
    _DIRTY[key] = (now, value)
    return value


def hw_needs_building(repo):
    """The sitting's problem set, if its PDF is missing or older than its source.

    Cheap: two `stat` calls behind a lookup the board already does every payload.
    Returns the set's name, or None when there is nothing to build -- no problem
    sets in this repository, none bound to this sitting, or a PDF already newer
    than the `.tex`.
    """
    try:
        st = homework.status(repo.root, repo.state())
    except Exception:                                        # noqa: BLE001
        return None
    if not st or not st.get("rel") or not st.get("name"):
        return None
    tex_path = os.path.join(repo.root, st["rel"])
    if not os.path.exists(tex_path):
        return None
    pdf = homework.compiled_pdf(repo.root, tex_path)
    if pdf and os.path.getmtime(pdf) >= os.path.getmtime(tex_path):
        return None
    return st["name"]


def run_hw_build(repo):
    """Compile the write-up because somebody asked, and hand back the record.

    `build_before_push` compiles only when the PDF is stale, which is right for
    a push -- there is no reason to spend a minute of LaTeX on a document that is
    already current. This one is a person pressing a button, and it always runs:
    "build it" that quietly does nothing is a button you press twice.

    The record comes back off `hw.json` rather than being reconstructed here, so
    the board is told exactly what the CLI recorded -- including `pdf`, which is
    what a download needs, and the LaTeX tail, which is what a failure needs.
    """
    try:
        st = homework.status(repo.root, repo.state())
    except Exception:                                        # noqa: BLE001
        st = None
    if not st or not st.get("rel") or not st.get("name"):
        return {"ok": False,
                "detail": "no problem set is bound to this sitting, so there is "
                          "nothing to write up. `board hw use <set>` names one."}
    cli = os.path.join(paths.TOOL, "bin", "board")
    if not os.path.exists(cli):
        return {"ok": False, "detail": "the board CLI is not where it should be"}
    try:
        # stdin=DEVNULL: a board detached by `board start`, or started by
        # launchd, has fd 0 closed, and a python3 that inherits that dies with
        # "can't initialize sys standard streams" before it runs a line. See
        # the note in `server/spawn.py`.
        p = subprocess.run([sys.executable, cli, "hw", "build"], cwd=repo.root,
                           stdin=subprocess.DEVNULL,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           timeout=300)
        out = p.stdout.decode("utf-8", "replace").strip()
    except (subprocess.TimeoutExpired, OSError) as exc:
        return {"ok": False, "set": st.get("name"), "detail": str(exc)}
    try:
        with open(os.path.join(repo.live, "hw.json"), "r", encoding="utf-8") as fh:
            rec = json.load(fh)
    except (OSError, ValueError):
        rec = {"ok": False, "set": st.get("name"), "detail": out[-1600:]}
    rec.setdefault("set", st.get("name"))
    return rec


def build_before_push(repo):
    """Compile the write-up, so what is committed is the document and not just
    its source.

    An exercise is finished when it is typeset, not when it is agreed: the point
    of the hour is the piece of mathematics. Compiling it was a step the tutor had
    to remember at the end of a turn that had already delivered its card -- and
    sessions end by being abandoned far more often than they end tidily. What got
    pushed was then a `.tex` carrying tonight's proof beside a `.pdf` from last
    week that does not, which is worse than no PDF at all: it looks finished and
    is silently missing the exercise the evening was spent on.

    The compile is `board hw build`, the same one the tutor would run, so there is
    one way of building and one `hw.json` -- which the board is already painting,
    so a LaTeX error appears on the iPad rather than in a log nobody is reading.
    """
    name = hw_needs_building(repo)
    if not name:
        return None
    cli = os.path.join(paths.TOOL, "bin", "board")
    if not os.path.exists(cli):
        return None
    try:
        # stdin=DEVNULL: a board detached by `board start`, or started by
        # launchd, has fd 0 closed, and a python3 that inherits that dies with
        # "can't initialize sys standard streams" before it runs a line. See
        # the note in `server/spawn.py`.
        p = subprocess.run([sys.executable, cli, "hw", "build"], cwd=repo.root,
                           stdin=subprocess.DEVNULL,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           timeout=180)
        out = p.stdout.decode("utf-8", "replace").strip()
        code = p.returncode
    except (subprocess.TimeoutExpired, OSError) as exc:
        out, code = str(exc), 1
    return {"set": name, "ok": code == 0, "detail": out[-800:]}


def other_dirty_workspaces(repo):
    """Which OTHER workspaces have uncommitted work right now.

    There is one repository, so a save commits the whole of it -- and the person
    tapping save is looking at one workspace and thinking about one afternoon.
    This is what turns that from a surprise into a sentence on the card: "also
    saved: research/TRD-EHR, projects/Paper-Writer". Naming them is the whole
    point; a save that quietly swept two other projects' work into a commit
    titled after a Galois Theory lesson is a commit nobody can find again.
    """
    out = []
    try:
        for w in atlas.workspaces():
            if paths.same_dir(w["root"], repo.root):
                continue
            p = subprocess.run(["git", "--no-optional-locks", "status",
                                "--porcelain", "--", w["root"]],
                               cwd=w["root"], stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL, timeout=10)
            if p.returncode == 0 and p.stdout.strip():
                out.append(w["id"])
    except (OSError, subprocess.TimeoutExpired):
        return []
    return out


def run_push(repo, message=None):
    """Commit and push, and record what happened.

    The work is the repository owner's. The script carries no co-author trailer
    and neither does anything here -- history should credit the person who did
    the mathematics and nobody else.

    It commits the whole tree on purpose: **save** means save, and a save that
    left the afternoon's code behind because it was not the lesson would be the
    wrong kind of clever. That was already true when a workspace was its own
    clone; with one repository it means MORE, because the whole tree is now
    every workspace. So two things are different and neither of them is the
    behaviour:

    * the commit message NAMES THE WORKSPACE the save was tapped in, because
      2,061 commits called "lesson complete" are not a history;
    * the record names every other workspace that had work in it, so the card
      says what else went along rather than leaving it to be discovered.

    What it still will not do is commit into an operation somebody is part-way
    through. A rebase or a merge outstanding means a terminal in this repository
    has its own plan for the next commit, and a tap on an iPad is not an
    instruction to walk over it -- so the tap says what is in the way instead,
    on the board, where the person who tapped is looking. That guard reads the
    REPOSITORY's git directory now, not the workspace's, which is the same
    question asked one level up.
    """
    busy = worktree.busy_reason(repo.root)
    if busy:
        record = {
            "ok": False,
            "at": time.time(),
            "iso": time.strftime("%Y-%m-%d %H:%M:%S"),
            "detail": ("nothing was committed: %s in this repository, so a "
                       "commit now would land in the middle of it. Nothing has "
                       "been lost -- finish or abort that in the terminal and "
                       "press save again." % busy),
        }
        with open(os.path.join(repo.live, "push.json"), "w", encoding="utf-8") as fh:
            json.dump(record, fh, indent=2)
        return record
    # AND NOTHING THAT REACHES FOR SESSION CONTENT. The same check the command
    # line makes, on the same push, because this is the same push: a tap on save
    # commits the whole repository and a fixture cut out of a transcript goes
    # with it. See `tutorboard/leaving.py` for what it catches.
    #
    # NO OVERRIDE HERE, and that is the difference between this surface and the
    # command line. `board push --anyway` is a keyboard act; a button on a
    # tablet that waves a PHI fence through is the thing the fence is for. The
    # way past it from the iPad is to tell the tutor, which is a person deciding
    # and an assistant acting.
    phi = leaving.reason(repo.root)
    if phi:
        record = {
            "ok": False,
            "at": time.time(),
            "iso": time.strftime("%Y-%m-%d %H:%M:%S"),
            "detail": phi,
        }
        with open(os.path.join(repo.live, "push.json"), "w", encoding="utf-8") as fh:
            json.dump(record, fh, indent=2)
        return record
    # A lock left behind by a git that was killed is not an operation to respect;
    # it is rubbish, and until this it closed the only door the person tapping
    # has. Git's own answer -- "remove the file manually to continue" -- is not
    # an instruction anybody can follow from an iPad, and it was the entire
    # contents of a red banner on 10 September while the work sat uncommitted.
    lock_verdict, lock_said = worktree.lock_reason(repo.root)
    cleared = None
    if lock_verdict == "held":
        record = {
            "ok": False,
            "at": time.time(),
            "iso": time.strftime("%Y-%m-%d %H:%M:%S"),
            "detail": "nothing was committed: " + lock_said,
        }
        with open(os.path.join(repo.live, "push.json"), "w", encoding="utf-8") as fh:
            json.dump(record, fh, indent=2)
        return record
    if lock_verdict == "stale":
        cleared = worktree.clear_stale_lock(repo.root)
    # The write-up is part of the work, so it is part of the commit. Only when it
    # is actually out of date, so an ordinary save in the middle of a lesson
    # costs nothing.
    built = build_before_push(repo)

    # Said before the commit, because afterwards there is nothing left to
    # compare against -- and this is the sentence the card needs.
    also = other_dirty_workspaces(repo)

    # The workspace leads the message. `save-and-push.sh` lives with the tool
    # now, one copy for the one repository, and it is run FROM THE REPOSITORY
    # ROOT: a push is a push of the repository and pretending otherwise from a
    # subdirectory is how a commit ends up with half of what somebody meant.
    said = message or "lesson complete"
    where = atlas.identify(repo.root)
    if where and not said.startswith(where):
        said = "%s: %s" % (where, said)

    # The repository THIS WORKSPACE is in, asked of git rather than derived by
    # taking `dirname` of its git directory -- which is right for an ordinary
    # clone and wrong for a linked worktree or a submodule, where the git
    # directory lives somewhere else entirely.
    #
    # ITS OWN NAME FOR THE ANSWER. This read `said` as its scratch variable --
    # the commit MESSAGE, built three lines above -- so every save from the
    # board committed with the absolute path of the repository as its subject
    # and the workspace's name nowhere in it. A message is not a place.
    top = repo.root
    try:
        p = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=repo.root,
                           stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                           timeout=10)
        found = p.stdout.decode("utf-8", "replace").strip()
        if p.returncode == 0 and found:
            top = found
    except (OSError, subprocess.TimeoutExpired):
        pass

    # ONE copy of the script, and the working directory is what tells it which
    # repository to commit. A workspace has no `scripts/` of its own any more --
    # there is one repository and the tool's copy is the only copy -- and the
    # script derives its root from `pwd`, not from where it is installed. That
    # distinction is not pedantry: for about an hour it derived the root from its
    # own location instead, and a test that taps save on a throwaway repository
    # committed the real Atlas three times.
    script = os.path.join(paths.TOOL, "scripts", "save-and-push.sh")
    if os.path.exists(script):
        cmd = ["bash", script, said]
    else:
        cmd = ["bash", "-c",
               'set -e; export GIT_TERMINAL_PROMPT=0; git add -A; '
               'git diff --cached --quiet || git commit -m "$1"; git push'
               , "_", said]
    try:
        p = subprocess.run(cmd, cwd=top, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=180)
        out = p.stdout.decode("utf-8", "replace").strip()
        code = p.returncode
    except subprocess.TimeoutExpired:
        out, code = "timed out after 3 minutes -- is a credential prompt waiting?", 1
    except OSError as exc:
        out, code = str(exc), 1

    record = {
        "ok": code == 0,
        "at": time.time(),
        "iso": time.strftime("%Y-%m-%d %H:%M:%S"),
        "workspace": where,
        "detail": out[-1200:],
    }
    if also:
        # Not a warning and not a failure. One repository, one push, and this
        # is the half of it the person tapping could not see.
        record["also"] = also
        record["detail"] = ("this is one repository, so the save also carried "
                            "uncommitted work in: " + ", ".join(also) + "\n\n"
                            + record["detail"])
    if cleared:
        record["cleared_lock"] = True
        record["detail"] = cleared + "\n" + record["detail"]
    if built:
        # Said on the board, not only in a log. A push that quietly shipped a
        # stale PDF because LaTeX failed is the exact silence this exists to end.
        record["built"] = built["set"]
        record["built_ok"] = built["ok"]
        if not built["ok"]:
            record["detail"] = (
                "the write-up did not compile, so its PDF is behind the source "
                "that was pushed:\n" + built["detail"] + "\n\n" + record["detail"])
    with open(os.path.join(repo.live, "push.json"), "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=2)
    return record


# ---------------------------------------------------------------------------
# what somebody did while the board was not looking
# ---------------------------------------------------------------------------
#     "I want to be able to pop open my laptop and code up something and have
#      the tutor see that if it pertains to whatever project we're in."
#
# Every turn is a cold turn -- `session_turns: 1`, a fresh `claude -p` reading
# `board brief` off disk -- so the briefing is the only place this can go. A
# tutor that has just been told what changed can teach the thing that changed;
# one that has not will cheerfully explain a function somebody rewrote at lunch.
#
# TWO RULES, and the second is the one that matters.
#
#   SCOPED TO THE WORKSPACE. There is one repository holding nine of them now,
#   and `git log` at its root answers about all nine. A turn about Galois Theory
#   told about PSYCH-ASR's afternoon is a turn that will try to teach it.
#
#   NAMED AS THE PERSON'S WORK, NEVER THE TUTOR'S. A turn that mistakes a commit
#   somebody made on their laptop for something it did itself will report having
#   done work it has not done, and that is the worst failure this board has: it
#   is undetectable from the outside, it is confidently stated, and it makes
#   every other thing the tutor says less believable. The wording below says
#   whose work it is three times, in three different ways, on purpose.
#
# NOT THE DIFF. A briefing is about 22k tokens and it stays that way. Subjects,
# filenames, and a count -- enough to know what to go and read, which is what a
# turn needs, and nothing that grows with the size of an afternoon's work.

_BESIDE = {}
BESIDE_TTL = 20.0

# How many commits and how many filenames are worth saying. Past these it is the
# COUNT that is the fact -- "eleven commits" tells a turn what it needs, and the
# eleventh subject does not.
BESIDE_COMMITS = 8
BESIDE_FILES = 12

# The furthest back this ever looks, whatever the sitting says. A lecture opened
# a fortnight ago and left open is the ordinary case on this board, and a
# fortnight of somebody's commits is not news, it is a changelog.
BESIDE_WINDOW = 3 * 86400


def _seen_until(repo):
    """The moment the tutor's knowledge of this workspace stops.

    The newest card it wrote, because a card is the tutor saying something and
    therefore the last point at which it certainly knew the state of the world.
    Failing that the sitting's own opening. Either way capped at
    `BESIDE_WINDOW`, so what comes back is news rather than history.
    """
    newest = 0
    try:
        for name in os.listdir(repo.cards):
            if not name.endswith((".md", ".markdown", ".tex")):
                continue
            try:
                newest = max(newest, os.path.getmtime(
                    os.path.join(repo.cards, name)))
            except OSError:
                continue
    except OSError:
        newest = 0

    if not newest:
        said = (repo.state() or {}).get("opened") or ""
        for shape in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
            try:
                newest = time.mktime(time.strptime(said, shape))
                break
            except (ValueError, OverflowError):
                continue

    floor = time.time() - BESIDE_WINDOW
    return max(newest or floor, floor)


def beside_the_lesson(repo):
    """What somebody did to THIS workspace that the tutor has not been told.

    `{"commits": [...], "uncommitted": [...], "files": n, "since": t}` or None
    when this is not a git repository. Cached, because the payload is polled
    four times a second and this is two `git` calls.
    """
    now = time.time()
    key = os.path.realpath(repo.root)
    hit = _BESIDE.get(key)
    if hit and now - hit[0] < BESIDE_TTL:
        return hit[1]

    value = None
    if worktree.git_dir(repo.root):
        since = _seen_until(repo)
        value = {"since": since, "commits": [], "uncommitted": [], "files": 0}
        try:
            # SCOPED BY PATHSPEC, not filtered afterwards. The pathspec is what
            # makes this answer about one workspace in a repository that holds
            # nine.
            p = subprocess.run(
                ["git", "--no-optional-locks", "log",
                 "--since=@%d" % int(since), "--no-merges",
                 "--pretty=%at%x00%s", "--", repo.root],
                cwd=repo.root, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, timeout=10)
            if p.returncode == 0:
                for line in p.stdout.decode("utf-8", "replace").splitlines():
                    at, _, subject = line.partition("\0")
                    if not subject.strip():
                        continue
                    try:
                        when = int(at)
                    except ValueError:
                        when = 0
                    value["commits"].append({"at": when,
                                             "subject": subject.strip()[:100]})
        except (OSError, subprocess.TimeoutExpired):
            pass

        try:
            # `git status --porcelain` prints paths relative to the GIT ROOT,
            # not to the directory it was run in -- so in a repository holding
            # nine workspaces every name comes back with the workspace's own
            # directory on the front of it. A turn in Galois-Theory told about
            # `courses/Galois-Theory/notes/ch04.tex` has to strip a prefix to
            # find a file that is right there beside it.
            top = repo.root
            tp = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                                cwd=repo.root, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, timeout=10)
            if tp.returncode == 0:
                said = tp.stdout.decode("utf-8", "replace").strip()
                if said:
                    top = said
            p = subprocess.run(
                ["git", "--no-optional-locks", "status", "--porcelain",
                 "--", repo.root],
                cwd=repo.root, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, timeout=10)
            if p.returncode == 0:
                names = []
                for line in p.stdout.decode("utf-8", "replace").splitlines():
                    if not line.strip():
                        continue
                    # `XY <path>`, and a rename is `XY <old> -> <new>`.
                    rel = line[3:].strip().strip('"')
                    if " -> " in rel:
                        rel = rel.split(" -> ", 1)[1]
                    try:
                        here = os.path.relpath(os.path.join(top, rel), repo.root)
                    except ValueError:
                        here = rel
                    names.append(here)
                # THE LESSON'S OWN SCRATCH IS NOT SOMEBODY'S WORK. `live/` is
                # where the board writes cards, ink and state while a sitting is
                # running; reporting it as "they changed these files" would make
                # every turn open with a list of what the board itself just did.
                theirs = [n for n in names
                          if not n.startswith("live" + os.sep) and n != "live"]
                # COUNTED AFTER THE FILTER, so the number and the list are about
                # the same thing. "2 files are uncommitted" over a list of one is
                # a turn wondering what the other one was.
                value["files"] = len(theirs)
                value["uncommitted"] = theirs[:BESIDE_FILES]
        except (OSError, subprocess.TimeoutExpired):
            pass

    _BESIDE[key] = (now, value)
    return value
