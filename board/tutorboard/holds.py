"""holds.py -- a sitting held at the cluster, coached on the glass.

The owner sometimes writes code beside the data. The coach stays on the Mac and
the card still lands on the iPad; the step's check runs on the cluster, because
it needs the rows. Four files carry it, all under the workspace's `relay/`:

    relay/holds/<thread>.json        the cluster's: this thread's files are its
    relay/reports/check-<t>-<n>.json the cluster's: step n's check, RELAY: lines
    relay/coach/<thread>.md          the Mac's: the coach's reply to the step

WHILE A HOLD LASTS, THE THREAD'S `files` ARE THE CLUSTER'S. The Mac refuses to
commit them (`refusal`, which `board push` and the save button ask), and the
relay's pass pulls under the owner's uncommitted edits (`sync`) because nothing
upstream touches those files. So a pull on either side never conflicts.

`board send` is the owner's one command per step: commit the thread's changed
files as `<thread>: step`, run the thread's `check` here, commit its report,
push both, and print the coach's reply when it lands. On the Mac the pull that
carries a check report drops a `[coach]` line (`wake`), the woken turn writes
the next card, and `board coach` writes the same text to `relay/coach/` and
pushes it.

PURE where it can be: `validate_hold` and `refused_writes` take what they need
and touch nothing, beside `jobs.validate`.

Standard library only, like everything else.
"""

import json
import os
import re
import subprocess
import time

from . import jobs
from .course import threads as course_threads

HOLDS = "holds"
COACH = "coach"
CHECK_PREFIX = "check-"

# The Mac's pull cadence while any hold stands. A step's round trip is this,
# a turn, and a push back: a minute or two.
POLL_SECONDS = 20

# How long `board send` waits for the coach's reply, and how often it looks.
WAIT_SECONDS = 180
WAIT_EVERY = 10

# A check runs on the owner's node, in their terminal. Half an hour is a check
# that is really a job, and a job goes through `board job`.
CHECK_SECONDS = 30 * 60

MAX_LINES = 40
MAX_LINE = 300
RELAY_LINE = re.compile(r"^RELAY:\s?(.*)$")
# The exception type of a crash, from a traceback's last line. Only the type:
# the message after it can print a value.
CRASH_LINE = re.compile(r"^([A-Za-z_][\w.]*(?:Error|Exception|Interrupt|Exit))\b")
COACH_HEAD = re.compile(r"^<!-- coach (\S+) step (\d+) -->\s*$")


# ---------------------------------------------------------------------------
# where things are
# ---------------------------------------------------------------------------
def holds_dir(root):
    return os.path.join(root, jobs.RELAY, HOLDS)


def hold_path(root, tid):
    return os.path.join(holds_dir(root), tid + ".json")


def coach_path(root, tid):
    return os.path.join(root, jobs.RELAY, COACH, tid + ".md")


def check_id(tid, n):
    return "%s%s-%d" % (CHECK_PREFIX, tid, n)


def is_check(report_id):
    """Is this report a step's check rather than a request's? Item 4's wake
    asks this, so a check report wakes `[coach]` and never `[job]`."""
    return str(report_id or "").startswith(CHECK_PREFIX)


def holds(root):
    """`{thread: hold}` for every hold standing in this workspace."""
    out = {}
    for rec in jobs._read_json_dir(holds_dir(root)):
        tid = str(rec.get("thread") or rec.get("id") or "")
        if tid:
            out[tid] = rec
    return out


def checks(root, tid):
    """`[report]` of this thread's step checks, oldest first."""
    pat = re.compile(r"^%s%s-(\d+)$" % (re.escape(CHECK_PREFIX), re.escape(tid)))
    got = []
    for rid, rep in jobs.reports(root).items():
        m = pat.match(rid)
        if m:
            got.append((int(m.group(1)), rep))
    return [r for _, r in sorted(got, key=lambda x: x[0])]


def next_step(root, tid):
    done = checks(root, tid)
    return (int(done[-1].get("step") or 0) + 1) if done else 1


