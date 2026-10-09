"""holds.py -- a sitting held at the cluster, coached on the glass.

The owner sometimes writes code on the cluster: beside the data, or simply in a
terminal there. The coach stays on the Mac and the card still lands on the
iPad; the step's check runs on the cluster. Three files carry it, all under the
workspace's `relay/`:

    relay/holds/<id>.json            the cluster's: these files are its
    relay/reports/check-<id>-<n>.json the cluster's: step n's check
    relay/coach/<id>.md              the Mac's: the coach's reply to the step

A HOLD IS NAMED BY A THREAD OR BY ITS FILES. `board hold <thread>` holds a
thread of `threads.json`; `board hold -- <path>...` holds those paths in any
workspace; a bare `board hold` holds the current sitting's thread, homework
file, chapter directory or map box (`resolve_target`). The record:

    {"id", "thread"?, "label", "files", "check", "held", "source"}

where `check` is `{"script": rel}`, `{"spec": "one"|"all", "argv": [...]}`, or
null (an unchecked hold, allowed only where output is open).

WHILE A HOLD LASTS, ITS `files` ARE THE CLUSTER'S. The Mac refuses to commit
them (`refusal`, which `board push` and the save button ask), and the relay's
pass pulls under the owner's uncommitted edits (`sync`) because nothing
upstream touches those files. So a pull on either side never conflicts.

WHAT A CHECK REPORT CARRIES depends on the workspace (`output_open`). By
default it is `RELAY:` lines only, each an aggregate. Only where
`tutorboard.json` says `"phi": false`, on disk and at HEAD, with no fence and
the policy loaded, is it the check's merged output too, made public line by
line and cut to fit (`check_output`), so the coach sees which test failed and
why.

`board send` is the owner's one command per step: commit the held files'
changes as `<id>: step`, run the check here, commit its report, push both, and
print the coach's reply when it lands. On the Mac the pull that carries a check
report drops a `[coach]` line (`wake`), the woken turn writes the next card,
and `board coach` writes the same text to `relay/coach/` and pushes it.

PURE where it can be: `validate_hold`, `check_spec`, `check_output` and
`refused_writes` take what they need and touch nothing.

Standard library only, like everything else.
"""

import json
import os
import re
import subprocess
import time

from . import cluster, jobs
from .course import threads as course_threads
# The check, and what of its output may leave, live in code.py; holds keeps
# its names until T38c deletes it.
from .code import (ANSI_RE, CHECK_SECONDS, CRASH_LINE, MAX_LINE,  # noqa: F401
                   MAX_LINES, OUT_BYTES, OUT_HEAD, OUT_TAIL, RELAY_LINE,
                   _argv_env, _head_phi, _policy, _program_ok, check_argv,
                   check_output, check_spec, crash_type, output_open,
                   relay_lines, run_check)

HOLDS = "holds"
COACH = "coach"
CHECK_PREFIX = "check-"

# The Mac's pull cadence while any hold stands. A step's round trip is this,
# a turn, and a push back: a minute or two.
POLL_SECONDS = 20

# How long `board send` waits for the coach's reply, and how often it looks.
WAIT_SECONDS = 180
WAIT_EVERY = 10

COACH_HEAD = re.compile(r"^<!-- coach (\S+) step (\d+) -->\s*$")


# ---------------------------------------------------------------------------
# where things are
# ---------------------------------------------------------------------------
def holds_dir(root):
    return os.path.join(root, jobs.RELAY, HOLDS)


def hold_path(root, hid):
    return os.path.join(holds_dir(root), hid + ".json")


def coach_path(root, hid):
    return os.path.join(root, jobs.RELAY, COACH, hid + ".md")


def check_id(hid, n):
    return "%s%s-%d" % (CHECK_PREFIX, hid, n)


def is_check(report_id):
    """Is this report a step's check rather than a request's? Item 4's wake
    asks this, so a check report wakes `[coach]` and never `[job]`."""
    return str(report_id or "").startswith(CHECK_PREFIX)


def hold_id(rec):
    """A hold's id: its own, or its thread's in a record that names only that."""
    return str((rec or {}).get("id") or (rec or {}).get("thread") or "")


