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
import time

from .. import atlas, gitops, leaving, paths, worktree
from ..course import homework
from ..course import repo as course_repo


# Keyed by workspace root. One process serves one board, so in practice this
# holds one entry -- but a key that is not the workspace is a cache that answers
# about the wrong workspace the first time anything asks twice, and Atlas is a
# repository where "the wrong workspace" is several other people's afternoons.
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

    `run_push` commits the same scope; see `save_pathspec`.
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

    A person pressing a button, so it always runs: "build it" that quietly
    does nothing is a button you press twice. `homework.build` is the same
    compile `board writeup build` runs, in this process and on this session,
    and the record it writes to the session's `hw.json` is the one returned --
    including `pdf`, which a download needs, and the LaTeX tail, which a
    failure needs.
    """
    try:
        st = homework.status(repo.root, repo.state())
    except Exception:                                        # noqa: BLE001
        st = None
    if not st or not st.get("rel") or not st.get("name"):
        return {"ok": False,
                "detail": "this session has no write-up yet, so there is nothing "
                          "to build. The first `board writeup add` starts one."}
    try:
        homework.build(repo.root, repo.live, st)
    except OSError as exc:
        return {"ok": False, "set": st.get("name"), "detail": str(exc)}
    rec = homework.last_build(repo.live) or {"ok": False, "detail": "no record"}
    rec.setdefault("set", st.get("name"))
    return rec


def build_before_push(repo):
    """Compile the write-up, so what is committed is the document and not just
    its source -- only when its PDF is missing or older than the `.tex`.

    A pushed `.tex` carrying tonight's proof beside a `.pdf` from last week is
    worse than no PDF at all: it looks finished and is silently missing the
    exercise the evening was spent on. The compile is `homework.build`, the
    one `board writeup build` runs, and its `hw.json` is the record the board
    paints, so a LaTeX error appears on the iPad.
    """
    name = hw_needs_building(repo)
    if not name:
        return None
    try:
        st = homework.status(repo.root, repo.state())
        code, _pdf, out = homework.build(repo.root, repo.live, st)
    except Exception as exc:                                 # noqa: BLE001
        out, code = str(exc), 1
    return {"set": name, "ok": code == 0, "detail": out[-800:]}


def save_pathspec(root, top, only=None):
    """What a save from the workspace at `root` commits, as git pathspecs
    relative to `top`, the repository it is in.

    `(specs, refused)`. With no `only`, the workspace's own directory. With
    `only`, those paths -- each resolved against the working directory -- and
    `refused` names every one that is not inside the workspace, because a save
    made here commits here and nowhere else. Either way the tool and any
    workspace nested inside this one are excluded. NFS litter (`.nfs*`) is kept
    out by Atlas's root `.gitignore`, so no door commits it.

    AN EXCLUDE NAMES, LITERALLY, A DIRECTORY INSIDE ONE OF THE PATHS IT
    NARROWS. With an exclude outside them, or a wildcard one such as
    `**/.nfs*`, git 2.52's `add -A` adds no untracked file at all, and the save
    reports "nothing to commit" over a workspace full of new work.
    """
    real_top = os.path.realpath(top)
    real_root = os.path.realpath(root)

    def rel(path):
        r = os.path.relpath(os.path.realpath(path), real_top)
        return "." if r == os.curdir else r

    refused = []
    if only:
        specs = []
        for p in only:
            if paths.within(os.path.abspath(p), real_root):
                specs.append(rel(os.path.abspath(p)))
            else:
                refused.append(p)
    else:
        specs = [rel(real_root)]

    nested = [paths.TOOL]
    try:
        nested += [w["root"] for w in atlas.workspaces()]
    except OSError:
        pass
    narrowed = [os.path.join(real_top, s) for s in specs]
    for other in nested:
        real = os.path.realpath(other)
        if real == real_root or not paths.within(real, real_root):
            continue
        if any(real != n and paths.within(real, n) for n in narrowed):
            specs.append(":(exclude)" + rel(real))
    return specs, refused


def repo_top(root):
    """The repository the workspace at `root` is in, asked of git rather than
    derived by taking `dirname` of its git directory -- which is right for an
    ordinary clone and wrong for a linked worktree or a submodule."""
    try:
        p = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=root,
                           stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                           timeout=10)
        found = p.stdout.decode("utf-8", "replace").strip()
        if p.returncode == 0 and found:
            return found
    except (OSError, subprocess.TimeoutExpired):
        pass
    return root


def run_push(repo, message=None):
    """Commit and push, and record what happened.

    The work is the repository owner's. `gitops` adds no co-author trailer
    and neither does anything here -- history should credit the person who did
    the mathematics and nobody else.

    It commits THIS WORKSPACE and nothing else: `save_pathspec` is the
    pathspec, so the tool, every other workspace and NFS litter stay out of a
    commit named after this one. Everything uncommitted inside the workspace
    goes, because save means save. The commit message names the workspace.

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
    # line makes, on the same push, because this is the same push: a fixture
    # cut out of a transcript goes with it. See `tutorboard/leaving.py` for what it catches.
    #
    # NO OVERRIDE HERE, and that is the difference between this surface and the
    # command line. `board push --anyway` is a keyboard act; a button on a
    # tablet that waves a PHI fence through is the thing the fence is for. The
    # way past it from the iPad is to tell the tutor, which is a person deciding
    # and an assistant acting.
    phi = leaving.reason(repo.root)
    # And nothing a thread held at the cluster owns: `holds.refusal`, the same
    # check `board push` makes.
    if not phi:
        from .. import holds
        phi = holds.refusal(repo.root)
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

    # The workspace leads the message, and the commit is of the repository
    # the workspace is in, carrying only `save_pathspec`.
    said = message or gitops.SAVE
    where = atlas.identify(repo.root)
    if where and not said.startswith(where):
        said = "%s: %s" % (where, said)

    top = repo_top(repo.root)
    specs, _ = save_pathspec(repo.root, top)
    ok, out = gitops.save(top, specs, said)
    code = 0 if ok else 1

    record = {
        "ok": code == 0,
        "at": time.time(),
        "iso": time.strftime("%Y-%m-%d %H:%M:%S"),
        "workspace": where,
        "detail": out[-1200:],
    }
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
#   SCOPED TO THE WORKSPACE. Atlas's repository holds every workspace, and
#   `git log` at its root answers about all of them. A turn about TRD-EHR told about PSYCH-ASR's afternoon is a turn that will
#   try to teach it.
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
            # makes this answer about one workspace in a repository that may
            # hold several.
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

        theirs = uncommitted(repo.root)
        if theirs is not None:
            # COUNTED AFTER THE FILTER, so the number and the list are about
            # the same thing. "2 files are uncommitted" over a list of one is
            # a turn wondering what the other one was.
            value["files"] = len(theirs)
            value["uncommitted"] = theirs[:BESIDE_FILES]

    _BESIDE[key] = (now, value)
    return value