def held_anywhere(roots):
    """Does any of these workspaces have a hold standing? The Mac's pull runs
    every `POLL_SECONDS` while one does."""
    return any(holds(r) for r in roots or [])


def poll_seconds(roots, usual):
    """The Mac's pull cadence: `POLL_SECONDS` while a hold stands, else `usual`."""
    return POLL_SECONDS if held_anywhere(roots) else usual


def owned(root):
    """Workspace-relative paths the cluster writes here right now: its reports,
    exports and holds, and every held thread's files. The relay's pass treats
    an edit or a commit under these as its own and anything else as a reason
    to skip."""
    out = [jobs.RELAY + "/reports", "exports", jobs.RELAY + "/" + HOLDS]
    clean, _ = course_threads.read(root)
    out.extend(sorted(held_files(clean, holds(root))))
    return out


# ---------------------------------------------------------------------------
# the validator: pure
# ---------------------------------------------------------------------------
def held_files(clean, standing):
    """`{path: thread}`: every path a standing hold covers. The hold's own list
    and the thread's current one, so a file added to the thread mid-hold is
    held too."""
    out = {}
    for tid, rec in sorted((standing or {}).items()):
        one = course_threads.thread(clean, tid) if clean else None
        for p in list(rec.get("files") or []) + list((one or {}).get("files") or []):
            rel = course_threads._rel(p)
            if rel:
                out.setdefault(rel, tid)
    return out


def _covering(rel, covered):
    for base, tid in covered.items():
        if rel == base or rel.startswith(base + "/"):
            return tid
    return None


def validate_hold(clean, tid, standing, tracked):
    """`(hold, problems)`: may this thread be held at the cluster? PURE.

        clean     the thread file, as `threads.validate` returns it
        tid       the thread to hold
        standing  `{thread: hold}`, the holds already standing
        tracked   workspace-relative paths tracked and unchanged at HEAD

    Refused whole, every problem at once.
    """
    problems = []
    one = course_threads.thread(clean, tid) if clean else None
    if not one:
        return None, ["thread %r is not one this workspace's thread file "
                      "declares" % (tid,)]
    if tid in (standing or {}):
        problems.append("thread %s is already held at the cluster, since %s. "
                        "`board release %s` ends it"
                        % (tid, _when((standing or {})[tid].get("held")), tid))
    if not one["files"]:
        problems.append("thread %s has no files, so there is nothing for the "
                        "cluster to hold" % tid)
    others = held_files(clean, dict((k, v) for k, v in (standing or {}).items()
                                    if k != tid))
    for f in one["files"]:
        by = _covering(f, others)
        if by:
            problems.append("%s is already held, by thread %s" % (f, by))
    if not one.get("check"):
        problems.append("thread %s has no check. The tutor writes one and names "
                        "it with `board thread check %s <script>`" % (tid, tid))
    elif one["check"] not in set(tracked or ()):
        problems.append("check %s is not tracked and unchanged at HEAD, so the "
                        "step would be checked by something nobody can read"
                        % one["check"])
    if problems:
        return None, problems
    return {"thread": tid, "files": list(one["files"]),
            "check": one["check"]}, []


def refused_writes(paths, clean, standing):
    """Every problem with a turn here writing `paths`, workspace-relative. PURE.

    A path under a held thread's files is the cluster's until the release.
    """
    covered = held_files(clean, standing)
    out = []
    for p in sorted(set(paths or ())):
        rel = course_threads._rel(p)
        tid = _covering(rel, covered) if rel else None
        if tid:
            out.append("%s belongs to thread %s, held at the cluster since %s. "
                       "A turn here does not write it; `board release %s` on "
                       "the cluster gives it back"
                       % (rel, tid, _when(standing[tid].get("held")), tid))
    return out


def _when(t):
    try:
        return time.strftime("%Y-%m-%d %H:%M", time.localtime(float(t)))
    except (TypeError, ValueError):
        return "an unknown time"


