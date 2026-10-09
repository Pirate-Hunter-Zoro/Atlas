"""code.py -- a coding session held at the cluster: `board code`.

The owner writes code in a terminal on the cluster, beside the data, and the
tutor coaches from the Mac. One git ref carries it, `code/<session>`:

    board code <session> <path>...    hold these paths and watch them
    board code <session>              resume watching a session held here
    board code <session> --end [--title T]
                                      one commit of the held paths on main
    board code <session> --abandon    drop the ref and the registration
    board code --list                 the sessions held on this machine

A REGISTRATION, `~/.local/state/tutor-board/code/<session>.json`, is the
session on this machine: {session, subject, paths, base, last, step, root}.
`base` is HEAD when it started, `last` the tip of `code/<session>` as this
loop last saw it (its own snapshot, or a commit it applied), `step` the number
of snapshots pushed. The paths are repository-relative, inside one subject.

EACH STEP. The loop polls the held paths' mtimes every `POLL` seconds. After
`QUIET` seconds without a change it builds a snapshot through a temporary index
(`GIT_INDEX_FILE`: `read-tree <last>`, `add -A -- <paths>`, `write-tree`,
`commit-tree -p <last>`), so HEAD, the real index and main never move. The
commit-time gate runs over what the snapshot changes against HEAD: the audit,
`leaving.refused` and the participant scan (`audit.gate`). A refusal prints
why and pushes nothing. Then the subject's check runs, and the message carries
`Step N`, `check: pass|fail|none`, `ran_at`, the `RELAY:` lines, and the
check's sanitized output only where `output_open` is true. The snapshot is
pushed to `refs/heads/code/<session>`, fast-forward only.

A COMMIT THE LOOP DID NOT MAKE -- a vibe push from the Mac -- arrives on the
same ref. Every `FETCH_EVERY` seconds the loop asks origin for it, and applies
it with `git checkout <sha> -- <paths>` (through a temporary index) when the
held paths are unchanged since the last snapshot. Otherwise it prints "both
sides changed" with the files, and waits.

`--end` takes `relay/.lock`, the relay pass's own lock, commits the held paths
to main as one `<subject>: <title>` commit through `gitops`, pushes main,
deletes the remote ref and the registration. A held file that main changed
too is refused, named. `--abandon` deletes the ref and the registration only.

While a session is registered, the relay tolerates its paths (`held`): an
edit there never skips a pass, and an upstream change to one stops the pull
with "held path changed upstream" instead of overwriting it. A request filed
from the session may pin a commit on `code/<session>` (`pin_ok`).

THE CHECK, and what of its output may leave, live here too: `check_spec`,
`run_check`, `check_output`, `relay_lines`, `crash_type` and `output_open`.

Relay-path code: it runs on the cluster's python3, which may be 3.7. No
walrus, no `match`. Standard library only.
"""

import fcntl
import json
import os
import re
import shutil
import subprocess
import tempfile
import time

from . import exports, fenced, paths

POLL = 2.0
QUIET = 10.0
# How often the loop asks origin for a commit it did not make.
FETCH_EVERY = 10.0
# How long `--end` waits for a relay pass to let go of `relay/.lock`.
LOCK_WAIT = 300
LOCK = os.path.join("relay", ".lock")

SESSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
SUBJECT_DIRS = ("courses", "projects")
# Under a subject: the cluster channel, which the relay writes.
CHANNEL = ("relay", "exports")
# Never walked by the mtime poll.
SKIP_DIRS = (".git", "node_modules", "__pycache__", ".lake")

# A check runs in the owner's terminal. Half an hour is a job, and a job goes
# through `board job`.
CHECK_SECONDS = 30 * 60

MAX_LINES = 40
MAX_LINE = 300
# An open subject's output: the first `OUT_HEAD` and last `OUT_TAIL` lines, at
# most `OUT_BYTES` in all. The end of a test run is where the failure is.
OUT_HEAD = 40
OUT_TAIL = 120
OUT_BYTES = 16 * 1024
RELAY_LINE = re.compile(r"^RELAY:\s?(.*)$")
# The exception type of a crash, from a traceback's last line. Only the type:
# the message after it can print a value.
CRASH_LINE = re.compile(r"^([A-Za-z_][\w.]*(?:Error|Exception|Interrupt|Exit))\b")
ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)"
                     r"|\x1b[@-Z\\-_]")

USAGE = """\
board code <session> <path>...        hold these paths at the cluster and watch
                                      them: each pause of 10 s is a step, pushed
                                      to code/<session> with its check
board code <session>                  resume watching a session held here
board code <session> --end [--title T]
                                      commit the held paths to main as one
                                      commit, push, and drop code/<session>
board code <session> --abandon        drop code/<session> and the registration;
                                      the working tree is left as it is
board code --list                     the sessions held on this machine

Paths are relative to here or to the Atlas root, inside one course or
project, and never fenced."""


# ---------------------------------------------------------------------------
# git
# ---------------------------------------------------------------------------
def _git(top, *args, **kw):
    """`(code, text)`: stdout stripped on success, stdout and stderr on a
    failure. `env` adds to the environment, `input` is stdin. Never raises."""
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_ASKPASS="/bin/false")
    env.update(kw.get("env") or {})
    try:
        p = subprocess.run(["git"] + list(args), cwd=top, env=env,
                           input=kw.get("input"), stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, universal_newlines=True,
                           timeout=kw.get("timeout", 120))
    except (OSError, subprocess.SubprocessError) as exc:
        return 1, str(exc)
    if p.returncode == 0:
        return 0, (p.stdout or "").strip()
    return p.returncode, ((p.stdout or "") + (p.stderr or "")).strip()