def uncommitted(root, paths=None):
    """Uncommitted paths under `paths` (default: the workspace), relative to `root`.

    None where git cannot be asked. `live/` is left out: it is the board's own
    scratch -- cards, ink, state -- and listing it as changed work would make
    every answer open with what the board itself just did.
    """
    try:
        # `git status --porcelain` prints paths relative to the GIT ROOT, not
        # to the directory it was run in -- so in a repository holding several
        # workspaces every name comes back with the workspace's own directory
        # on the front of it. A turn in PSYCH-ASR told about
        # `projects/PSYCH-ASR/notes/ch04.md` has to strip a prefix to find a
        # file that is right there beside it.
        top = root
        tp = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                            cwd=root, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, timeout=10)
        if tp.returncode == 0:
            said = tp.stdout.decode("utf-8", "replace").strip()
            if said:
                top = said
        spec = [os.path.join(root, p) if not os.path.isabs(p) else p
                for p in (paths or [root])]
        p = subprocess.run(
            ["git", "--no-optional-locks", "status", "--porcelain", "--"] + spec,
            cwd=root, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if p.returncode != 0:
        return None
    names = []
    for line in p.stdout.decode("utf-8", "replace").splitlines():
        if not line.strip():
            continue
        # `XY <path>`, and a rename is `XY <old> -> <new>`.
        rel = line[3:].strip().strip('"')
        if " -> " in rel:
            rel = rel.split(" -> ", 1)[1]
        try:
            # Both sides resolved: git answers the top with symlinks taken out,
            # and a Mac's temporary and home paths run through one (`/var` is
            # `/private/var`), so a raw `root` puts `../../private` on the front.
            here = os.path.relpath(os.path.realpath(os.path.join(top, rel)),
                                   os.path.realpath(root))
        except ValueError:
            here = rel
        names.append(here)
    scratch = os.path.relpath(course_repo.session_dir(root), root)
    return [n for n in names
            if not n.startswith(scratch + os.sep) and n != scratch]