def refusal(root, only=None):
    """`""`, or why a commit from this machine would write a held file.

    Only on a machine without Slurm: on the cluster the held files are the
    owner's to commit. `only` narrows it to those paths, as `board push --`
    names them (absolute, or relative to the working directory).
    """
    if jobs.has_slurm():
        return ""
    standing = holds(root)
    if not standing:
        return ""
    clean, _ = course_threads.read(root)
    dirty = course_threads.dirty_of(root)
    if only:
        real = os.path.realpath(root)
        want = []
        for p in only:
            r = os.path.relpath(os.path.realpath(os.path.abspath(p)), real)
            want.append("" if r == os.curdir else r)
        dirty = [d for d in dirty
                 if any(not w or d == w or d.startswith(w + "/") for w in want)]
    problems = refused_writes(dirty, clean, standing)
    if not problems:
        return ""
    return "nothing was committed: " + "; ".join(problems)


# ---------------------------------------------------------------------------
# git, on the cluster
# ---------------------------------------------------------------------------
def _git(top, *args, **kw):
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_ASKPASS="/bin/false")
    try:
        p = subprocess.run(["git"] + list(args), cwd=top, env=env,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           universal_newlines=True,
                           timeout=kw.get("timeout", 120))
    except (OSError, subprocess.SubprocessError) as exc:
        return 1, str(exc)
    return p.returncode, p.stdout or ""


def top_of(root):
    code, out = _git(root, "rev-parse", "--show-toplevel", timeout=10)
    return out.strip() if code == 0 else ""


def _dirty(top):
    """Repository-relative paths with uncommitted edits, untracked included."""
    code, out = _git(top, "status", "--porcelain", "-z", "--untracked-files=all")
    if code != 0:
        return None
    got, fields, i = [], out.split("\0"), 0
    while i < len(fields):
        entry = fields[i]
        i += 1
        if len(entry) < 4:
            continue
        got.append(entry[3:])
        if entry[0] in "RC" and i < len(fields):
            got.append(fields[i])
            i += 1
    return got


def sync(top):
    """Bring origin in under the owner's uncommitted edits. `(ok, said)`.

    `git rebase --autostash` onto the upstream: the owner's edits are set
    aside, the local commits replayed on origin, and the edits put back. That
    is safe only because nothing upstream touches an edited path, so that is
    checked first: a path both edited here and changed upstream stops the pull
    with nothing moved. A rebase that fails anyway is aborted, which puts the
    tree back as it was.
    """
    from . import worktree
    busy = worktree.busy_reason(top)
    if busy:
        return False, "%s, so nothing was pulled" % busy
    code, up = _git(top, "rev-parse", "--abbrev-ref", "@{upstream}", timeout=10)
    if code != 0:
        return True, "no upstream to pull from"
    remote = up.strip().split("/", 1)[0]
    code, out = _git(top, "fetch", "--quiet", remote)
    if code != 0:
        return False, "could not fetch %s: %s" % (remote, out.strip()[-300:])
    code, out = _git(top, "rev-list", "--count", "HEAD..@{upstream}")
    if code == 0 and out.strip() == "0":
        return True, "already current"
    code, out = _git(top, "diff", "--name-only", "-z", "HEAD...@{upstream}")
    if code != 0:
        return False, ("could not read what origin changes, so nothing was "
                       "pulled: %s" % out.strip()[-300:])
    incoming = set(x for x in out.split("\0") if x)
    dirty = _dirty(top)
    if dirty is None:
        return False, "git status failed, so nothing was pulled"
    clash = sorted(p for p in dirty if p in incoming)
    if clash:
        return False, ("origin changes %s, which %s uncommitted edits here, so "
                       "nothing was pulled. Commit or send them, then pull"
                       % (", ".join(clash[:6]),
                          "has" if len(clash) == 1 else "have"))
    stashed = _stashes(top)
    code, out = _git(top, "rebase", "--autostash", "--quiet", "@{upstream}",
                     timeout=300)
    if code != 0:
        _git(top, "rebase", "--abort")
        return False, ("the rebase onto origin stopped, so it was undone and "
                       "the tree is as it was: %s" % out.strip()[-300:])
    code, left = _git(top, "diff", "--name-only", "--diff-filter=U")
    if code != 0 or left.strip():
        return False, ("the edits set aside did not go back cleanly; they are "
                       "kept in `git stash list`: %s" % left.strip())
    # The other way an autostash fails to go back: `stash apply` refuses (a
    # file changed while the rebase ran), git still exits 0 and leaves no
    # conflict, and the edits sit in the stash, gone from the tree.
    after = _stashes(top)
    if (stashed is None or after is None or after > stashed
            or "resulted in conflicts" in out):
        return False, ("the edits set aside did not go back; they are kept in "
                       "`git stash list` (stash@{0}), so put them back with "
                       "`git stash pop` before the next pull")
    return True, "pulled origin under the edits here"