def holds(root):
    """`{id: hold}` for every hold standing in this workspace."""
    out = {}
    for rec in jobs._read_json_dir(holds_dir(root)):
        hid = hold_id(rec)
        if hid:
            out[hid] = rec
    return out


def checks(root, hid):
    """`[report]` of this hold's step checks, oldest first."""
    pat = re.compile(r"^%s%s-(\d+)$" % (re.escape(CHECK_PREFIX), re.escape(hid)))
    got = []
    for rid, rep in jobs.reports(root).items():
        m = pat.match(rid)
        if m:
            got.append((int(m.group(1)), rep))
    return [r for _, r in sorted(got, key=lambda x: x[0])]


def next_step(root, hid):
    done = checks(root, hid)
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
    exports and holds, and every held file. The relay's pass treats an edit or
    a commit under these as its own and anything else as a reason to skip."""
    out = [jobs.RELAY + "/reports", "exports", jobs.RELAY + "/" + HOLDS]
    clean, _ = course_threads.read(root)
    out.extend(sorted(held_files(clean, holds(root))))
    return out


def who(hid, rec):
    """How a refusal names a hold: by its thread where it has one."""
    tid = (rec or {}).get("thread")
    return "thread %s" % tid if tid else "the hold %s" % hid


# ---------------------------------------------------------------------------
# is output open here: may a check's output leave this workspace whole
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# the validator: pure
# ---------------------------------------------------------------------------
def held_files(clean, standing):
    """`{path: hold id}`: every path a standing hold covers. The hold's own
    list, and for a thread's hold the thread's current one too, so a file
    added to the thread mid-hold is held as well."""
    out = {}
    for hid, rec in sorted((standing or {}).items()):
        tid = (rec or {}).get("thread")
        one = course_threads.thread(clean, tid) if (clean and tid) else None
        for p in list(rec.get("files") or []) + list((one or {}).get("files") or []):
            rel = course_threads._rel(p)
            if rel:
                out.setdefault(rel, hid)
    return out


def _covering(rel, covered):
    for base, hid in covered.items():
        if rel == base or rel.startswith(base + "/"):
            return hid
    return None


def _inside(rel, covered):
    """A held path under `rel`, which holding `rel` would swallow."""
    for base, hid in covered.items():
        if base.startswith(rel + "/"):
            return base, hid
    return None, None


def slug(text):
    """A hold id out of a file or directory name: `coin_change.go` is
    `coin-change`. Never starts `check-`."""
    s = re.sub(r"[^a-z0-9]+", "-", str(text or "").lower()).strip("-")[:60]
    s = s.strip("-") or "hold"
    return "h-" + s if s.startswith(CHECK_PREFIX) else s


def check_label(chk):
    """How a check is written in a report and on a card."""
    if not chk:
        return "none"
    if chk.get("script"):
        return chk["script"]
    return " ".join(chk.get("argv") or [])


def check_of(rec):
    """A hold record's check, in the record's shape. An old record's bare
    script path reads as `{"script": path}`."""
    chk = (rec or {}).get("check")
    if isinstance(chk, str):
        return {"script": chk} if chk else None
    if isinstance(chk, dict) and (chk.get("script") or chk.get("argv")):
        return chk
    return None


def validate_hold(clean, target, standing, tracked, spec=None, open_=False):
    """`(hold, problems)`: may this be held at the cluster? PURE.

        clean     the thread file, as `threads.validate` returns it, or None
        target    a thread id, or `{"thread"?, "id"?, "files"?, "label"?,
                  "check"?, "source"?, "dirs"?}`; `check` is a script path
                  that overrides, `dirs` the held paths that are directories
        standing  `{id: hold}`, the holds already standing
        tracked   workspace-relative paths tracked and unchanged at HEAD
        spec      the workspace's `tutorboard.json` check, cleaned, or None
        open_     `output_open`: whether a hold may stand with no check

    Refused whole, every problem at once.
    """
    if isinstance(target, str):
        target = {"thread": target}
    target = dict(target or {})
    problems = []
    tid = target.get("thread") or ""
    one = None
    if tid:
        one = course_threads.thread(clean, tid) if clean else None
        if not one:
            return None, ["thread %r is not one this workspace's thread file "
                          "declares" % (tid,)]
    hid = target.get("id") or tid
    if not tid:
        if not hid or not jobs.REQUEST_ID_RE.match(hid):
            problems.append("the hold's id %r must be 1-80 characters of a-z, "
                            "0-9 and hyphen; name one with --as" % (hid,))
        elif hid.startswith(CHECK_PREFIX):
            problems.append("the hold's id %r starts `%s`, which a step's check "
                            "report would share; name another with --as"
                            % (hid, CHECK_PREFIX))
        elif course_threads.thread(clean, hid) if clean else False:
            problems.append("%s is the id of a thread; `board hold %s` holds "
                            "the thread, or name this hold another with --as"
                            % (hid, hid))
    files = []
    for p in (target.get("files") if target.get("files") is not None
              else (one or {}).get("files") or []):
        rel = course_threads._rel(p)
        if not rel:
            problems.append("%r is not a path inside this workspace" % (p,))
        elif rel not in files:
            files.append(rel)
    if hid in (standing or {}):
        problems.append("%s is already held at the cluster, since %s. "
                        "`board release %s` ends it"
                        % (who(hid, standing[hid]),
                           _when(standing[hid].get("held")), hid))
    if not files:
        problems.append("%s has no files, so there is nothing for the cluster "
                        "to hold" % ("thread " + tid if tid else "this hold"))
    others = dict((k, v) for k, v in (standing or {}).items() if k != hid)
    covered = held_files(clean, others)
    for f in files:
        by = _covering(f, covered)
        if by:
            problems.append("%s is already held, by %s" % (f, who(by, others[by])))
            continue
        base, by = _inside(f, covered)
        if by:
            problems.append("%s holds %s, which is already held, by %s"
                            % (f, base, who(by, others[by])))
    script = target.get("check") or (one or {}).get("check") or ""
    chk = None
    if script:
        if script not in set(tracked or ()):
            problems.append("check %s is not tracked and unchanged at HEAD, so "
                            "the step would be checked by something nobody can "
                            "read" % script)
        chk = {"script": script}
    elif spec and files:
        dirs = set(target.get("dirs") or ())
        chk, bad = check_spec(spec, [(f, f in dirs) for f in files])
        problems.extend(bad)
        if chk and not _program_ok(chk["argv"][0], tracked):
            problems.append("the workspace's check runs %s, which is not "
                            "tracked and unchanged at HEAD" % chk["argv"][0])
    elif not open_:
        problems.append(
            "%s has no check, and this workspace's output is closed, so a step "
            "would come back with nothing. %s" % (
                "thread " + tid if tid else "this hold",
                "The tutor writes one and names it with `board thread check "
                "%s <script>`" % tid if tid else
                "Name a tracked script with --check, or declare `check` in "
                "tutorboard.json"))
    if problems:
        return None, problems
    rec = {"id": hid, "files": files,
           "label": target.get("label") or (one or {}).get("title") or hid,
           "check": chk, "source": target.get("source") or (
               "thread %s" % tid if tid else "named")}
    if tid:
        rec["thread"] = tid
    return rec, []


def refused_writes(paths, clean, standing):
    """Every problem with a turn here writing `paths`, workspace-relative. PURE.

    A path under a hold's files is the cluster's until the release.
    """
    covered = held_files(clean, standing)
    out = []
    for p in sorted(set(paths or ())):
        rel = course_threads._rel(p)
        hid = _covering(rel, covered) if rel else None
        if hid:
            out.append("%s belongs to %s, held at the cluster since %s. A turn "
                       "here does not write it; `board release %s` on the "
                       "cluster gives it back"
                       % (rel, who(hid, standing[hid]),
                          _when(standing[hid].get("held")), hid))
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
# what a bare `board hold` holds
# ---------------------------------------------------------------------------
def resolve_target(root, words, state, cwd=None, as_id=None, script=None):
    """`(target, said, problems)` for `board hold`'s words.

        board hold <thread>                  that thread
        board hold [--as <id>] [--check <s>] -- <path>...
        board hold                           the current sitting

    A path is workspace-relative, or relative to `cwd` and inside the
    workspace, and it must exist. With no words the sitting in
    `live/state.json` answers, in this order: its thread, its homework file,
    its chapter's directory, its map box's files; otherwise "name the files".
    `said` is where the answer came from, which the command prints, because
    this machine's `state.json` is only as fresh as its last pull.
    """
    words = list(words or [])
    clean, _ = course_threads.read(root)
    if words and words[0] != "--" and len(words) == 1 and not as_id \
            and course_threads.thread(clean, words[0]):
        return ({"thread": words[0], "check": script or ""},
                "thread %s, named" % words[0], [])
    if words and words[0] == "--":
        words = words[1:]
    if words:
        files, dirs, problems = _paths(root, words, cwd)
        if problems:
            return None, "", problems
        hid = as_id or slug(os.path.basename(files[0]))
        return ({"id": hid, "files": files, "dirs": dirs, "check": script or "",
                 "label": ", ".join(files[:3]) + (" ..." if len(files) > 3
                                                  else ""),
                 "source": "named"}, "the paths named", [])
    st = state or {}
    tid = str(st.get("thread") or "")
    if tid and course_threads.thread(clean, tid):
        return ({"thread": tid, "check": script or "",
                 "source": "the sitting's thread"},
                "the sitting's thread, %s (live/state.json)" % tid, [])
    found, source, label = [], "", ""
    hw = str(st.get("hw") or "")
    if hw and course_threads._rel(hw) and os.path.isfile(os.path.join(root, hw)):
        found, source = [course_threads._rel(hw)], "the sitting's homework file"
        label = st.get("chapter") or os.path.basename(hw)
    if not found and st.get("chapter"):
        from .course import syllabus
        d = syllabus.chapter_dir(root, st.get("chapter"))
        if d:
            found, source, label = [d], "the sitting's chapter", st["chapter"]
    if not found and st.get("node"):
        try:
            from .course import map as course_map
            node = course_map.find(root, st["node"], st)
        except Exception:                                    # noqa: BLE001
            node = None
        got = [course_threads._rel(f) for f in (node or {}).get("files") or []]
        got = [f for f in got if f and os.path.exists(os.path.join(root, f))]
        if got:
            found, source = got, "the sitting's map box, %s" % st["node"]
            label = (node or {}).get("name") or st["node"]
    if not found:
        return None, "", ["this sitting has no thread, homework file, chapter "
                          "directory or map box to hold, so name the files: "
                          "board hold -- <path>..."]
    dirs = [f for f in found if os.path.isdir(os.path.join(root, f))]
    base = os.path.splitext(os.path.basename(found[0]))[0]
    return ({"id": as_id or slug(base), "files": found, "dirs": dirs,
             "check": script or "", "label": label, "source": source},
            "%s: %s (live/state.json)" % (source, ", ".join(found)), [])


def _paths(root, words, cwd=None):
    real = os.path.realpath(root)
    files, dirs, problems = [], [], []
    for w in words:
        cand = None
        for base in ([root] + ([cwd] if cwd else [])):
            full = os.path.realpath(os.path.join(base, w))
            if os.path.exists(full):
                cand = os.path.relpath(full, real)
                break
        rel = course_threads._rel(cand) if cand else None
        if not rel or rel.startswith("../") or rel == "..":
            problems.append("%s is neither a thread of threads.json nor a "
                            "file or directory inside this workspace" % w)
            continue
        if rel not in files:
            files.append(rel)
            if os.path.isdir(os.path.join(root, rel)):
                dirs.append(rel)
    return files, dirs, problems


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

    A path on disk, or deleted from disk but still in the index, is added. One
    already out of the index (`git rm`) is not: `git add` would refuse it as
    a pathspec matching nothing, and `--only` commits its removal anyway.
    """
    there = [r for r in rels if os.path.lexists(os.path.join(top, r))
             or _git(top, "ls-files", "--", r, timeout=20)[1].strip()]
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
    """Workspace-relative paths tracked and unchanged at HEAD, that resolve
    inside the workspace: a tracked symlink to another workspace's script is
    not this workspace's check."""
    tracked = set(jobs._git_lines(root, ["ls-files", "-z", "--", "."]))
    changed = set(jobs._git_lines(root, ["diff", "--name-only", "-z",
                                         "--relative", "HEAD", "--", "."]))
    real = os.path.realpath(root)
    return set(p for p in tracked - changed
               if os.path.realpath(os.path.join(real, p)).startswith(real + os.sep))


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
def hold(root, target, now=None, said=""):
    """Hold `target` at the cluster: write the hold, commit it alone, push it.
    `(ok, lines)`. `target` is a thread id or `resolve_target`'s dict; `said`
    is where it came from, printed first."""
    if not jobs.has_slurm():
        return False, ["a hold is made in the cluster checkout, where the owner "
                       "writes the code; this machine has no Slurm"]
    from . import atlas
    if "/" not in atlas.identify(root):
        # Only a workspace's own `relay/holds/` is read by the Mac's refusal
        # and its wake, so a hold made above one would hold nothing.
        return False, ["%s is not a workspace of a family, so nothing was held. "
                       "`cd` into the workspace the files are in, then hold "
                       "them there" % root]
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
    if isinstance(target, str):
        target = {"thread": target}
    if problems and target.get("thread"):
        return False, problems
    from .course import config
    cfg = config.read_config(root)
    open_ = output_open(root, cfg=cfg)
    rec, problems = validate_hold(clean, target, holds(root), _tracked(root),
                                  spec=cfg.get("check"), open_=open_)
    if problems:
        return False, problems
    hid = rec["id"]
    rec["held"] = round(float(now or time.time()), 3)
    path = hold_path(root, hid)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(rec, fh, indent=2, sort_keys=True)
        fh.write("\n")
    ok, out = _commit(top, [_rel_top(top, root, os.path.relpath(path, root))],
                      _message(root, "%s: held at the cluster" % hid))
    if not ok:
        os.remove(path)
        return False, ["the hold could not be committed: " + out]
    pushed, why = push(top)
    lines = []
    if said:
        lines.append("Holding %s." % said)
    lines += ["%s is held at the cluster: its files are yours here, and the "
              "Mac refuses to write them until `board release %s`."
              % (hid, hid),
              "Files: " + ", ".join(rec["files"]),
              "Check: " + (check_label(rec["check"]) if rec["check"] else
                           "none -- the coach reads the step's diff alone"),
              "Output to the coach: " + (
                  "the check's own, cut to fit" if open_ else
                  "RELAY: lines only (this workspace is closed)"),
              "After each step: board send"]
    for p in cfg.get("check_problems") or []:
        lines.append("(tutorboard.json: %s)" % p)
    if not pushed:
        lines.append("BUT IT IS NOT PUSHED YET (%s). `board send` pushes it "
                     "with the first step." % why)
    return pushed, lines