def top_of(root):
    code, out = _git(root, "rev-parse", "--show-toplevel", timeout=10)
    return out if code == 0 else ""


def _ancestor(top, a, b):
    code, _ = _git(top, "merge-base", "--is-ancestor", a, b, timeout=30)
    return code == 0


def _tree_of(top, rev):
    code, out = _git(top, "rev-parse", "--verify", "--quiet", rev + "^{tree}")
    return out if code == 0 else ""


def ref(sid):
    return "refs/heads/code/%s" % sid


def tracking(sid):
    return "refs/remotes/origin/code/%s" % sid


def remote_tip(top, sid):
    """`(sha, error)`: `code/<sid>` as origin has it, fetched here. `("", "")`
    where origin has no such ref."""
    code, out = _git(top, "ls-remote", "origin", ref(sid), timeout=60)
    if code != 0:
        return "", "could not ask origin for code/%s: %s" % (
            sid, (out.splitlines() or ["no answer"])[-1])
    sha = out.split()[0] if out.split() else ""
    if not sha:
        _git(top, "update-ref", "-d", tracking(sid))
        return "", ""
    if _git(top, "cat-file", "-e", sha + "^{commit}")[0] != 0:
        code, out = _git(top, "fetch", "--quiet", "origin",
                         "+%s:%s" % (ref(sid), tracking(sid)), timeout=120)
        if code != 0:
            return "", "could not fetch code/%s: %s" % (
                sid, (out.splitlines() or ["no answer"])[-1])
    else:
        _git(top, "update-ref", tracking(sid), sha)
    return sha, ""


# ---------------------------------------------------------------------------
# registrations
# ---------------------------------------------------------------------------
def reg_dir():
    return os.path.join(os.environ.get("BOARD_STATE_DIR") or paths.STATE_DIR,
                        "code")


def reg_path(sid):
    return os.path.join(reg_dir(), sid + ".json")


def _same(a, b):
    return os.path.realpath(a or "") == os.path.realpath(b or "")


def read(sid, top=None):
    """The registration of session `sid` on this machine, or None. With
    `top`, only one made for that checkout."""
    if not SESSION_RE.match(str(sid or "")):
        return None
    try:
        with open(reg_path(sid), "r", encoding="utf-8") as fh:
            rec = json.load(fh)
    except (OSError, ValueError):
        return None
    if not isinstance(rec, dict) or not isinstance(rec.get("paths"), list):
        return None
    if top and rec.get("root") and not _same(rec["root"], top):
        return None
    return rec


def registrations(top=None):
    """Every registration on this machine, for `top` only where given."""
    try:
        names = sorted(os.listdir(reg_dir()))
    except OSError:
        return []
    out = []
    for name in names:
        if name.endswith(".json"):
            rec = read(name[:-len(".json")], top)
            if rec:
                out.append(rec)
    return out


def held(top):
    """Repository-relative paths an open coding session holds in `top`."""
    out = []
    for rec in registrations(top):
        out.extend(p for p in rec.get("paths") or [] if isinstance(p, str) and p)
    return sorted(set(out))


def _save(rec):
    path = reg_path(rec["session"])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + ".tmp", "w", encoding="utf-8") as fh:
        json.dump(rec, fh, indent=2, sort_keys=True)
        fh.write("\n")
    os.replace(path + ".tmp", path)


def forget(sid):
    try:
        os.remove(reg_path(sid))
    except OSError:
        pass


def _under(rel, base):
    return rel == base or rel.startswith(base + "/")


# ---------------------------------------------------------------------------
# what may be held
# ---------------------------------------------------------------------------
def subject_of(rel):
    """`courses/X` or `projects/X` for a repository-relative path, or ""."""
    parts = rel.split("/")
    if len(parts) >= 2 and parts[0] in SUBJECT_DIRS and parts[1] \
            and not parts[1].startswith("."):
        return parts[0] + "/" + parts[1]
    return ""


def resolve(top, words, cwd=None, others=None):
    """`(paths, subject, problems)` for `board code`'s path words.

    A word is relative to `cwd`, else to `top`, and must exist inside a
    subject. Refused: no words, a fenced path, the subject itself, its
    `relay/` or `exports/`, a path git ignores or the audit refuses, paths in
    two subjects, and a path another session here holds (`others`, `{sid:
    [paths]}`). Every problem at once.
    """
    from . import audit
    real = os.path.realpath(top)
    found, problems = [], []
    if not words:
        return [], "", ["no paths: name what you will write, "
                        "`board code <session> <path>...`"]
    for w in words:
        # Fenced by name, whether or not it is there: nothing is even
        # looked up under a fence.
        if fenced.in_fence(w):
            problems.append("%s is fenced (%s): nothing there is held, "
                            "snapshotted or pushed"
                            % (w, ", ".join(fenced.NEVER)))
            continue
        cand = None
        for base in ([cwd] if cwd else []) + [top]:
            full = os.path.realpath(os.path.join(base, w))
            if os.path.lexists(full):
                cand = full
                break
        if cand is None:
            problems.append("%s is not there, here or under the Atlas root"
                            % w)
            continue
        rel = os.path.relpath(cand, real).replace(os.sep, "/")
        if rel == "." or rel.startswith("../") or rel == "..":
            problems.append("%s is outside the Atlas checkout" % w)
            continue
        if fenced.in_fence(rel):
            problems.append("%s is fenced (%s): nothing there is held, "
                            "snapshotted or pushed"
                            % (rel, ", ".join(fenced.NEVER)))
            continue
        subject = subject_of(rel)
        if not subject:
            problems.append("%s is not inside a course or project" % rel)
            continue
        if rel == subject:
            problems.append("%s is the whole subject; name the directories or "
                            "files you will write inside it" % rel)
            continue
        if any(_under(rel, subject + "/" + c) for c in CHANNEL):
            problems.append("%s is the relay's channel, which the cluster "
                            "writes itself" % rel)
            continue
        if _git(top, "check-ignore", "-q", "--", rel)[0] == 0:
            problems.append("git ignores %s, so a step could never carry it"
                            % rel)
            continue
        said = audit.problems(rel)
        if said:
            problems.extend(said)
            continue
        if rel not in found:
            found.append(rel)
    # A path inside another held one adds nothing.
    found = [p for p in found
             if not any(q != p and _under(p, q) for q in found)]
    subjects = sorted(set(subject_of(p) for p in found))
    if len(subjects) > 1:
        problems.append("the paths are in %d subjects (%s); a coding session "
                        "holds paths in one" % (len(subjects),
                                                ", ".join(subjects)))
    for sid, theirs in sorted((others or {}).items()):
        for p in found:
            for q in theirs or []:
                if _under(p, q) or _under(q, p):
                    problems.append("%s is already held by coding session %s "
                                    "(%s)" % (p, sid, q))
    if problems:
        return [], "", problems
    return sorted(found), subjects[0], []