def _stashes(top):
    """How many entries `git stash list` holds, or None if git would not say."""
    code, out = _git(top, "stash", "list", timeout=20)
    if code != 0:
        return None
    return len([l for l in out.splitlines() if l.strip()])


def push(top):
    """Push the branch. A rejection is answered by one `sync` and one more try,
    never by force. `(ok, said)`."""
    code, branch = _git(top, "rev-parse", "--abbrev-ref", "HEAD", timeout=10)
    branch = branch.strip()
    code, up = _git(top, "rev-parse", "--abbrev-ref", "@{upstream}", timeout=10)
    if code != 0:
        return False, "%s has no upstream, so nothing was pushed" % branch
    remote = up.strip().split("/", 1)[0]
    said = ""
    for attempt in (1, 2):
        code, out = _git(top, "push", "--quiet", remote, "HEAD:" + branch,
                         timeout=180)
        if code == 0:
            return True, "pushed %s" % branch
        said = out.strip()[-300:]
        if attempt == 1:
            ok, why = sync(top)
            if not ok:
                return False, "the push was rejected and the pull failed: " + why
    return False, "the push failed: " + said


def _commit(top, rels, message):
    """Commit exactly `rels` (repository-relative), whatever else is staged.

    A path already removed (`git rm`, or a deleted file whose directory went
    with it) is not added: `--only` commits its removal from the index.
    """
    there = [r for r in rels if os.path.lexists(os.path.join(top, r))
             or os.path.isdir(os.path.dirname(os.path.join(top, r)))]
    if there:
        code, out = _git(top, "add", "-A", "--", *there)
        if code != 0:
            return False, out.strip()
    code, out = _git(top, "commit", "-q", "-m", message, "--only", "--", *rels)
    return code == 0, out.strip()


def _rel_top(top, root, rel):
    return os.path.relpath(os.path.join(os.path.realpath(root), rel),
                           os.path.realpath(top))


def _tracked(root):
    """Workspace-relative paths tracked and unchanged at HEAD."""
    tracked = set(jobs._git_lines(root, ["ls-files", "-z", "--", "."]))
    changed = set(jobs._git_lines(root, ["diff", "--name-only", "-z",
                                         "--relative", "HEAD", "--", "."]))
    return tracked - changed


def visible(root):
    """`""`, or the sentence saying git would not see a hold here."""
    rel = "%s/%s/x.json" % (jobs.RELAY, HOLDS)
    if jobs.ignored(root, rel):
        return ("git ignores %s in this workspace, so a hold would never reach "
                "the Mac. Add `!%s/%s/*.json` to %s after the rule that hides "
                "it." % (os.path.dirname(rel), jobs.RELAY, HOLDS,
                         os.path.join(root, ".gitignore")))
    return ""


