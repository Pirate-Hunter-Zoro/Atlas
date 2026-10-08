#!/usr/bin/env python3
"""`scripts/move-residue.sh` and PSYCH-ASR's `job_env.sh`, on temp trees only.

    python3 test/move_residue.py

A scratch repository holds a subject whose tracked files already moved from
research/ to projects/, with ignored residue left behind. Every run uses the
Mac's /bin/bash (3.2) where it exists. Fake `stat` and `find` on PATH stand in
for a second filesystem and record what got listed.
"""

import os
import shutil
import stat as statmod
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = os.path.dirname(HERE)
ROOT = os.path.dirname(BOARD)
SCRIPT = os.path.join(BOARD, "scripts", "move-residue.sh")
LIB = os.path.join(ROOT, "projects", "PSYCH-ASR", "slurm_jobs", "lib")
BASH = "/bin/bash" if os.path.exists("/bin/bash") else shutil.which("bash")

# Names that sit below a fenced directory: no output may ever carry them.
HIDDEN = ["ZZ0001_s1.wav", "ZZ0002_notes.txt", "ZZ0003.csv"]

fails = []


def check(name, cond, detail=""):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name + (("\n       " + str(detail)) if detail else ""))


def put(path, data, mode=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(data if isinstance(data, bytes) else data.encode())
    if mode is not None:
        os.chmod(path, mode)


def read(path):
    with open(path, "rb") as fh:
        return fh.read()


def git(repo, *args):
    return subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                           "-c", "core.hooksPath=/dev/null"] + list(args),
                          cwd=repo, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True)


def snapshot(top):
    """Every path under `top` with its type, mode and bytes or link target."""
    out = {}
    for dirpath, dirs, files in os.walk(top):
        if ".git" in dirs:
            dirs.remove(".git")
        for name in dirs + files:
            p = os.path.join(dirpath, name)
            st = os.lstat(p)
            rel = os.path.relpath(p, top)
            if statmod.S_ISLNK(st.st_mode):
                out[rel] = ("link", os.readlink(p))
            elif statmod.S_ISDIR(st.st_mode):
                out[rel] = ("dir", st.st_mode)
            else:
                out[rel] = ("file", st.st_mode, read(p))
    return out


def fakes(bin_dir):
    """A `stat` that reports device 999 for $FAKE_OTHER_DEV, and a `find`
    that logs its arguments to $FIND_LOG; both defer to the real tool."""
    real_stat = shutil.which("stat")
    real_find = shutil.which("find")
    put(os.path.join(bin_dir, "stat"), """#!/bin/sh
last=""
for a in "$@"; do last="$a"; done
if [ -n "${FAKE_OTHER_DEV:-}" ] && [ "$last" = "$FAKE_OTHER_DEV" ]; then
    "%s" "$@" >/dev/null 2>&1 || exit 1
    echo 999
    exit 0
fi
exec "%s" "$@"
""" % (real_stat, real_stat), 0o755)
    put(os.path.join(bin_dir, "find"), """#!/bin/sh
if [ -n "${FIND_LOG:-}" ]; then printf '%%s\\n' "$1" >> "$FIND_LOG"; fi
exec "%s" "$@"
""" % real_find, 0o755)