def start(top, sid, words, cwd=None, now=None):
    """`(registration, problems)`: register a session, or resume one held
    here. Writes only the registration; nothing in git moves."""
    if not SESSION_RE.match(str(sid or "")):
        return None, ["%r is not a session id (letters, digits, - and _)"
                      % (sid,)]
    rec = read(sid)
    if rec and not _same(rec.get("root"), top):
        return None, ["session %s is held in %s, not here" % (sid, rec.get("root"))]
    if rec and not words:
        return rec, []
    others = dict((r["session"], r["paths"]) for r in registrations()
                  if r.get("session") != sid)
    found, subject, problems = resolve(top, words, cwd, others)
    if problems:
        return None, problems
    if rec:
        if found == sorted(rec["paths"]):
            return rec, []
        return None, ["session %s already holds %s. `board code %s --end` or "
                      "`--abandon` it before holding other paths"
                      % (sid, ", ".join(rec["paths"]), sid)]
    from . import worktree
    busy = worktree.busy_reason(top)
    if busy:
        return None, ["%s, so nothing is held" % busy]
    code, base = _git(top, "rev-parse", "HEAD")
    if code != 0:
        return None, ["this checkout has no commit to start from"]
    rec = {"session": sid, "subject": subject, "paths": found, "base": base,
           "last": base, "step": 0, "root": os.path.realpath(top),
           "started": round(float(now or time.time()), 3)}
    _save(rec)
    return rec, []


# ---------------------------------------------------------------------------
# trees through a temporary index
# ---------------------------------------------------------------------------
class _Index(object):
    """A scratch index, removed on exit. `env` points git at it."""

    def __enter__(self):
        self.dir = tempfile.mkdtemp(prefix="board-code-")
        self.env = {"GIT_INDEX_FILE": os.path.join(self.dir, "index")}
        return self

    def __exit__(self, *exc):
        shutil.rmtree(self.dir, ignore_errors=True)
        return False


def _present(top, held_paths, env):
    """The held paths `git add` can be given: on disk, or in the index."""
    out = []
    for p in held_paths:
        if os.path.lexists(os.path.join(top, p)) or _git(
                top, "ls-files", "--error-unmatch", "--", p, env=env)[0] == 0:
            out.append(p)
    return out


def _fill(top, start, held_paths, env):
    """`read-tree <start>`, then the held paths as the working tree has them.
    "" or the error."""
    code, out = _git(top, "read-tree", start, env=env)
    if code != 0:
        return "read-tree failed: %s" % out
    there = _present(top, held_paths, env)
    if there:
        code, out = _git(top, "add", "-A", "--", *there, env=env)
        if code != 0:
            return "git add failed: %s" % out
    return ""


def tree(top, start, held_paths):
    """`(tree, error)`: `start`'s tree with the held paths as on disk."""
    with _Index() as ix:
        err = _fill(top, start, held_paths, ix.env)
        if err:
            return "", err
        code, out = _git(top, "write-tree", env=ix.env)
        return (out, "") if code == 0 else ("", "write-tree failed: %s" % out)


def _changed(top, a, b, held_paths=None):
    """Paths that differ between two tree-ishes, under `held_paths` if given."""
    args = ["diff-tree", "-r", "--name-only", "--no-renames", a, b]
    if held_paths:
        args += ["--"] + list(held_paths)
    code, out = _git(top, *args)
    return [l for l in out.splitlines() if l.strip()] if code == 0 else []


def gate(top, held_paths):
    """Every refusal the commit-time gate gives what the held paths change
    against HEAD: the audit, `leaving.refused` and the participant scan, as
    `.githooks/pre-commit` asks them (`audit.gate`). `[]` is a pass. A gate
    that cannot run refuses."""
    from . import audit
    with _Index() as ix:
        err = _fill(top, "HEAD", held_paths, ix.env)
        if err:
            return ["the gate could not stage the step: %s" % err]
        old = os.environ.get("GIT_INDEX_FILE")
        os.environ["GIT_INDEX_FILE"] = ix.env["GIT_INDEX_FILE"]
        try:
            return audit.gate(top, top, False)
        except Exception as exc:                             # noqa: BLE001
            return ["the gate failed (%s), so nothing was sent"
                    % type(exc).__name__]
        finally:
            if old is None:
                os.environ.pop("GIT_INDEX_FILE", None)
            else:
                os.environ["GIT_INDEX_FILE"] = old