def release(root, hid):
    """End the hold: remove it, commit that alone, push. `(ok, lines)`."""
    standing = holds(root)
    if hid not in standing:
        return False, ["%s is not held%s" % (
            hid, "; held here: " + ", ".join(sorted(standing)) if standing
            else "")]
    clean, _ = course_threads.read(root)
    mine = held_files(clean, {hid: standing[hid]})
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
    rel = _rel_top(top, root, os.path.relpath(hold_path(root, hid), root))
    code, out = _git(top, "rm", "-q", "--", rel)
    if code != 0:
        return False, ["the hold could not be removed: " + out.strip()]
    ok, out = _commit(top, [rel], _message(root, "%s: released" % hid))
    if not ok:
        return False, ["the release could not be committed: " + out]
    pushed, said = push(top)
    lines = ["%s is released: the Mac may write its files again." % hid]
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
def send(root, hid=None, wait=WAIT_SECONDS, say=print, run=subprocess.run,
         anyway=False, now=None):
    """`board send`: one step, checked here and sent to the coach. Exit code.

    1. Commit the held files' changes as `<id>: step`, as the owner.
    2. Run the hold's check; write `relay/reports/check-<id>-<n>.json` and
       commit it alone.
    3. Push both, and wait up to `wait` seconds for the coach's reply.
    """
    if not jobs.has_slurm():
        say("board send: a step is sent from the cluster checkout, where the "
            "work is held. This machine has no Slurm.")
        return 1
    standing = holds(root)
    if hid is None:
        if len(standing) != 1:
            say("board send: name the hold -- held here: %s"
                % (", ".join(sorted(standing)) or "none"))
            return 1
        hid = sorted(standing)[0]
    if hid not in standing:
        say("board send: %s is not held. `board hold` first." % hid)
        return 1
    top = top_of(root)
    ok, why = sync(top)
    if not ok:
        say("board send: nothing was sent: " + why)
        return 1
    standing = holds(root)
    if hid not in standing:
        say("board send: %s was released upstream. Nothing was sent." % hid)
        return 1
    rec = standing[hid]
    tid = rec.get("thread") or ""
    clean, problems = course_threads.read(root)
    one = course_threads.thread(clean, tid) if (clean and tid) else None
    if tid and (problems or not one):
        say("board send: the thread file does not declare %s: %s"
            % (tid, "; ".join(problems)))
        return 1
    from .course import config
    cfg = config.read_config(root)
    open_ = output_open(root, cfg=cfg)
    chk = check_of(rec) or (
        {"script": one["check"]} if one and one.get("check") else None)
    tracked = _tracked(root)
    if chk and chk.get("script") and chk["script"] not in tracked:
        say("board send: the check %s is not tracked and unchanged at HEAD. "
            "Nothing was sent." % chk["script"])
        return 1
    if chk and chk.get("argv") and not _program_ok(chk["argv"][0], tracked):
        say("board send: the check runs %s, which is not tracked and unchanged "
            "at HEAD. Nothing was sent." % chk["argv"][0])
        return 1
    if not chk and not open_:
        say("board send: %s has no check, and this workspace's output is "
            "closed. Nothing was sent." % hid)
        return 1
    if not anyway:
        from . import leaving
        phi = leaving.reason(root)
        if phi:
            say("board send: " + phi)
            return 1

    mine = held_files(clean, {hid: rec})
    changed = sorted(d for d in course_threads.dirty_of(root)
                     if _covering(d, mine))
    if changed:
        ok, out = _commit(top, [_rel_top(top, root, c) for c in changed],
                          "%s: step" % hid)
        if not ok:
            say("board send: the step could not be committed: " + out)
            return 1
        say("committed %s: step (%s)" % (hid, ", ".join(changed)))
    else:
        say("no change under %s's files; sending the check alone" % hid)

    n = next_step(root, hid)
    began = float(now or time.time())
    if chk:
        say("running the check: %s" % check_label(chk))
        got = run_check(root, chk, run=run, names_phi=_policy(root),
                        open_=open_, path=(cfg.get("check") or {}).get("path")
                        if chk.get("argv") else None)
        state = "completed" if got["exit"] == 0 else "failed"
    else:
        say("no check: the coach reads the step's diff alone")
        got, state = {"relay": []}, "unchecked"
    rep = {"id": check_id(hid, n), "kind": "check", "hold": hid, "step": n,
           "label": rec.get("label") or hid, "check": check_label(chk),
           "files": changed, "open": open_, "state": state,
           "ran": round(began, 3), "ended": round(time.time(), 3)}
    if tid:
        rep["thread"] = tid
    rep.update(got)
    target = os.path.join(jobs.reports_dir(root), rep["id"] + ".json")
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=2, sort_keys=True, ensure_ascii=False)
        fh.write("\n")
    ok, out = _commit(top, [_rel_top(top, root, os.path.relpath(target, root))],
                      "%s: check %d" % (hid, n))
    if not ok:
        say("board send: the check's report could not be committed: " + out)
        return 1
    for line in got.get("relay") or []:
        say("  RELAY: " + line)
    if chk:
        say("check %s, exit %d%s%s" % (
            rep["state"], got["exit"],
            ", " + got["crash"] if got.get("crash") else "",
            "; its output (%d line(s)) goes to the coach"
            % got.get("output_total", 0) if open_ else ""))
    pushed, said = push(top)
    if not pushed:
        say("board send: step %d is committed here and NOT pushed: %s. "
            "`board send` again pushes it." % (n, said))
        return 1
    say("step %d sent." % n)
    if wait <= 0:
        return 0
    say("waiting up to %d seconds for the coach..." % wait)
    text = await_reply(root, hid, n, wait)
    if text is None:
        say("no reply in %d seconds. It lands on the board; `board send "
            "--reply %s` prints it here." % (wait, hid))
        return 0
    say("")
    say(text)
    return 0