# ---------------------------------------------------------------------------
# hold and release, on the cluster
# ---------------------------------------------------------------------------
def hold(root, tid, now=None):
    """Hold `tid` at the cluster: write the hold, commit it alone, push it.
    `(ok, lines)`."""
    if not jobs.has_slurm():
        return False, ["a hold is made in the cluster checkout, where the owner "
                       "writes the code; this machine has no Slurm"]
    hidden = visible(root)
    if hidden:
        return False, [hidden]
    top = top_of(root)
    if not top:
        return False, ["%s is not in a git repository" % root]
    ok, why = sync(top)
    if not ok:
        return False, ["nothing was held: " + why]
    clean, problems = course_threads.read(root)
    if problems:
        return False, problems
    rec, problems = validate_hold(clean, tid, holds(root), _tracked(root))
    if problems:
        return False, problems
    rec["held"] = round(float(now or time.time()), 3)
    target = hold_path(root, tid)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8") as fh:
        json.dump(rec, fh, indent=2, sort_keys=True)
        fh.write("\n")
    ok, out = _commit(top, [_rel_top(top, root, os.path.relpath(target, root))],
                      _message(root, "%s: held at the cluster" % tid))
    if not ok:
        os.remove(target)
        return False, ["the hold could not be committed: " + out]
    pushed, said = push(top)
    lines = ["%s is held at the cluster: its files are yours here, and the Mac "
             "refuses to write them until `board release %s`." % (tid, tid),
             "Files: " + ", ".join(rec["files"]),
             "After each step: board send"]
    if not pushed:
        lines.append("BUT IT IS NOT PUSHED YET (%s). `board send` pushes it "
                     "with the first step." % said)
    return pushed, lines


def release(root, tid):
    """End the hold: remove it, commit that alone, push. `(ok, lines)`."""
    standing = holds(root)
    if tid not in standing:
        return False, ["thread %s is not held%s" % (
            tid, "; held here: " + ", ".join(sorted(standing)) if standing
            else "")]
    clean, _ = course_threads.read(root)
    mine = held_files(clean, {tid: standing[tid]})
    left = [d for d in course_threads.dirty_of(root) if _covering(d, mine)]
    if left:
        return False, ["%s still %s uncommitted edits. `board send` them as a "
                       "step first, or commit them yourself; released, the Mac "
                       "may write those files." % (
                           ", ".join(left[:6]),
                           "has" if len(left) == 1 else "have")]
    top = top_of(root)
    ok, why = sync(top)
    if not ok:
        return False, ["nothing was released: " + why]
    rel = _rel_top(top, root, os.path.relpath(hold_path(root, tid), root))
    code, out = _git(top, "rm", "-q", "--", rel)
    if code != 0:
        return False, ["the hold could not be removed: " + out.strip()]
    ok, out = _commit(top, [rel], _message(root, "%s: released" % tid))
    if not ok:
        return False, ["the release could not be committed: " + out]
    pushed, said = push(top)
    lines = ["%s is released: the Mac may write its files again." % tid]
    if not pushed:
        lines.append("BUT IT IS NOT PUSHED YET: " + said)
    return pushed, lines


def _message(root, what):
    from . import atlas
    where = atlas.identify(root)
    return "%s: %s" % (where, what) if where else what


# ---------------------------------------------------------------------------
# the check, and `board send`
# ---------------------------------------------------------------------------
def relay_lines(text, names_phi=None):
    """`(lines, withheld)`: what a report may carry out of a program's output.

    Only lines behind `RELAY:`, prefix dropped, each through `relay.public`
    (control characters gone, an absolute or home path made `<path>`, cut to
    `MAX_LINE`), at most `MAX_LINES`. A line the lab's PHI policy flags is
    withheld and counted.
    """
    from . import relay
    out, withheld = [], 0
    for line in (text or "").splitlines():
        m = RELAY_LINE.match(line.rstrip("\r"))
        if not m:
            continue
        said = relay.public(m.group(1), names_phi, MAX_LINE)
        if said is None:
            withheld += 1
            continue
        if not said:
            continue
        if len(out) < MAX_LINES:
            out.append(said)
    return out, withheld