def apply(top, last, tip, held_paths):
    """Bring the held paths to `tip`: `git checkout <tip> -- <paths>` through a
    scratch index, and a file `tip` removed is removed. "" or the error."""
    gone = _changed(top, last, tip, held_paths)
    code, out = _git(top, "ls-tree", "-r", "--name-only", tip, "--",
                     *held_paths)
    keep = [l for l in out.splitlines() if l.strip()] if code == 0 else []
    with _Index() as ix:
        code, out = _git(top, "read-tree", tip, env=ix.env)
        if code != 0:
            return "read-tree failed: %s" % out
        if keep:
            code, out = _git(top, "checkout", tip, "--", *keep, env=ix.env)
            if code != 0:
                return "checkout failed: %s" % out
    for rel in gone:
        if rel not in keep:
            try:
                os.remove(os.path.join(top, rel))
            except OSError:
                pass
    return ""


# ---------------------------------------------------------------------------
# is output open here: may a check's output leave this subject whole
# ---------------------------------------------------------------------------
def output_open(root, names_phi=None, cfg=None):
    """True only when a check's full output may go back to the tutor.

    It fails closed. All four must hold, and anything else closes it:

      1. its `tutorboard.json` says `"phi": false` literally, on disk;
      2. and at HEAD (`_head_phi`), so an uncommitted edit opens nothing;
      3. the subject holds no fence (`fenced.holds`);
      4. the lab's PHI policy loaded (`names_phi`), so a checkout without the
         private `ai-config` is closed.

    `names_phi` and `cfg` are for a caller that already has them; left None
    they are read here.
    """
    from .course import config
    try:
        cfg = cfg if cfg is not None else config.read_config(root)
        if cfg.get("phi") is not False or _head_phi(root) is not False:
            return False
        if fenced.holds(root):
            return False
        if names_phi is None:
            names_phi = _policy(root)
        return callable(names_phi)
    except Exception:                                        # noqa: BLE001
        return False


def _head_phi(root):
    """What the committed `tutorboard.json` says for `"phi"`: True or False
    literally, else None (no file at HEAD, bad JSON, no key, not a bool)."""
    code, out = _git(root, "show", "HEAD:./tutorboard.json", timeout=20)
    if code != 0:
        return None
    try:
        said = json.loads(out)
    except ValueError:
        return None
    phi = said.get("phi") if isinstance(said, dict) else None
    return phi if isinstance(phi, bool) else None


def _policy(root=None):
    try:
        from . import leaving
        return leaving.policy()
    except Exception:                                        # noqa: BLE001
        return None


# ---------------------------------------------------------------------------
# the check
# ---------------------------------------------------------------------------
def check_spec(spec, files):
    """`(check, problems)`: the subject's declared check, made concrete for
    these held paths. PURE.

    `one` is used when it can be filled from exactly one held path, `all`
    otherwise. Each placeholder value is a subject path, never an option:

        {dir}     the held directory, or the held file's directory
        {file}    the held file
        {module}  the held path, dotted, its extension dropped:
                  `Exercises/Sets/E01.lean` is `Exercises.Sets.E01`

    `files` is `[(rel, is_dir)]`, relative to the subject.
    """
    if not spec:
        return None, []
    one, every = spec.get("one"), spec.get("all")
    if one and len(files or []) == 1:
        rel, is_dir = files[0]
        values = {"{dir}": rel if is_dir else (os.path.dirname(rel) or "."),
                  "{module}": os.path.splitext(rel)[0].replace("/", ".")}
        if not is_dir:
            values["{file}"] = rel
        argv, bad = [], []
        for word in one:
            for hole in re.findall(r"\{[^}]*\}", word):
                val = values.get(hole)
                if val is None:
                    bad.append("%s needs a held file, and %s is a directory"
                               % (hole, rel))
                    continue
                if (val != "." and exports.rel(val) != val) \
                        or val.startswith("-") or "{" in val:
                    bad.append("%r is not a path a check may be given" % val)
                    continue
                word = word.replace(hole, val)
            argv.append(word)
        if not bad:
            return {"spec": "one", "argv": argv}, []
        if not every:
            return None, bad
    if every:
        return {"spec": "all", "argv": list(every)}, []
    return None, ["the subject's check has only `one`, which needs exactly "
                  "one held path"]


def check_label(chk):
    """How a check is written in a message."""
    if not chk:
        return "none"
    if chk.get("script"):
        return chk["script"]
    return " ".join(chk.get("argv") or [])


def _program_ok(word, tracked_paths):
    from .course import config
    if word in config.CHECK_PROGRAMS:
        return True
    return config.check_program(word) and word in set(tracked_paths or ())


def tracked(root):
    """Subject-relative paths tracked and unchanged at HEAD, that resolve
    inside the subject: a tracked symlink to another subject's script is not
    this subject's check."""
    def lines(*args):
        code, out = _git(root, *args, timeout=30)
        return [x for x in out.split("\0") if x] if code == 0 else []
    have = set(lines("ls-files", "-z", "--", "."))
    changed = set(lines("diff", "--name-only", "-z", "--relative", "HEAD",
                        "--", "."))
    real = os.path.realpath(root)
    return set(p for p in have - changed
               if os.path.realpath(os.path.join(real, p)).startswith(real + os.sep))