# ---------------------------------------------------------------------------
# the coach's reply
# ---------------------------------------------------------------------------
def parse_coach(text):
    """`(hold id, step, body)` out of a `relay/coach/` file, or `(None, 0, "")`."""
    lines = (text or "").splitlines()
    m = COACH_HEAD.match(lines[0]) if lines else None
    if not m:
        return None, 0, ""
    return m.group(1), int(m.group(2)), "\n".join(lines[1:]).strip()


def coach_text(hid, n, body):
    return "<!-- coach %s step %d -->\n%s\n" % (hid, n, body.strip())


def upstream_reply(root, hid):
    """`(step, body)` of the reply on origin, fetched now. `(0, "")` if none."""
    top = top_of(root)
    code, up = _git(top, "rev-parse", "--abbrev-ref", "@{upstream}", timeout=10)
    if code != 0:
        return 0, ""
    _git(top, "fetch", "--quiet", up.strip().split("/", 1)[0])
    rel = _rel_top(top, root, os.path.relpath(coach_path(root, hid), root))
    code, out = _git(top, "show", "@{upstream}:" + rel, timeout=20)
    if code != 0:
        return 0, ""
    whose, step, body = parse_coach(out)
    return (step, body) if whose == hid else (0, "")


def await_reply(root, hid, n, wait, every=WAIT_EVERY, sleep=time.sleep):
    """The coach's reply to step `n`, or None after `wait` seconds."""
    deadline = time.time() + wait
    while True:
        step, body = upstream_reply(root, hid)
        if step >= n and body:
            return body
        if time.time() >= deadline:
            return None
        sleep(min(every, max(0.0, deadline - time.time())))