def crash_type(text):
    """The exception type a traceback ended on, or ""."""
    for line in reversed((text or "").strip().splitlines()):
        m = CRASH_LINE.match(line.strip())
        if m:
            return m.group(1).rsplit(".", 1)[-1]
    return ""


def check_argv(root, rel):
    path = os.path.join(root, rel)
    ext = os.path.splitext(rel)[1].lower()
    if ext == ".py":
        return ["python3", path]
    if ext == ".sh" or not os.access(path, os.X_OK):
        return ["bash", path]
    return [path]


def run_check(root, rel, run=subprocess.run, timeout=CHECK_SECONDS,
              names_phi=None):
    """Run the thread's check here, from the workspace root.

    `{exit, relay, withheld, crash, seconds}`. Nothing else of its output is
    kept: a check prints `RELAY:` lines for the report and anything else for
    the owner's own eyes, and that stays in this terminal.
    """
    t0 = time.time()
    try:
        p = run(check_argv(root, rel), cwd=root, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, universal_newlines=True,
                timeout=timeout)
        code, out, err = p.returncode, p.stdout or "", p.stderr or ""
    except subprocess.TimeoutExpired:
        code, out, err = 124, "", "TimeoutExpired"
    except OSError as exc:
        code, out, err = 127, "", type(exc).__name__
    lines, withheld = relay_lines(out, names_phi)
    got = {"exit": code, "relay": lines, "seconds": round(time.time() - t0, 1)}
    if withheld:
        got["withheld"] = withheld
    if code != 0:
        crash = crash_type(err)
        if crash:
            got["crash"] = crash
    return got


def _policy(root):
    try:
        from . import leaving
        return leaving.policy()
    except Exception:                                        # noqa: BLE001
        return None


def send(root, tid=None, wait=WAIT_SECONDS, say=print, run=subprocess.run,
         anyway=False, now=None):
    """`board send`: one step, checked here and sent to the coach. Exit code.

    1. Commit the thread's changed files as `<thread>: step`, as the owner.
    2. Run the thread's check; write `relay/reports/check-<thread>-<n>.json`
       and commit it alone.
    3. Push both, and wait up to `wait` seconds for the coach's reply.
    """
    if not jobs.has_slurm():
        say("board send: a step is sent from the cluster checkout, where the "
            "thread is held. This machine has no Slurm.")
        return 1
    standing = holds(root)
    if tid is None:
        if len(standing) != 1:
            say("board send: name the thread -- held here: %s"
                % (", ".join(sorted(standing)) or "none"))
            return 1
        tid = sorted(standing)[0]
    if tid not in standing:
        say("board send: thread %s is not held. `board hold %s` first."
            % (tid, tid))
        return 1
    top = top_of(root)
    ok, why = sync(top)
    if not ok:
        say("board send: nothing was sent: " + why)
        return 1
    clean, problems = course_threads.read(root)
    one = course_threads.thread(clean, tid) if clean else None
    if problems or not one:
        say("board send: the thread file does not declare %s: %s"
            % (tid, "; ".join(problems)))
        return 1
    if not one.get("check") or one["check"] not in _tracked(root):
        say("board send: thread %s's check %s is not tracked and unchanged at "
            "HEAD. Nothing was sent." % (tid, one.get("check") or "(none)"))
        return 1
    if not anyway:
        from . import leaving
        phi = leaving.reason(root)
        if phi:
            say("board send: " + phi)
            return 1

    mine = held_files(clean, {tid: standing[tid]})
    changed = sorted(d for d in course_threads.dirty_of(root)
                     if _covering(d, mine))
    if changed:
        ok, out = _commit(top, [_rel_top(top, root, c) for c in changed],
                          "%s: step" % tid)
        if not ok:
            say("board send: the step could not be committed: " + out)
            return 1
        say("committed %s: step (%s)" % (tid, ", ".join(changed)))
    else:
        say("no change under %s's files; sending the check alone" % tid)

    n = next_step(root, tid)
    say("running the check: %s" % one["check"])
    began = float(now or time.time())
    got = run_check(root, one["check"], run=run, names_phi=_policy(root))
    rep = {"id": check_id(tid, n), "kind": "check", "thread": tid, "step": n,
           "check": one["check"], "files": changed,
           "state": "completed" if got["exit"] == 0 else "failed",
           "ran": round(began, 3), "ended": round(time.time(), 3)}
    rep.update(got)
    target = os.path.join(jobs.reports_dir(root), rep["id"] + ".json")
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=2, sort_keys=True, ensure_ascii=False)
        fh.write("\n")
    ok, out = _commit(top, [_rel_top(top, root, os.path.relpath(target, root))],
                      "%s: check %d" % (tid, n))
    if not ok:
        say("board send: the check's report could not be committed: " + out)
        return 1
    for line in got["relay"]:
        say("  RELAY: " + line)
    say("check %s, exit %d%s" % (rep["state"], got["exit"],
                                 ", " + got["crash"] if got.get("crash") else ""))
    pushed, said = push(top)
    if not pushed:
        say("board send: step %d is committed here and NOT pushed: %s. "
            "`board send` again pushes it." % (n, said))
        return 1
    say("step %d sent." % n)
    if wait <= 0:
        return 0
    say("waiting up to %d seconds for the coach..." % wait)
    text = await_reply(root, tid, n, wait)
    if text is None:
        say("no reply in %d seconds. It lands on the board; `board send "
            "--reply %s` prints it here." % (wait, tid))
        return 0
    say("")
    say(text)
    return 0