def relay_lines(text, names_phi=None):
    """`(lines, withheld)`: what a message may carry out of a program's output.

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


def check_output(text, root, names_phi, top=None):
    """`{output, output_total, output_cut, withheld}`: a check's whole output,
    fit for a public commit. PURE. For an OPEN subject only.

    1. ANSI codes and control characters go.
    2. The subject's absolute path, its real path and the repository's top
       become relative, so `leetcode/x/x_test.go:12` stays readable.
    3. Each line goes through `relay.public`: any other absolute or home path
       becomes `<path>`, and a line `names_phi` flags is withheld and counted.
    4. The first `OUT_HEAD` and last `OUT_TAIL` lines are kept, each cut to
       `MAX_LINE`, at most `OUT_BYTES` in all, and the cut is marked.
    """
    from . import relay
    prefixes = []
    for base in (root, os.path.realpath(root) if root else "",
                 top, os.path.realpath(top) if top else ""):
        if base and base not in prefixes:
            prefixes.append(base.rstrip("/"))
    prefixes.sort(key=len, reverse=True)
    pats = [re.compile(re.escape(b) + r"(?:/|(?![\w.-]))") for b in prefixes]
    kept, withheld = [], 0
    for raw in (text or "").splitlines():
        line = ANSI_RE.sub("", raw.rstrip("\r")).expandtabs(4)
        for pat in pats:
            line = pat.sub(lambda m: "" if m.group(0).endswith("/") else ".",
                           line)
        indent = len(line) - len(line.lstrip(" "))
        said = relay.public(line, names_phi, MAX_LINE - min(indent, 40))
        if said is None:
            withheld += 1
            continue
        if not said:
            continue
        kept.append(" " * min(indent, 40) + said)
    total = len(kept)
    if total > OUT_HEAD + OUT_TAIL:
        head, tail = kept[:OUT_HEAD], kept[-OUT_TAIL:]
    else:
        head, tail = kept, []
    size = sum(len(x) + 1 for x in head + tail)
    while size > OUT_BYTES and (head or tail):
        gone = head.pop() if head else tail.pop(0)
        size -= len(gone) + 1
    cut = total - len(head) - len(tail)
    out = head + (["… %d line%s cut …" % (cut, "" if cut == 1 else "s")]
                  if cut else []) + tail
    return {"output": out, "output_total": total, "output_cut": cut,
            "withheld": withheld}


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


def _argv_env(root, chk, cfg_path=None):
    """`(argv, env)` for a check, run without a shell."""
    env = dict(os.environ)
    if chk.get("script"):
        return check_argv(root, chk["script"]), env
    argv = list(chk.get("argv") or [])
    from .course import config
    if argv and argv[0] not in config.CHECK_PROGRAMS:
        argv[0] = os.path.join(root, argv[0])
    if cfg_path:
        env["PATH"] = os.pathsep.join(list(cfg_path) + [env.get("PATH", "")])
    return argv, env


def run_check(root, chk, run=subprocess.run, timeout=CHECK_SECONDS,
              names_phi=None, open_=False, path=None):
    """Run a check here, from the subject's root.

    `{exit, relay, withheld, crash, seconds}`, and in an OPEN subject
    (`output_open`) also `output`, `output_total` and `output_cut`: stdout and
    stderr merged, through `check_output`. In a closed one nothing else of the
    output is kept: a check prints `RELAY:` lines for the message and anything
    else for the owner's own eyes, and that stays in this terminal.

    `chk` is `{"spec", "argv"}` or `{"script"}`, or a bare script path.
    `path` is the subject check's `path`, put in front of PATH.
    """
    if isinstance(chk, str):
        chk = {"script": chk}
    argv, env = _argv_env(root, chk, path)
    t0 = time.time()
    try:
        p = run(argv, cwd=root, env=env, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT if open_ else subprocess.PIPE,
                universal_newlines=True, timeout=timeout)
        code, out, err = p.returncode, p.stdout or "", p.stderr or ""
    except subprocess.TimeoutExpired:
        code, out, err = 124, "", "TimeoutExpired"
    except OSError as exc:
        code, out, err = 127, "", type(exc).__name__
    lines, withheld = relay_lines(out, names_phi)
    got = {"exit": code, "relay": lines, "seconds": round(time.time() - t0, 1)}
    if open_:
        whole = check_output(out + err, root, names_phi, top_of(root) or None)
        withheld += whole.pop("withheld")
        got.update(whole)
    if withheld:
        got["withheld"] = withheld
    if code != 0:
        crash = crash_type(out + err if open_ else err)
        if crash:
            got["crash"] = crash
    return got


def step_check(top, rec, run=subprocess.run):
    """`(result, open_)` for the subject's check over the held paths.

    `result` has `state` pass, fail or none; `label`; `why` where none; and
    what `run_check` returns. Without the PHI policy no `RELAY:` line is kept.
    """
    from . import leaving
    from .course import config
    sroot = os.path.join(top, rec["subject"])
    names_phi = leaving.policy(top)
    cfg = config.read_config(sroot)
    open_ = output_open(sroot, names_phi=names_phi, cfg=cfg)
    spec = cfg.get("check")
    if not spec:
        return {"state": "none", "label": "none",
                "why": "the subject's tutorboard.json declares no check"}, open_
    rels = []
    for p in rec["paths"]:
        sub = p[len(rec["subject"]) + 1:]
        rels.append((sub, os.path.isdir(os.path.join(top, p))))
    chk, bad = check_spec(spec, rels)
    if not chk:
        return {"state": "none", "label": "none", "why": "; ".join(bad)}, open_
    if not _program_ok(chk["argv"][0], tracked(sroot)):
        return {"state": "none", "label": check_label(chk),
                "why": "it runs %s, which is not tracked and unchanged at HEAD"
                       % chk["argv"][0]}, open_
    got = run_check(sroot, chk, run=run, names_phi=names_phi, open_=open_,
                    path=spec.get("path"))
    if names_phi is None:
        got["relay"] = []
    got["state"] = "pass" if got["exit"] == 0 else "fail"
    got["label"] = check_label(chk)
    return got, open_


def message(rec, n, changed, got, open_, ran_at):
    """A step's commit message. Public: every line in it is a file name, a
    number, or what `run_check` already made public."""
    state = got.get("state") or "none"
    shown = ", ".join(changed[:3]) + (" and %d more" % (len(changed) - 3)
                                      if len(changed) > 3 else "")
    lines = ["Step %d (check: %s): %s" % (n, state, shown), "",
             "Step %d" % n,
             "check: %s" % state,
             "session: %s" % rec["session"],
             "subject: %s" % rec["subject"],
             "paths: %s" % ", ".join(rec["paths"]),
             "files: %s" % ", ".join(changed),
             "ran_at: %s" % (ran_at or "unknown")]
    if state != "none":
        lines.append("command: %s" % got.get("label"))
        lines.append("exit: %s%s" % (got.get("exit"), ", " + got["crash"]
                                     if got.get("crash") else ""))
    elif got.get("why"):
        lines.append("why none: %s" % got["why"])
    for line in got.get("relay") or []:
        lines.append("RELAY: %s" % line)
    if got.get("withheld"):
        lines.append("withheld: %d line(s) the PHI policy flagged"
                     % got["withheld"])
    if open_ and got.get("output") is not None:
        lines.append("output: %d line(s)%s" % (
            got.get("output_total") or 0,
            ", %d cut from the middle" % got["output_cut"]
            if got.get("output_cut") else ""))
        lines.extend("    " + x for x in got["output"])
    elif state != "none":
        lines.append("output: closed here (phi is not literally false), so "
                     "RELAY: lines only")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# the loop
# ---------------------------------------------------------------------------
def signature(top, held_paths):
    """`(signature, newest mtime)` of everything under the held paths."""
    sig, newest = [], 0.0
    for p in held_paths:
        full = os.path.join(top, p)
        if not os.path.lexists(full):
            sig.append((p, "missing"))
            continue
        todo = [full]
        while todo:
            here = todo.pop()
            try:
                st = os.lstat(here)
            except OSError:
                continue
            sig.append((os.path.relpath(here, top), st.st_mtime_ns, st.st_size))
            newest = max(newest, st.st_mtime)
            if os.path.isdir(here) and not os.path.islink(here):
                try:
                    names = os.listdir(here)
                except OSError:
                    continue
                todo.extend(os.path.join(here, n) for n in names
                            if n not in SKIP_DIRS and not fenced.in_fence(n))
    return tuple(sorted(sig, key=str)), newest


class Loop(object):
    """One registered session, watched. `tick()` is one poll."""

    def __init__(self, top, rec, say=print, clock=time.time,
                 run=subprocess.run):
        self.top, self.rec, self.say, self.clock, self.run = (
            top, rec, say, clock, run)
        self.sig = None
        self.changed_at = 0.0
        self.checked = None
        self.fetched_at = None
        self.retry_at = 0.0
        self.waiting = None
        self.stopped = False
        self.said = set()

    def _once(self, line):
        if line not in self.said:
            self.said.add(line)
            self.say(line)

    def tick(self, fetch=None):
        """Fetch when due (or when `fetch`), then snapshot after the quiet.
        True when a step was pushed."""
        now = self.clock()
        if fetch or (fetch is None and (self.fetched_at is None
                                        or now - self.fetched_at >= FETCH_EVERY)):
            self.fetched_at = now
            self.remote()
        if self.stopped or self.waiting:
            return False
        sig, newest = signature(self.top, self.rec["paths"])
        if sig != self.sig:
            if self.sig is not None:
                self.changed_at = now
            self.sig = sig
        if now - max(newest, self.changed_at) < QUIET or now < self.retry_at:
            return False
        if sig == self.checked:
            return False
        self.checked = sig
        return self.snapshot()

    def remote(self):
        """Apply a commit on `code/<session>` the loop did not make."""
        rec, top = self.rec, self.top
        sid = rec["session"]
        tip, err = remote_tip(top, sid)
        if err:
            self._once(err)
            return
        if not tip:
            if rec.get("pushed"):
                self.say("code/%s is gone from origin: the session was ended "
                         "or abandoned elsewhere. Stopped watching; the "
                         "registration stays until `board code %s --abandon`."
                         % (sid, sid))
                self.stopped = True
            return
        if tip == rec["last"]:
            self.waiting = None
            return
        if not _ancestor(top, rec["last"], tip):
            if _ancestor(top, tip, rec["last"]):
                return
            self._once("code/%s moved to %s, which does not hold the last "
                       "step %s. Waiting; `--end` or `--abandon` settles it."
                       % (sid, tip[:12], rec["last"][:12]))
            self.waiting = tip
            return
        ok, said = settle(top, rec, tip)
        if ok:
            self.waiting = None
            self.checked = None
            self.say(said)
        else:
            self.waiting = tip
            self._once(said)

    def snapshot(self):
        rec, top = self.rec, self.top
        parent = rec["last"]
        new, err = tree(top, parent, rec["paths"])
        if err:
            self.say("step not sent: %s" % err)
            return False
        if new == _tree_of(top, parent):
            return False
        changed = _changed(top, parent, new)
        refused = gate(top, rec["paths"])
        if refused:
            self.say("step not sent, the commit-time gate refuses it:")
            for line in refused:
                self.say("  " + line)
            return False
        n = int(rec.get("step") or 0) + 1
        self.say("step %d: %s -- running the check" % (n, ", ".join(changed[:6])))
        got, open_ = step_check(top, rec, run=self.run)
        code, ran_at = _git(top, "rev-parse", "--short", "HEAD")
        msg = message(rec, n, changed, got, open_, ran_at if code == 0 else "")
        code, sha = _git(top, "commit-tree", new, "-p", parent, "-F", "-",
                         input=msg)
        if code != 0:
            self.say("step not sent: commit-tree failed: %s" % sha)
            return False
        code, out = _git(top, "push", "--quiet", "origin",
                         "%s:%s" % (sha, ref(rec["session"])), timeout=180)
        if code != 0:
            self.say("step %d is not pushed (%s); tried again shortly"
                     % (n, (out.splitlines() or ["no answer"])[-1]))
            self.checked = None
            self.retry_at = self.clock() + FETCH_EVERY
            self.fetched_at = None
            return False
        _git(top, "update-ref", tracking(rec["session"]), sha)
        rec.update(last=sha, step=n, pushed=True)
        _save(rec)
        for line in got.get("relay") or []:
            self.say("  RELAY: " + line)
        self.say("step %d pushed to code/%s: check %s%s" % (
            n, rec["session"], got.get("state"),
            "" if got.get("state") == "none" else ", exit %s" % got.get("exit")))
        return True


def settle(top, rec, tip):
    """Take `tip`, a commit on `code/<session>` after `last`. `(ok, said)`.

    Applied when the held paths are unchanged since `last`, or adopted when
    they already match it; otherwise refused, naming both sides' files.
    """
    sid = rec["session"]
    here, err = tree(top, rec["last"], rec["paths"])
    if err:
        return False, "could not read the held paths: %s" % err
    mine = _changed(top, rec["last"], here)
    theirs = _changed(top, rec["last"], tip, rec["paths"])
    outside = [p for p in _changed(top, rec["last"], tip)
               if p not in theirs]
    note = ("" if not outside else
            " It also changes %s, outside the held paths; that is not applied "
            "here and does not reach main at --end." % ", ".join(outside[:6]))
    if not mine:
        err = apply(top, rec["last"], tip, rec["paths"])
        if err:
            return False, "could not apply code/%s at %s: %s" % (
                sid, tip[:12], err)
        how = "applied"
    elif not _changed(top, here, tip, rec["paths"]):
        how = "matched"
    else:
        return False, ("both sides changed: %s here, %s on code/%s (%s). "
                       "Waiting: put the held files back as the last step had "
                       "them, or settle it by hand."
                       % (", ".join(mine), ", ".join(theirs) or "nothing held",
                          sid, tip[:12]))
    _, subject = _git(top, "log", "-1", "--format=%s", tip)
    rec["last"] = tip
    rec["pushed"] = True
    _save(rec)
    return True, "%s %s from code/%s: %s%s" % (how, tip[:12], sid, subject, note)


def watch(top, rec, say=print, sleep=time.sleep, clock=time.time,
          ticks=None, run=subprocess.run):
    """The loop: a tick every `POLL` seconds until Ctrl-C. Exit code."""
    loop = Loop(top, rec, say=say, clock=clock, run=run)
    say("holding %s for session %s. Each pause of %d s is a step, pushed to "
        "code/%s with its check. Ctrl-C stops watching; `board code %s --end` "
        "commits to main." % (", ".join(rec["paths"]), rec["session"],
                              int(QUIET), rec["session"], rec["session"]))
    try:
        while not loop.stopped:
            loop.tick()
            if ticks is not None:
                ticks -= 1
                if ticks <= 0:
                    break
            sleep(POLL)
    except KeyboardInterrupt:
        say("\nstopped watching. Session %s stays open: `board code %s` "
            "resumes it, `--end` commits it to main, `--abandon` drops it."
            % (rec["session"], rec["session"]))
    return 1 if loop.stopped else 0


# ---------------------------------------------------------------------------
# --end and --abandon
# ---------------------------------------------------------------------------
def _lock(top, wait):
    """`relay/.lock`, held, or None after `wait` seconds."""
    path = os.path.join(top, LOCK)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fh = open(path, "a+")
    deadline = time.time() + wait
    while True:
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return fh
        except OSError:
            if time.time() >= deadline:
                fh.close()
                return None
            time.sleep(1)


def _drop_ref(top, sid):
    """Delete `code/<sid>` on origin, where it is. "" or the error."""
    tip, err = remote_tip(top, sid)
    if err:
        return err
    if tip:
        code, out = _git(top, "push", "--quiet", "origin", ":" + ref(sid),
                         timeout=180)
        if code != 0:
            return "could not delete code/%s on origin: %s" % (
                sid, (out.splitlines() or ["no answer"])[-1])
    _git(top, "update-ref", "-d", tracking(sid))
    return ""


def end(top, sid, title=None, say=print, wait=LOCK_WAIT):
    """`--end`: the held paths as one commit on main, pushed; then the ref
    and the registration go. Exit code."""
    from . import gitops
    rec = read(sid, top)
    if not rec:
        say("board code: no coding session %s is held in this checkout" % sid)
        return 1
    fh = _lock(top, wait)
    if fh is None:
        say("board code: a relay pass held %s for %d s; nothing was ended. "
            "Try again." % (LOCK, wait))
        return 1
    try:
        tip, err = remote_tip(top, sid)
        if err:
            say("board code: nothing was ended: " + err)
            return 1
        if tip and tip != rec["last"]:
            if not _ancestor(top, rec["last"], tip):
                say("board code: code/%s is at %s, which does not hold the "
                    "last step. Nothing was ended; `--abandon` drops it."
                    % (sid, tip[:12]))
                return 1
            ok, said = settle(top, rec, tip)
            say(said)
            if not ok:
                say("board code: nothing was ended.")
                return 1
        code, branch = _git(top, "symbolic-ref", "--quiet", "--short", "HEAD")
        if code != 0:
            say("board code: HEAD is detached; nothing was ended")
            return 1
        code, out = _git(top, "fetch", "--quiet", "origin", branch, timeout=120)
        if code != 0:
            say("board code: could not fetch origin/%s, so nothing was "
                "ended: %s" % (branch, (out.splitlines() or [""])[-1]))
            return 1
        up = "refs/remotes/origin/%s" % branch
        here, err = tree(top, "HEAD", rec["paths"])
        if err:
            say("board code: " + err)
            return 1
        mine = set(_changed(top, "HEAD", here))
        code, out = _git(top, "diff", "--name-only", "HEAD..." + up, "--",
                         *rec["paths"])
        theirs = set(l for l in out.splitlines() if l.strip()) if code == 0 \
            else set()
        clash = sorted(mine & theirs)
        if clash:
            say("board code: main changed %s too, since this checkout last "
                "pulled. Nothing was committed; merge them by hand, then "
                "--end again." % ", ".join(clash))
            return 1
        behind = _git(top, "rev-list", "--count", "HEAD.." + up)[1]
        ahead = _git(top, "rev-list", "--count", up + "..HEAD")[1]
        if behind not in ("", "0") and ahead in ("", "0"):
            code, out = _git(top, "merge", "--ff-only", "--quiet", up)
            if code != 0:
                say("board code: could not fast-forward to origin/%s, so "
                    "nothing was committed: %s"
                    % (branch, (out.splitlines() or [""])[-1]))
                return 1
        with _Index() as ix:
            _git(top, "read-tree", "HEAD", env=ix.env)
            there = _present(top, rec["paths"], ix.env)
        title = (title or "").strip() or "%s, coached at the cluster (%d step%s)" % (
            ", ".join(rec["paths"][:3]), int(rec.get("step") or 0),
            "" if int(rec.get("step") or 0) == 1 else "s")
        msg = "%s: %s" % (rec["subject"], title.splitlines()[0])
        if there:
            ok, said = gitops.commit(top, there, msg)
            if not ok:
                say("board code: %s\nNothing was ended." % said)
                return 1
            say(said)
        ok, said = gitops.push(top)
        if not ok:
            say("board code: the commit is made here and NOT pushed: %s\n"
                "The session stays open; --end again pushes it." % said)
            return 1
        say(said)
        err = _drop_ref(top, sid)
        if err:
            say("board code: main is pushed, but " + err)
            return 1
        forget(sid)
        say("session %s ended: its paths are committed to %s and code/%s is "
            "gone." % (sid, branch, sid))
        return 0
    finally:
        fh.close()


def abandon(top, sid, say=print):
    """`--abandon`: the ref and the registration go; the tree stays."""
    rec = read(sid, top)
    err = _drop_ref(top, sid)
    if err:
        say("board code: " + err)
        return 1
    forget(sid)
    say("session %s abandoned: code/%s is gone%s. The working tree is as it "
        "was." % (sid, sid, "" if rec else " (nothing was registered here)"))
    return 0


# ---------------------------------------------------------------------------
# a request pinned to the session's ref
# ---------------------------------------------------------------------------
def pin_ok(root, sid, commit):
    """May a request filed from session `sid` run at `commit` here, though HEAD
    lacks it? Yes when a coding session `sid` is registered for this checkout,
    `commit` is an ancestor of `origin/code/<sid>`, and the held paths at
    `commit` are the working tree's."""
    top = top_of(root)
    rec = read(sid, top) if top else None
    if not rec or not isinstance(commit, str):
        return False
    tip, err = remote_tip(top, sid)
    if err or not tip or not _ancestor(top, commit, tip):
        return False
    here, err = tree(top, commit, rec["paths"])
    return not err and here == _tree_of(top, commit)