def write_coach(root, hid, body, step=None, push=True):
    """`board coach`, on the Mac: the coach's reply to the step, committed
    alone and pushed. `(ok, said)`."""
    if not (body or "").strip():
        return False, "nothing on stdin, so nothing was sent"
    names_phi = _policy(root)
    if names_phi and names_phi(body):
        return False, ("the reply reaches for session content, and it is "
                       "public. Nothing was sent.")
    done = checks(root, hid)
    if step is None:
        if not done:
            return False, ("%s has no step check to answer" % hid)
        step = int(done[-1].get("step") or 0)
    target = coach_path(root, hid)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8") as fh:
        fh.write(coach_text(hid, step, body))
    return jobs.commit_alone(root, target, "%s: coach, step %d" % (hid, step),
                             push=push)


# ---------------------------------------------------------------------------
# the wake, on the Mac
# ---------------------------------------------------------------------------
def _woken(root, rid):
    """The claim on a check report's wake: `relay/state/reported/coach-<id>`,
    beside the job claims. One written under `live/coach.woken/` before the
    move is moved there by `jobs.migrate_state`, which `_claim` runs first."""
    return os.path.join(jobs.claims_dir(root), "coach-%s" % rid)


def _claim(root, rid):
    jobs.migrate_state(root)
    target = _woken(root, rid)
    try:
        os.makedirs(os.path.dirname(target), exist_ok=True)
        fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except OSError:
        return False
    os.close(fd)
    return True