def build(base):
    """A repo whose projects/PSYCH-ASR is tracked and research/PSYCH-ASR holds
    only ignored residue. Returns (repo, old, new)."""
    repo = os.path.join(base, "repo")
    os.makedirs(repo)
    git(repo, "init", "-q")
    put(os.path.join(repo, ".gitignore"),
        "/projects/*/phi/\n/research/*/phi/\n.env\n__pycache__/\nresults/\n"
        ".venv/\nData/\nscratch.txt\n")
    new = os.path.join(repo, "projects", "PSYCH-ASR")
    old = os.path.join(repo, "research", "PSYCH-ASR")
    put(os.path.join(new, "README.md"), "tracked\n")
    put(os.path.join(new, "psych_asr", "config.py"), "X = 1\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "tracked")
    put(os.path.join(old, "phi", "inbox", HIDDEN[0]), "RIFF", 0o600)
    put(os.path.join(old, "phi", HIDDEN[1]), "x")
    put(os.path.join(old, "Data", HIDDEN[2]), "x")
    put(os.path.join(old, "psych_asr", "__pycache__", "config.cpython-311.pyc"), b"\0\1")
    put(os.path.join(old, "results", "run1", "summary.json"), "{}\n")
    put(os.path.join(old, ".venv", "bin", "python"), "#!/bin/sh\n", 0o755)
    os.symlink("bin/python", os.path.join(old, ".venv", "py"))
    put(os.path.join(old, "scratch.txt"), "notes\n")
    return repo, old, new


def write_env(old, new):
    """A .env with path values under both spellings of <old>, and values that
    are not paths. Returns (text, expected text after the move)."""
    logical_old = old
    physical_old = os.path.realpath(old)
    logical_new = new
    physical_new = os.path.realpath(new)
    keep = ("# comment naming %s/phi stays as it is\r\n"
            "TOKEN=s3cr3t-value\n"
            "  INDENTED=%s/x\n"
            "LIST=/elsewhere:%s/y\n"
            "URL=https://example.org%s\n"
            "EMPTY=\n"
            "SIBLING=%s-other/z\n"
            "not a line at all\n") % (old, old, old, old, old)
    paths = ("PSYCH_ASR_DATA=%s/phi\n"
             "export MODELS=\"%s/models dir\"\n"
             "CACHE='%s'\n") % (physical_old, logical_old, physical_old)
    want = ("PSYCH_ASR_DATA=%s/phi\n"
            "export MODELS=\"%s/models dir\"\n"
            "CACHE='%s'\n") % (physical_new, logical_new, physical_new)
    tail = "LAST=%s/tail" % logical_old           # no final newline
    tail_want = "LAST=%s/tail" % logical_new
    return keep + paths + tail, keep + want + tail_want


def run(args, base, extra=None):
    e = dict(os.environ)
    e["PATH"] = os.path.join(base, "bin") + os.pathsep + e.get("PATH", "")
    e["FIND_LOG"] = os.path.join(base, "find.log")
    e.pop("FAKE_OTHER_DEV", None)
    e.update(extra or {})
    return subprocess.run([BASH, SCRIPT] + list(args), cwd=base,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True, env=e)


def found_listed(base):
    try:
        with open(os.path.join(base, "find.log")) as fh:
            return [l.rstrip("\n") for l in fh]
    except FileNotFoundError:
        return []


def fenced_listed(base):
    return [l for l in found_listed(base)
            if os.path.basename(l).lower() in ("phi", "data")
            or "/phi/" in l.lower() or "/data/" in l.lower()]


def nothing_hidden(p):
    said = p.stdout + p.stderr
    return not any(h in said for h in HIDDEN)


def fresh(tag):
    base = tempfile.mkdtemp(prefix="tutor-move-residue-%s-" % tag)
    fakes(os.path.join(base, "bin"))
    return base


bases = []
try:
    # --- the dry run, then the move -------------------------------------------
    base = fresh("move")
    bases.append(base)
    repo, old, new = build(base)
    text, want = write_env(old, new)
    put(os.path.join(old, ".env"), text, 0o600)
    before = snapshot(repo)

    p = run([old, new], base)
    check("the dry run exits 0", p.returncode == 0, p.stderr)
    check("the dry run changes nothing", snapshot(repo) == before)
    check("the dry run names what would move",
          "would move\t%s\t" % os.path.join(os.path.realpath(old), "phi") in p.stdout
          and "would move\t%s\t" % os.path.join(os.path.realpath(old), ".env") in p.stdout,
          p.stdout)
    check("the dry run names the .env keys it would rewrite",
          all("would rewrite\t" in p.stdout and "\t%s\n" % k in p.stdout
              for k in ("PSYCH_ASR_DATA", "MODELS", "CACHE", "LAST")), p.stdout)
    check("the dry run prints no name below a fenced directory", nothing_hidden(p))

    p = run([old, new, "--apply"], base)
    after_new = os.path.join(new)
    check("--apply exits 0", p.returncode == 0, p.stderr + p.stdout)
    check("the ignored phi/ moved whole, contents and mode intact",
          read(os.path.join(new, "phi", "inbox", HIDDEN[0])) == b"RIFF"
          and statmod.S_IMODE(os.stat(os.path.join(new, "phi", "inbox", HIDDEN[0])).st_mode) == 0o600)
    check("a merged directory gains its residue beside the tracked file",
          os.path.isfile(os.path.join(new, "psych_asr", "__pycache__", "config.cpython-311.pyc"))
          and read(os.path.join(new, "psych_asr", "config.py")) == b"X = 1\n")
    check("results/, .venv/ and a symlink moved",
          os.path.isfile(os.path.join(new, "results", "run1", "summary.json"))
          and os.readlink(os.path.join(new, ".venv", "py")) == "bin/python")
    check("the .env moved and keeps its mode",
          statmod.S_IMODE(os.stat(os.path.join(new, ".env")).st_mode) == 0o600)
    got = read(os.path.join(new, ".env")).decode()
    check("path values are rewritten, both spellings, quotes kept", got == want,
          "\n--- got\n%s\n--- want\n%s" % (got, want))
    keep_lines = text.splitlines(True)[:8]
    check("non-path .env lines stay byte-identical",
          got.encode().startswith("".join(keep_lines).encode()))
    env_lines = [l for l in p.stdout.splitlines() if l.startswith("env\t")]
    check("only the changed key names are printed",
          sorted(l.split("\t")[2] for l in env_lines)
          == ["CACHE", "LAST", "MODELS", "PSYCH_ASR_DATA"]
          and "s3cr3t" not in p.stdout + p.stderr, env_lines)
    check("the old directory is gone, and the emptied research/ with it",
          not os.path.exists(old) and not os.path.exists(os.path.join(repo, "research")))
    check("every move is logged for a rollback",
          "moved\t%s\t%s" % (os.path.join(os.path.realpath(old), "phi"),
                             os.path.join(os.path.realpath(new), "phi")) in p.stdout
          and "rmdir\t%s" % os.path.realpath(old) in p.stdout
          and "rmdir\t%s" % os.path.realpath(os.path.join(repo, "research")) in p.stdout,
          p.stdout)
    check("nothing below phi/ or Data/ was ever listed, or printed",
          not fenced_listed(base) and nothing_hidden(p), fenced_listed(base))
    check("git sees no tracked change", git(repo, "status", "--porcelain").stdout == "",
          git(repo, "status", "--porcelain").stdout)

    # --- collisions -----------------------------------------------------------
    base = fresh("collide")
    bases.append(base)
    repo, old, new = build(base)
    put(os.path.join(new, "scratch.txt"), "the other one\n")
    put(os.path.join(new, "phi", "inbox", "x"), "")
    before = snapshot(repo)
    for args in ([old, new], [old, new, "--apply"]):
        p = run(args, base)
        check("a collision is refused (%s)" % " ".join(args[2:] or ["dry run"]),
              p.returncode != 0 and "collision: %s" % os.path.join(
                  os.path.realpath(new), "scratch.txt") in p.stderr
              and "collision: %s" % os.path.join(os.path.realpath(new), "phi") in p.stderr,
              p.stderr)
        check("and moves nothing", snapshot(repo) == before)
    check("a fenced directory on both sides is refused, never listed",
          not fenced_listed(base) and nothing_hidden(p), fenced_listed(base))

    # --- another filesystem ---------------------------------------------------
    base = fresh("device")
    bases.append(base)
    repo, old, new = build(base)
    before = snapshot(repo)
    p = run([old, new, "--apply"], base, {"FAKE_OTHER_DEV": os.path.realpath(new)})
    check("<new> on another filesystem is refused",
          p.returncode != 0 and "different filesystems" in p.stderr, p.stderr)
    check("and moves nothing", snapshot(repo) == before)
    p = run([old, new, "--apply"], base,
            {"FAKE_OTHER_DEV": os.path.join(os.path.realpath(old), "phi")})
    check("an entry mounted from another filesystem is refused",
          p.returncode != 0 and "on another filesystem: " in p.stderr, p.stderr)
    check("and moves nothing", snapshot(repo) == before)

    # --- git preconditions ----------------------------------------------------
    p = run([old, repo], base)
    q = run([repo, new], base)
    check("<old> inside <new> or the reverse is refused",
          p.returncode != 0 and "inside" in p.stderr
          and q.returncode != 0 and "inside" in q.stderr, p.stderr + q.stderr)
    os.makedirs(os.path.join(repo, "projects", "Empty"))
    p = run([old, os.path.join(repo, "projects", "Empty"), "--apply"], base)
    check("a <new> with no tracked files is refused",
          p.returncode != 0 and "no tracked files" in p.stderr, p.stderr)
    put(os.path.join(old, "kept.md"), "x\n")
    git(repo, "add", "research/PSYCH-ASR/kept.md")
    git(repo, "commit", "-q", "-m", "kept")
    before = snapshot(repo)
    p = run([old, new, "--apply"], base)
    check("an <old> still holding tracked files is refused",
          p.returncode != 0 and "still holds tracked files" in p.stderr, p.stderr)
    check("and moves nothing", snapshot(repo) == before)

    # --- job_env.sh: a missing data root stops the job ------------------------
    base = fresh("jobenv")
    bases.append(base)
    ws = os.path.join(base, "ws")
    shutil.copytree(LIB, os.path.join(ws, "slurm_jobs", "lib"),
                    ignore=shutil.ignore_patterns("__pycache__"))
    recipe = os.path.join(ws, "slurm_jobs", "job.sbatch")
    put(recipe, "#!/bin/bash\nset -e\nsource slurm_jobs/lib/job_env.sh\n"
                "echo reached\n")

    def job(extra=None):
        e = dict(os.environ)
        e.pop("PSYCH_ASR_DATA", None)
        e.update(extra or {})
        return subprocess.run([BASH, recipe], cwd=ws, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, universal_newlines=True, env=e)

    p = job()
    check("job_env.sh stops a job whose phi/ is missing",
          p.returncode != 0 and "reached" not in p.stdout
          and "RELAY: data root PSYCH_ASR_DATA does not exist" in p.stderr, p.stderr)
    check("and does not create it", not os.path.exists(os.path.join(ws, "phi")))
    check("its RELAY: line names no path",
          not any(l.startswith("RELAY:") and (base in l or os.path.realpath(base) in l)
                  for l in p.stderr.splitlines()),
          p.stderr)
    gone = os.path.join(base, "elsewhere", "data-root")
    p = job({"PSYCH_ASR_DATA": gone})
    check("an override pointing nowhere stops the job too, creating nothing",
          p.returncode != 0 and "reached" not in p.stdout
          and not os.path.exists(os.path.join(base, "elsewhere")), p.stderr)
    os.makedirs(os.path.join(ws, "phi"))
    p = job()
    check("with the data root present the job runs on",
          p.returncode == 0 and "reached" in p.stdout, p.stderr)
finally:
    for b in bases:
        shutil.rmtree(b, ignore_errors=True)

print()
if fails:
    print("%d check(s) failed" % len(fails))
    sys.exit(1)
print("move-residue.sh renames residue on one filesystem only, refuses "
      "collisions, never lists below a fence, and job_env.sh never recreates "
      "a data root")