# ---------------------------------------------------------------------------
# the command
# ---------------------------------------------------------------------------
def main(argv, top=None, say=print, cwd=None):
    """`board code ...`. Exit code."""
    argv = list(argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        say(USAGE)
        return 0
    if top is None:
        from . import subjects
        top = top_of(subjects.root()) or subjects.root()
    if argv[0] == "--list":
        recs = registrations(top)
        for rec in recs:
            say("%s  %s  step %s  %s" % (rec["session"], rec["subject"],
                                         rec.get("step") or 0,
                                         ", ".join(rec["paths"])))
        if not recs:
            say("no coding session is held here")
        return 0
    sid, rest = argv[0], argv[1:]
    if "--end" in rest:
        title = None
        if "--title" in rest:
            i = rest.index("--title")
            title = rest[i + 1] if i + 1 < len(rest) else ""
        return end(top, sid, title=title, say=say)
    if "--abandon" in rest:
        return abandon(top, sid, say=say)
    bad = [w for w in rest if w.startswith("-")]
    if bad:
        say("board code: unknown option %s\n\n%s" % (bad[0], USAGE))
        return 2
    rec, problems = start(top, sid, rest, cwd=cwd or os.getcwd())
    if problems:
        say("board code: nothing is held:")
        for p in problems:
            say("  " + p)
        return 1
    return watch(top, rec, say=say)