# ---------------------------------------------------------------------------
# the coach's reply
# ---------------------------------------------------------------------------
def parse_coach(text):
    """`(thread, step, body)` out of a `relay/coach/` file, or `(None, 0, "")`."""
    lines = (text or "").splitlines()
    m = COACH_HEAD.match(lines[0]) if lines else None
    if not m:
        return None, 0, ""
    return m.group(1), int(m.group(2)), "\n".join(lines[1:]).strip()


def coach_text(tid, n, body):
    return "<!-- coach %s step %d -->\n%s\n" % (tid, n, body.strip())


def upstream_reply(root, tid):
    """`(step, body)` of the reply on origin, fetched now. `(0, "")` if none."""
    top = top_of(root)
    code, up = _git(top, "rev-parse", "--abbrev-ref", "@{upstream}", timeout=10)
    if code != 0:
        return 0, ""
    _git(top, "fetch", "--quiet", up.strip().split("/", 1)[0])
    rel = _rel_top(top, root, os.path.relpath(coach_path(root, tid), root))
    code, out = _git(top, "show", "@{upstream}:" + rel, timeout=20)
    if code != 0:
        return 0, ""
    who, step, body = parse_coach(out)
    return (step, body) if who == tid else (0, "")


def await_reply(root, tid, n, wait, every=WAIT_EVERY, sleep=time.sleep):
    """The coach's reply to step `n`, or None after `wait` seconds."""
    deadline = time.time() + wait
    while True:
        step, body = upstream_reply(root, tid)
        if step >= n and body:
            return body
        if time.time() >= deadline:
            return None
        sleep(min(every, max(0.0, deadline - time.time())))


def write_coach(root, tid, body, step=None, run=subprocess.run, push=True):
    """`board coach`, on the Mac: the coach's reply to the step, committed
    alone and pushed. `(ok, said)`."""
    if not (body or "").strip():
        return False, "nothing on stdin, so nothing was sent"
    names_phi = _policy(root)
    if names_phi and names_phi(body):
        return False, ("the reply reaches for session content, and it is "
                       "public. Nothing was sent.")
    done = checks(root, tid)
    if step is None:
        if not done:
            return False, ("thread %s has no step check to answer" % tid)
        step = int(done[-1].get("step") or 0)
    target = coach_path(root, tid)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8") as fh:
        fh.write(coach_text(tid, step, body))
    return jobs.commit_alone(root, target, "%s: coach, step %d" % (tid, step),
                             run=run, push=push)