def report_hold(rep):
    """The hold a check report belongs to."""
    return str((rep or {}).get("hold") or (rep or {}).get("thread") or "")


def step_commit(root, rep):
    """The step's commit: the parent of the commit that added the report, if
    its subject is `<id>: step`. "" where there was no code in the step."""
    rel = os.path.join(jobs.RELAY, "reports", rep["id"] + ".json")
    lines = jobs._git_lines(root, ["log", "-z", "--format=%H", "--diff-filter=A",
                                   "--", rel])
    if not lines:
        return ""
    added = lines[-1].strip()
    code, out = _git(root, "log", "-1", "--format=%H%x00%s", added + "^",
                     timeout=20)
    sha, _, subject = out.strip().partition("\0")
    if code == 0 and subject == "%s: step" % report_hold(rep):
        return sha
    return ""


def sense(root, rep):
    """The `[coach]` inbox line for one step's check report."""
    hid, n = report_hold(rep), rep.get("step")
    tid = rep.get("thread") or ""
    title = rep.get("label") or hid
    if tid:
        title = "thread %s" % tid
        try:
            clean, _ = course_threads.read(root)
            one = course_threads.thread(clean, tid) if clean else None
            if one:
                title = "thread %s (%s)" % (tid, one["title"])
        except Exception:                                    # noqa: BLE001
            pass
    elif rep.get("label") and rep["label"] != hid:
        title = "%s (%s)" % (hid, rep["label"])
    open_ = bool(rep.get("open"))
    sha = step_commit(root, rep)
    lines = ["[coach] Step %s of %s came back from the cluster, where the "
             "sitting is held." % (n, title), ""]
    lines.append("  commit   %s" % ("%s  (`git show %s` is the step)"
                                    % (sha[:12], sha[:12]) if sha
                                    else "none: no code changed in this step"))
    if rep.get("files"):
        lines.append("  files    %s" % ", ".join(rep["files"]))
    if rep.get("state") == "unchecked":
        lines.append("  check    none: this hold has no check; read the diff")
    else:
        lines.append("  check    %s, exit %s%s" % (
            rep.get("check"), rep.get("exit"),
            ", " + rep["crash"] if rep.get("crash") else ""))
    if rep.get("relay"):
        lines.append("")
        lines.extend("  RELAY: %s" % x for x in rep["relay"])
    elif not open_ and rep.get("state") != "unchecked":
        lines.append("  (the check printed no RELAY: lines)")
    if open_ and rep.get("output") is not None:
        lines.append("")
        lines.append("  output   %d line(s)%s:" % (
            rep.get("output_total") or 0,
            ", %d cut from the middle" % rep["output_cut"]
            if rep.get("output_cut") else ""))
        lines.extend("    | " + x for x in rep["output"])
    if rep.get("withheld"):
        lines.append("  (%d line(s) withheld: the PHI policy flagged them)"
                     % rep["withheld"])
    diff = " with `git show %s`" % sha[:12] if sha else ""
    if open_:
        ran = ("The check already ran on the cluster and its output is above, "
               "so do not run it here: read the failing case from it. ")
        public = ("Both are public: talk about the code and the check's "
                  "output.")
    else:
        ran = ("The check already ran beside the data and its lines are above, "
               "so do not run it here. ")
        public = ("Both are public: talk about the code and the check's "
                  "aggregate numbers, never about rows.")
    lines += ["", "DO THIS: a coach turn, under TEACHING.md's \"A sitting held "
              "at the cluster\". Read the step's diff%s. %sWrite the next card "
              "with `board write`. Then send the same text to the owner's "
              "terminal: `board coach %s --step %s` with the card's body on "
              "stdin. %s The held files are the cluster's: do not edit them "
              "here." % (diff, ran, hid, n, public)]
    return "\n".join(lines)


