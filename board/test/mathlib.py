#!/usr/bin/env python3
"""Mathlib builds in the background, and nothing compiles it in the foreground.

`projects/Lean-Theorem-Proving/scripts/build-mathlib.sh` starts the build and
returns at once; `--status` exits 0 built, 1 missing, 2 running, 3 failed; the
project's `scripts/build.sh` refuses while Mathlib is anything but built,
because `lake build` would otherwise compile it inside a check; its
`scripts/setup.sh` starts the build and builds the exercises only once
Mathlib is built. Starts that overlap start one build; the build ignores the
hangup and interrupt of the terminal that started it and runs under
`caffeinate -is`; setup-mac.sh's step 7 starts it; and every script in the
project's scripts/ is committed executable, because each says to run it as
./scripts/<name>.

The scripts run on a copy of themselves, against a stub `lake` whose cache
fetch and build are steered by files, a mathlib checkout that is a one-commit
git repository, and a temp HOME and state directory.
"""

import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ATLAS = os.path.dirname(os.path.dirname(HERE))
LEAN = os.path.join(ATLAS, "projects", "Lean-Theorem-Proving")

fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


def write(path, text, mode=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    if mode:
        os.chmod(path, mode)


# `lake exe cache get` exits with ctl/cache_rc and sleeps ctl/cache_sleep
# seconds first. `lake build Mathlib` waits while ctl/hold exists, then exits
# with ctl/build_rc, writing Mathlib.olean when that is 0. Any other `lake
# build` is the exercises. Every call is one line in ctl/calls.
LAKE = r"""#!/bin/bash
ctl="$LAKE_CTL"
echo "$LEAN_NUM_THREADS $*" >> "$ctl/calls"
if [ "$1 $2 $3" = "exe cache get" ]; then
  [ -f "$ctl/cache_sleep" ] && sleep "$(cat "$ctl/cache_sleep")"
  exit "$(cat "$ctl/cache_rc" 2>/dev/null || echo 0)"
fi
if [ "$1 $2" = "build Mathlib" ]; then
  for _ in $(seq 600); do [ -f "$ctl/hold" ] || break; sleep 0.1; done
  rc="$(cat "$ctl/build_rc" 2>/dev/null || echo 0)"
  if [ "$rc" = 0 ]; then
    mkdir -p .lake/packages/mathlib/.lake/build/lib/lean
    touch .lake/packages/mathlib/.lake/build/lib/lean/Mathlib.olean
  fi
  exit "$rc"
fi
echo "warning: declaration uses 'sorry'"
exit 0
"""

# Real path: a script run by a relative path, as setup-mac.sh runs this one,
# names its checkout by the real path, and HOME must be a prefix of it.
base = os.path.realpath(tempfile.mkdtemp(prefix="tutor-mathlib-"))
try:
    home = os.path.join(base, "home")
    atlas = os.path.join(home, "Atlas")
    proj = os.path.join(atlas, "projects", "Lean-Theorem-Proving")
    ctl = os.path.join(base, "ctl")
    bin_ = os.path.join(base, "bin")
    slurm_bin = os.path.join(base, "slurm")
    os.makedirs(ctl)
    for name in ("build-mathlib.sh", "build.sh"):
        src = os.path.join(LEAN, "scripts", name)
        write(os.path.join(proj, "scripts", name), open(src, encoding="utf-8").read(), 0o755)
    write(os.path.join(proj, "lean-toolchain"), "leanprover/lean4:v4.34.1\n")
    write(os.path.join(bin_, "lake"), LAKE, 0o755)
    write(os.path.join(slurm_bin, "sbatch"), "#!/bin/bash\nexit 0\n", 0o755)

    git = os.path.dirname(shutil.which("git"))
    env = dict(os.environ)
    env.update({
        "HOME": home,
        "XDG_STATE_HOME": os.path.join(base, "state"),
        "PATH": os.pathsep.join([bin_, git, "/usr/bin", "/bin", "/usr/sbin", "/sbin"]),
        "LAKE_CTL": ctl,
        "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
    })
    for k in ("LEANTP_THREADS", "LEANTP_CACHE_TIMEOUT", "GIT_DIR", "GIT_WORK_TREE"):
        env.pop(k, None)

    mathlib = os.path.join(proj, ".lake", "packages", "mathlib")
    olean = os.path.join(mathlib, ".lake", "build", "lib", "lean", "Mathlib.olean")
    state = os.path.join(base, "state", "atlas-setup")
    stem = os.path.join(state, "mathlib-Atlas_projects_Lean-Theorem-Proving")

    def git_in(*args):
        return subprocess.run(["git", "-C", mathlib] + list(args), env=env, check=True,
                              capture_output=True, text=True).stdout.strip()

    def pin(rev):
        write(os.path.join(proj, "lake-manifest.json"), json.dumps({
            "version": "1.2.0", "packagesDir": ".lake/packages",
            "packages": [
                {"url": "https://github.com/leanprover-community/plausible",
                 "rev": "118aa17ee84656b8bd727fef7c458ee8c833385c", "name": "plausible"},
                {"url": "https://github.com/leanprover-community/mathlib4",
                 "rev": rev, "name": "mathlib"},
            ]}, indent=1))

    os.makedirs(mathlib)
    git_in("init", "-q")
    git_in("commit", "-q", "--allow-empty", "-m", "one")
    pin(git_in("rev-parse", "HEAD"))

    def run(script, *args, extra=None):
        e = dict(env, **(extra or {}))
        began = time.time()
        p = subprocess.run(["bash", os.path.join(proj, "scripts", script)] + list(args),
                           cwd=proj, env=e, capture_output=True, text=True, timeout=60)
        return p.returncode, p.stdout + p.stderr, time.time() - began

    def status():
        rc, out, _ = run("build-mathlib.sh", "--status")
        return rc, out

    def settle():
        for _ in range(300):
            rc, out = status()
            if rc != 2:
                return rc, out
            time.sleep(0.1)
        return rc, out

    def calls():
        try:
            with open(os.path.join(ctl, "calls"), encoding="utf-8") as fh:
                return fh.read().splitlines()
        except OSError:
            return []

    def reset_calls():
        if os.path.exists(os.path.join(ctl, "calls")):
            os.remove(os.path.join(ctl, "calls"))

    def hold(on):
        p = os.path.join(ctl, "hold")
        if on:
            write(p, "")
        elif os.path.exists(p):
            os.remove(p)

    def lock_pids():
        out = []
        lock = stem + ".lock"
        for f in os.listdir(lock) if os.path.isdir(lock) else []:
            with open(os.path.join(lock, f), encoding="utf-8") as fh:
                t = fh.read().strip()
            if t:
                out.append(int(t))
        return out

    # -----------------------------------------------------------------------
    # A. missing
    # -----------------------------------------------------------------------
    rc, out = status()
    check("with no Mathlib.olean, --status exits 1 and says missing",
          rc == 1 and "missing" in out)
    rc, out, took = run("build.sh")
    check("and build.sh refuses at once, without calling lake",
          rc == 1 and "NOT BUILT" in out and "missing" in out and took < 10 and not calls())
    rc, out, _ = run("build.sh", "Exercises.Sets.E01_InterComm")
    check("a one-module check is refused the same way", rc == 1 and not calls())

    # -----------------------------------------------------------------------
    # B. running: started in the background, under a caller's pipe
    # -----------------------------------------------------------------------
    hold(True)
    rc, out, took = run("build-mathlib.sh")
    check("a start returns at once with 'started', though stdout is a pipe the "
          "build never holds open", rc == 0 and out.startswith("started") and took < 10)
    rc, out = status()
    check("while it runs, --status exits 2 and names the log",
          rc == 2 and "running" in out and stem + ".log" in out)
    rc, out, _ = run("build-mathlib.sh")
    check("a second start says running and starts nothing", rc == 0 and out.startswith("running"))
    rc, out, took = run("build.sh")
    check("build.sh refuses while it runs, without calling lake build",
          rc == 1 and "building in the background" in out and took < 10
          and not any(c.split(" ", 1)[1] == "build" for c in calls()))
    with open(stem + ".status", encoding="utf-8") as fh:
        check("the status file says running", fh.read().strip() == "running")

    # -----------------------------------------------------------------------
    # C. built
    # -----------------------------------------------------------------------
    hold(False)
    rc, out = settle()
    check("when the build ends, --status exits 0 and says built", rc == 0 and out.strip() == "built")
    got = calls()
    cores = int(subprocess.run(["sysctl", "-n", "hw.ncpu"], capture_output=True,
                               text=True).stdout.strip() or "8")
    want = str(min(cores, 8))
    check("the cache is fetched first, then lake build Mathlib, once",
          [c.split(" ", 1)[1] for c in got] == ["exe cache get", "build Mathlib"])
    check("LEAN_NUM_THREADS is the core count capped at 8 (%s)" % want,
          all(c.split(" ", 1)[0] == want for c in got))
    check("the lock is gone and the log says how it ended",
          not os.path.exists(stem + ".lock")
          and "lake build exit status: 0" in open(stem + ".log", encoding="utf-8").read())
    reset_calls()
    rc, out, _ = run("build-mathlib.sh")
    check("a start on a built Mathlib says built and starts nothing",
          rc == 0 and out.strip() == "built" and not calls())
    rc, out, _ = run("build.sh")
    check("build.sh now builds", rc == 0 and "BUILD OK" in out and calls()[-1].endswith(" build"))
    reset_calls()

    # -----------------------------------------------------------------------
    # D. a mathlib checkout at another commit than the manifest pins
    # -----------------------------------------------------------------------
    git_in("commit", "-q", "--allow-empty", "-m", "two")
    rc, out = status()
    check("a mathlib checkout off the manifest's pin is missing, not built",
          rc == 1 and "lake-manifest.json" in out)
    rc, out, _ = run("build.sh")
    check("and build.sh refuses it rather than compile in the foreground",
          rc == 1 and not calls())
    pin(git_in("rev-parse", "HEAD"))
    check("pinned again, it is built", status()[0] == 0)

    # -----------------------------------------------------------------------
    # E. failed, under --source
    # -----------------------------------------------------------------------
    os.remove(olean)
    write(os.path.join(ctl, "build_rc"), "1")
    rc, out, _ = run("build-mathlib.sh", "--source")
    rc, out = settle()
    check("a build lake fails exits 3 on --status, naming the log",
          rc == 3 and out.startswith("failed") and stem + ".log" in out)
    check("--source never fetches the cache",
          [c.split(" ", 1)[1] for c in calls()] == ["build Mathlib"])
    rc, out, _ = run("build.sh")
    check("build.sh refuses a failed Mathlib", rc == 1 and "failed" in out)
    write(os.path.join(ctl, "build_rc"), "0")
    rc, out, _ = run("build-mathlib.sh")
    check("a start after a failure starts again and names the failed run's log",
          rc == 0 and out.startswith("started") and stem + ".prev.log" in out
          and os.path.exists(stem + ".prev.log"))
    check("and that build ends built", settle()[0] == 0)
    reset_calls()

    # -----------------------------------------------------------------------
    # F. stopped: by TERM, and by a kill nothing can trap
    # -----------------------------------------------------------------------
    os.remove(olean)
    hold(True)
    run("build-mathlib.sh", "--source")
    time.sleep(0.5)
    with open(stem + ".lock/run", encoding="utf-8") as fh:
        os.kill(int(fh.read().strip()), signal.SIGTERM)
    rc, out = settle()
    check("a build sent TERM records failed and drops its lock",
          rc == 3 and out.startswith("failed;") and not os.path.exists(stem + ".lock"))

    run("build-mathlib.sh", "--source")
    time.sleep(0.5)
    for pid in lock_pids():
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass
    time.sleep(0.3)
    rc, out = status()
    check("a build killed outright is failed, 'stopped without finishing'",
          rc == 3 and "stopped without finishing" in out)
    hold(False)
    time.sleep(0.5)  # the orphaned stub lake sees the hold gone and exits
    reset_calls()

    # -----------------------------------------------------------------------
    # G. threads, the cache cap, and Slurm
    # -----------------------------------------------------------------------
    rc, out, _ = run("build-mathlib.sh", extra={"LEANTP_THREADS": "nope"})
    check("LEANTP_THREADS that is not a whole number is refused before a start",
          rc == 64 and status()[0] == 3)
    write(os.path.join(ctl, "cache_sleep"), "30")
    rc, out, _ = run("build-mathlib.sh", extra={"LEANTP_THREADS": "3",
                                                "LEANTP_CACHE_TIMEOUT": "1"})
    rc, out = settle()
    log = open(stem + ".log", encoding="utf-8").read()
    check("LEANTP_THREADS overrides the cap", calls() and all(c.startswith("3 ") for c in calls()))
    check("a cache fetch past its cap is not retried; the build compiles instead",
          rc == 0 and "did not answer within 1s" in log
          and [c.split(" ", 1)[1] for c in calls()] == ["exe cache get", "build Mathlib"])
    os.remove(os.path.join(ctl, "cache_sleep"))

    os.remove(olean)
    slurm = {"PATH": slurm_bin + os.pathsep + env["PATH"]}
    rc, out, _ = run("build-mathlib.sh", extra=slurm)
    check("under Slurm a start is refused and points at the sbatch",
          rc == 1 and "build_mathlib.sbatch" in out and status()[0] == 1)
    rc, out, _ = run("build-mathlib.sh", "--status", extra=slurm)
    check("and --status still answers there", rc == 1)

    # -----------------------------------------------------------------------
    # H. the .tex branch of build.sh is not a Lean build and is never refused
    # -----------------------------------------------------------------------
    rc, out, _ = run("build.sh", os.path.join(base, "absent.tex"))
    check("build.sh on a .tex path answers for the .tex, not for Mathlib",
          rc == 1 and "no such file" in out and "NOT BUILT" not in out)

    # -----------------------------------------------------------------------
    # I. the project's setup.sh hands Mathlib over and never compiles it
    # -----------------------------------------------------------------------
    write(os.path.join(bin_, "elan"),
          '#!/bin/bash\ncase "$1" in\n  --version) echo "elan 4.0.0" ;;\n'
          '  toolchain) echo "leanprover/lean4:v4.34.1" ;;\nesac\n', 0o755)
    write(os.path.join(bin_, "lean"), '#!/bin/bash\necho "Lean (version 4.34.1)"\n', 0o755)
    for name in ("setup.sh", "status.sh"):
        src = os.path.join(LEAN, "scripts", name)
        write(os.path.join(proj, "scripts", name), open(src, encoding="utf-8").read(), 0o755)
    write(os.path.join(proj, "exercises.tsv"), "# order\ttopic\tmodule\ttitle\n")
    reset_calls()
    check("setup starts from a missing Mathlib", status()[0] == 1)

    hold(True)
    rc, out, took = run("setup.sh")
    check("setup.sh starts the build and returns at once, exit 0",
          rc == 0 and "Mathlib started" in out and took < 10)
    check("and builds no exercises while Mathlib builds",
          "exercises build once Mathlib has" in out
          and not any(c.split(" ", 1)[1] == "build" for c in calls()))
    rc, out, _ = run("setup.sh", "--check")
    check("setup.sh --check reports running and starts nothing",
          rc == 0 and "running" in out and status()[0] == 2)
    hold(False)
    check("the build setup.sh started ends built", settle()[0] == 0)
    reset_calls()
    rc, out, _ = run("setup.sh")
    check("setup.sh on a built Mathlib builds the exercises and nothing else",
          rc == 0 and "Mathlib built" in out and "lake build succeeded" in out
          and [c.split(" ", 1)[1] for c in calls()] == ["build"])
    reset_calls()

    os.remove(olean)
    rc, out, _ = run("setup.sh", extra=slurm)
    check("setup.sh under Slurm starts nothing and points at the sbatch",
          rc == 0 and "sbatch slurm_jobs/build_mathlib.sbatch" in out
          and not calls() and status()[0] == 1)

    # -----------------------------------------------------------------------
    def unbuild():
        if os.path.exists(olean):
            os.remove(olean)

    # J. starts that overlap start one build
    # -----------------------------------------------------------------------
    hold(True)
    reset_calls()
    script = os.path.join(proj, "scripts", "build-mathlib.sh")
    starts = [subprocess.Popen(["bash", script, "--source"], cwd=proj, env=env,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
              for _ in range(6)]
    said = [p.communicate(timeout=60)[0] for p in starts]
    time.sleep(0.5)
    check("six starts at once: one says started and five say running (%s)"
          % [o.split(" ", 1)[0] for o in said],
          sum(o.startswith("started") for o in said) == 1
          and sum(o.startswith("running") for o in said) == 5
          and all(p.returncode == 0 for p in starts))
    check("and lake build Mathlib runs once",
          [c.split(" ", 1)[1] for c in calls()] == ["build Mathlib"])
    check("no start's turn is left behind", not os.path.lexists(stem + ".starting"))
    hold(False)
    check("that one build ends built", settle()[0] == 0)

    unbuild()
    dead = subprocess.Popen(["true"])
    dead.wait()
    os.symlink(str(dead.pid), stem + ".starting")
    rc, out, took = run("build-mathlib.sh", "--source")
    check("a turn left by a start that died is cleared, and the start goes ahead",
          rc == 0 and out.startswith("started") and took < 10
          and not os.path.lexists(stem + ".starting"))
    check("and its build ends built", settle()[0] == 0)
    reset_calls()

    # -----------------------------------------------------------------------
    # K. the build outlives its terminal, and keeps the Mac awake
    # -----------------------------------------------------------------------
    unbuild()
    hold(True)
    caller = subprocess.Popen(["bash", script], cwd=proj, env=env, start_new_session=True,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    out = caller.communicate(timeout=60)[0]
    check("a start from a terminal of its own says started", out.startswith("started"))
    # caffeinate runs the build in its own pid and asserts beside it, as a
    # process of its own with the build's command line after its flags.
    if shutil.which("caffeinate"):
        everything = subprocess.run(["ps", "-axo", "command="], capture_output=True,
                                    text=True).stdout.splitlines()
        check("the build runs under caffeinate -is",
              "caffeinate -is bash %s --run" % script in [c.strip() for c in everything])
    for sig in (signal.SIGHUP, signal.SIGINT):
        try:
            os.killpg(caller.pid, sig)
        except OSError:
            pass
    time.sleep(1)
    rc, out = status()
    check("the terminal's hangup and interrupt leave the build running", rc == 2)
    hold(False)
    check("and it ends built", settle()[0] == 0)
    reset_calls()

    # -----------------------------------------------------------------------
    # L. setup-mac.sh's step 7, run from the Atlas root
    # -----------------------------------------------------------------------
    lines = open(os.path.join(ATLAS, "scripts", "setup-mac.sh"), encoding="utf-8").read().splitlines()
    head = [l for l in lines if l.startswith(("problems=0", "good()", "warn()"))]
    start = lines.index('echo "== 7. Mathlib"') if 'echo "== 7. Mathlib"' in lines else None
    step7 = []
    if start is not None:
        for l in lines[start:]:
            # Step 7 ends at the next step's header or the summary's blank echo;
            # step 8 loads a LaunchAgent and must never run here.
            if l == "echo" or (l.startswith('echo "== ') and step7):
                break
            step7.append(l)
    check("setup-mac.sh has its step 7 and its good and warn", len(head) == 3 and step7)
    step7_sh = os.path.join(base, "step7.sh")
    write(step7_sh, "\n".join(["set -uo pipefail"] + head + step7 + ['exit "$problems"']) + "\n")

    def step(cwd=atlas):
        p = subprocess.run(["bash", step7_sh], cwd=cwd, env=env, capture_output=True,
                           text=True, timeout=60)
        return p.returncode, p.stdout + p.stderr

    unbuild()
    hold(True)
    rc, out = step()
    check("on a missing Mathlib, step 7 starts the build (%r)" % out.strip(),
          rc == 0 and "ok    Mathlib started" in out and status()[0] == 2)
    rc, out = step()
    check("while it builds, step 7 says running", rc == 0 and "ok    Mathlib running" in out)
    hold(False)
    settle()
    rc, out = step()
    check("once it is built, step 7 says built", rc == 0 and "ok    Mathlib built" in out)
    rc, out = step(cwd=base)
    check("where there is no Lean project, step 7 says so",
          rc == 0 and "ok    no Lean project here" in out)
    reset_calls()

    # -----------------------------------------------------------------------
    # M. committed executable
    # -----------------------------------------------------------------------
    staged = subprocess.run(["git", "-C", ATLAS, "ls-files", "-s", "--",
                             "projects/Lean-Theorem-Proving/scripts/"],
                            capture_output=True, text=True).stdout.splitlines()
    modes = {l.split("\t", 1)[1].rsplit("/", 1)[1]: l.split(" ", 1)[0] for l in staged}
    check("every script in the project's scripts/ is committed 100755 (%s)"
          % sorted(n for n, m in modes.items() if m != "100755"),
          "build-mathlib.sh" in modes and all(m == "100755" for m in modes.values()))

finally:
    hold_path = os.path.join(base, "ctl", "hold")
    if os.path.exists(hold_path):
        os.remove(hold_path)
    time.sleep(0.3)
    shutil.rmtree(base, ignore_errors=True)

print()
if fails:
    print("%d FAILED" % len(fails))
    sys.exit(1)
print("all passed")