# ---------------------------------------------------------------------------
# the wake, on the Mac
# ---------------------------------------------------------------------------
def _woken(root, rid):
    return os.path.join(root, "live", "coach.woken", rid)


def _claim(root, rid):
    target = _woken(root, rid)
    try:
        os.makedirs(os.path.dirname(target), exist_ok=True)
        fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except OSError:
        return False
    os.close(fd)
    return True


def step_commit(root, rep):
    """The step's commit: the parent of the commit that added the report, if
    its subject is `<thread>: step`. "" where there was no code in the step."""
    rel = os.path.join(jobs.RELAY, "reports", rep["id"] + ".json")
    lines = jobs._git_lines(root, ["log", "-z", "--format=%H", "--diff-filter=A",
                                   "--", rel])
    if not lines:
        return ""
    added = lines[-1].strip()
    code, out = _git(root, "log", "-1", "--format=%H%x00%s", added + "^",
                     timeout=20)
    sha, _, subject = out.strip().partition("\0")
    if code == 0 and subject == "%s: step" % rep.get("thread"):
        return sha
    return ""


def sense(root, rep):
    """The `[coach]` inbox line for one step's check report."""
    tid, n = rep.get("thread"), rep.get("step")
    title = tid
    try:
        clean, _ = course_threads.read(root)
        one = course_threads.thread(clean, tid) if clean else None
        if one:
            title = "%s (%s)" % (tid, one["title"])
    except Exception:                                        # noqa: BLE001
        pass
    sha = step_commit(root, rep)
    lines = ["[coach] Step %s of thread %s came back from the cluster, where "
             "the sitting is held." % (n, title), ""]
    lines.append("  commit   %s" % ("%s  (`git show %s` is the step)"
                                    % (sha[:12], sha[:12]) if sha
                                    else "none: no code changed in this step"))
    if rep.get("files"):
        lines.append("  files    %s" % ", ".join(rep["files"]))
    lines.append("  check    %s, exit %s%s" % (
        rep.get("check"), rep.get("exit"),
        ", " + rep["crash"] if rep.get("crash") else ""))
    if rep.get("relay"):
        lines.append("")
        lines.extend("  RELAY: %s" % x for x in rep["relay"])
    else:
        lines.append("  (the check printed no RELAY: lines)")
    if rep.get("withheld"):
        lines.append("  (%d line(s) withheld: the PHI policy flagged them)"
                     % rep["withheld"])
    lines += ["", "DO THIS: a coach turn, under TEACHING.md's \"A sitting held "
              "at the cluster\". Read the step's diff%s. The check already ran "
              "beside the data and its lines are above, so do not run it here. "
              "Write the next card with `board write`. Then send the same text "
              "to the owner's terminal: `board coach %s --step %s` with the "
              "card's body on stdin. Both are public: talk about the code and "
              "the check's aggregate numbers, never about rows. The thread's "
              "files are held at the cluster: do not edit them here."
              % (" with `git show %s`" % sha[:12] if sha else "", tid, n)]
    return "\n".join(lines)


def wake(root, now=None):
    """Drop a `[coach]` line for each held thread's newest step check that has
    not woken a turn and has no reply yet. The reports dropped for.

    Item 4's pull calls this after every pull, beside its `[job]` wake. A
    check report on a thread no longer held wakes nothing.
    """
    out = []
    for tid in sorted(holds(root)):
        done = checks(root, tid)
        if not done:
            continue
        rep = done[-1]
        try:
            with open(coach_path(root, tid), "r", encoding="utf-8") as fh:
                who, step, _ = parse_coach(fh.read())
        except OSError:
            who, step = None, 0
        if who == tid and step >= int(rep.get("step") or 0):
            continue
        if not _claim(root, rep["id"]):
            continue
        try:
            jobs.drop(root, rep, now=now, text=sense(root, rep), signal="coach")
        except Exception:                                    # noqa: BLE001
            try:
                os.remove(_woken(root, rep["id"]))
            except OSError:
                pass
            continue
        out.append(rep)
    return out