def wake(root, now=None):
    """Drop a `[coach]` line for each hold's newest step check that has not
    woken a turn and has no reply yet. The reports dropped for.

    Item 4's pull calls this after every pull, beside its `[job]` wake. A
    check report on a hold no longer standing wakes nothing.
    """
    out = []
    for hid in sorted(holds(root)):
        done = checks(root, hid)
        if not done:
            continue
        rep = done[-1]
        try:
            with open(coach_path(root, hid), "r", encoding="utf-8") as fh:
                whose, step, _ = parse_coach(fh.read())
        except OSError:
            whose, step = None, 0
        if whose == hid and step >= int(rep.get("step") or 0):
            continue
        if not _claim(root, rep["id"]):
            continue
        try:
            cluster.wake(root, rep.get("session"), sense(root, rep),
                         wake=True, signal="coach", request=rep.get("request"),
                         now=now)
        except Exception:                                    # noqa: BLE001
            try:
                os.remove(_woken(root, rep["id"]))
            except OSError:
                pass
            continue
        out.append(rep)
    return out


def standing_sense(root):
    """The lines a brief carries for holds standing in this workspace, or []."""
    try:
        standing = holds(root)
    except Exception:                                        # noqa: BLE001
        return []
    out = []
    for hid, rec in sorted(standing.items()):
        out.append("HELD AT THE CLUSTER: %s (`%s`). The owner writes %s there, "
                   "and the files are the cluster's until `board release %s`: "
                   "%s. Do not edit them here; `board push` refuses. Each step "
                   "comes back as a `[coach]` line -- TEACHING.md, \"A sitting "
                   "held at the cluster\"."
                   % (rec.get("label") or hid, hid,
                      "thread %s's code" % rec["thread"] if rec.get("thread")
                      else "the code", hid,
                      ", ".join((rec.get("files") or [])[:8])))
    return out
