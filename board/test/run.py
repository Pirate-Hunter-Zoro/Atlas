#!/usr/bin/env python3
"""Run every suite in board/test/.

    python3 board/test/run.py              every suite, four at a time
    python3 board/test/run.py -j 1         one at a time
    python3 board/test/run.py --guards     the PHI and relay guards only
    python3 board/test/run.py relay holds  only the suites named

A suite is any `*.py` or `*.js` file in this directory except those in
HELPERS. Discovery, not a list: a suite added here runs without anyone
registering it. Three checks that live outside this directory run with the
full set: Paper-Writer's unittests, `tools/sync-macros.py --check`, and
ai-config's own `scripts/test.sh` (the PHI policy's tests), which also runs
with --guards. Where ai-config is absent the run says SKIPPED, loudly.

Each suite runs with board/ as its working directory and this process's
environment, plus a page cache of its own (TUTORBOARD_PAGES). Suites in SERIAL never run beside each other.

Stdlib only.
"""

import argparse
import os
import shutil
import subprocess
import tempfile
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = os.path.dirname(HERE)
ROOT = os.path.dirname(BOARD)
FACTORY = os.path.join(ROOT, "projects", "Paper-Writer")
AI_CONFIG_TESTS = os.path.join(ROOT, "ai-config", "scripts", "test.sh")

# Files in this directory that are not suites. A helper other than this file
# is a shared case some suite requires; the run names the suites it runs in,
# and fails when none does.
HELPERS = ["run.py", "inkzoom.js", "sessionpage.js"]

# Suites that must not run beside one another: each binds a fixed port or
# writes shared state under ~/.config. Found by comparing a -j 1 run with a
# -j 4 run. Empty: every suite binds port 0 and keeps its config in a temp
# dir, and a -j 4 run fails nothing a -j 1 run passes.
SERIAL = []

# The guards: what keeps PHI out of git and the relay honest, and the relay
# path runnable on the cluster's python 3.7.
GUARDS = ["tracked.py", "precommit.py", "requests.py", "relay.py", "holds.py",
          "code.py", "py37.py", "exporting.py", "phi_probe.py"]

# Started first, because they are the longest; the rest follow by name.
FIRST = ["link.js", "onlyagent.py", "plane.js", "factory", "seam.js", "relay.py"]


class Suite(object):
    def __init__(self, name, argv, cwd, kind):
        self.name = name
        self.argv = argv
        self.cwd = cwd
        self.kind = kind  # "py", "js", "factory", "macros" or "aiconfig"


def discover():
    suites = []
    for fn in sorted(os.listdir(HERE)):
        stem, ext = os.path.splitext(fn)
        if fn in HELPERS or ext not in (".py", ".js"):
            continue
        path = os.path.join(HERE, fn)
        if ext == ".py":
            suites.append(Suite(fn, [sys.executable, path], BOARD, "py"))
        else:
            suites.append(Suite(fn, ["node", path], BOARD, "js"))
    return suites


def helper_users(suites):
    """{helper: [suites that load it]} for every helper but this file."""
    users = {}
    for helper in HELPERS:
        if helper == os.path.basename(__file__):
            continue
        stem = os.path.splitext(helper)[0]
        marks = ("'./%s'" % stem, '"./%s"' % stem, "./%s.js" % stem,
                 "import %s" % stem, "from %s import" % stem)
        users[helper] = []
        for s in suites:
            with open(s.argv[-1], encoding="utf-8", errors="replace") as fh:
                text = fh.read()
            if any(m in text for m in marks):
                users[helper].append(s.name)
    return users


def ai_config():
    """ai-config's own tests, as a list of zero or one suite."""
    if not os.path.isfile(AI_CONFIG_TESTS):
        return []
    return [Suite("ai-config", ["bash", AI_CONFIG_TESTS],
                  os.path.dirname(os.path.dirname(AI_CONFIG_TESTS)), "aiconfig")]


def skipped_ai_config():
    print("ai-config SKIPPED: %s is not here, so the PHI policy's own tests "
          "DID NOT RUN" % os.path.relpath(AI_CONFIG_TESTS, ROOT))


def extras():
    out = [Suite("macros/tex",
                 [sys.executable, os.path.join(BOARD, "tools", "sync-macros.py"),
                  "--check"], BOARD, "macros")]
    out.extend(ai_config())
    if os.path.isdir(os.path.join(FACTORY, "paperwriter")):
        out.append(Suite("factory",
                         [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
                         FACTORY, "factory"))
    return out


def ensure_jsdom():
    """jsdom is development-only. Fetch it on first run; carry on without it."""
    if not shutil.which("node"):
        print("node is not installed; the test suite needs it (the board itself does not)")
        sys.exit(1)
    have = subprocess.run(["node", "-e", "require('jsdom')"], cwd=BOARD,
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if os.path.isdir(os.path.join(BOARD, "node_modules")) and have.returncode == 0:
        return
    if not shutil.which("npm"):
        print("no npm; the real-DOM suites will skip\n")
        return
    print("installing jsdom (development only, not needed to run the board)...")
    proc = subprocess.run(["npm", "install", "--no-save", "--silent", "jsdom"],
                          cwd=BOARD, stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL)
    print("  installed\n" if proc.returncode == 0
          else "  could not install -- the real-DOM suites will skip\n")


def failure_lines(out):
    """The FAIL/ERROR lines and their indented detail; else the tail."""
    lines = out.rstrip("\n").split("\n")
    picked = []
    keep = False
    for line in lines:
        if line.startswith(("FAIL", "ERROR")):
            picked.append(line)
            keep = True
        elif keep and line.startswith((" ", "\t")) and len(picked) < 60:
            picked.append(line)
        else:
            keep = False
    return picked or lines[-15:]


def run_one(suite):
    """Run one suite. Returns (status, seconds, summary, detail lines)."""
    start = time.time()
    # A page cache of its own: the real one is shared and pruned, and a suite
    # pruning another's page set mid-read is a failure neither caused.
    pages = tempfile.mkdtemp(prefix="suite-pages-")
    try:
        proc = subprocess.run(suite.argv, cwd=suite.cwd, stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              universal_newlines=True, errors="replace",
                              env=dict(os.environ, TUTORBOARD_PAGES=pages))
    finally:
        shutil.rmtree(pages, ignore_errors=True)
    secs = time.time() - start
    out = proc.stdout or ""
    lines = [l for l in out.split("\n") if l.strip()]
    last = lines[-1] if lines else ""

    if suite.kind == "js" and any(l.startswith("skip") for l in lines):
        first = next(l for l in lines if l.startswith("skip"))
        return "skip", secs, "skipped (%s)" % first[4:].strip(), []
    if suite.kind == "factory":
        ran = [l for l in lines if l.startswith("Ran ") and " test" in l]
        if proc.returncode == 0:
            return "pass", secs, (ran[-1] if ran else last) + ", and they pass", []
        return "fail", secs, "FAILED", [l for l in lines
                                        if l.startswith(("FAIL:", "ERROR:"))] or lines[-15:]
    if suite.kind == "aiconfig":
        if proc.returncode == 0:
            return "pass", secs, last, []
        return "fail", secs, "FAILED (exit %d)" % proc.returncode, lines[-15:]
    if suite.kind == "macros":
        if proc.returncode == 0:
            return "pass", secs, "TeX and KaTeX know the same commands", []
        return "fail", secs, "FAILED -- run: python3 board/tools/sync-macros.py", lines[-15:]
    if proc.returncode != 0:
        return "fail", secs, "FAILED (exit %d)" % proc.returncode, failure_lines(out)
    return "pass", secs, last, []


def run_all(suites, workers):
    """Run suites `workers` at a time; never two SERIAL suites at once."""
    pending = list(suites)
    results = {}
    cond = threading.Condition()
    state = {"serial": False}
    width = max(len(s.name) for s in suites) + 1

    def take():
        with cond:
            while True:
                if not pending:
                    return None
                for i, s in enumerate(pending):
                    if s.name in SERIAL and state["serial"]:
                        continue
                    pending.pop(i)
                    if s.name in SERIAL:
                        state["serial"] = True
                    return s
                cond.wait()

    def worker():
        while True:
            s = take()
            if s is None:
                return
            try:
                res = run_one(s)
            except OSError as e:
                res = ("fail", 0.0, "FAILED (could not start: %s)" % e, [])
            with cond:
                if s.name in SERIAL:
                    state["serial"] = False
                results[s.name] = res
                status, secs, summary, detail = res
                print("%-*s %6.1fs  %s" % (width, s.name, secs, summary))
                for line in detail:
                    print(" " * (width + 10) + line)
                sys.stdout.flush()
                cond.notify_all()

    threads = [threading.Thread(target=worker) for _ in range(max(1, workers))]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return results


def order(suites):
    rank = {n: i for i, n in enumerate(FIRST)}
    return sorted(suites, key=lambda s: (rank.get(s.name, len(rank)),
                                         s.name not in SERIAL, s.name))


def main(argv):
    ap = argparse.ArgumentParser(description="Run board/test's suites.")
    ap.add_argument("-j", type=int, default=4, metavar="N",
                    help="suites run at once (default 4)")
    ap.add_argument("--guards", action="store_true",
                    help="only " + ", ".join(GUARDS))
    ap.add_argument("names", nargs="*", help="run only these suites")
    args = ap.parse_args(argv)

    found = discover()
    everything = found + extras()
    unused = []
    if args.guards:
        chosen = [s for s in found if s.name in GUARDS] + ai_config()
        if not ai_config():
            skipped_ai_config()
    elif args.names:
        missing = []
        chosen = []
        for n in args.names:
            base = os.path.basename(n)
            hit = [s for s in everything
                   if s.name in (n, base) or os.path.splitext(s.name)[0] == base]
            if hit:
                chosen.extend(s for s in hit if s not in chosen)
            else:
                missing.append(n)
        if missing:
            print("no such suite: " + ", ".join(missing))
            return 2
    else:
        chosen = everything
        if not os.path.isdir(os.path.join(FACTORY, "paperwriter")):
            print("factory skipped: Paper-Writer is not checked out here")
        if not ai_config():
            skipped_ai_config()
        width = max(len(s.name) for s in chosen) + 1
        for helper, users in sorted(helper_users(found).items()):
            if users:
                print("%-*s %7s  helper, runs inside %s"
                      % (width, helper, "", ", ".join(users)))
            else:
                unused.append(helper)
                print("%-*s %7s  FAILED: a helper no suite loads never runs"
                      % (width, helper, ""))

    if any(s.kind == "js" for s in chosen):
        ensure_jsdom()

    start = time.time()
    results = run_all(order(chosen), args.j)
    total = time.time() - start

    fails = sorted(n for n, r in results.items() if r[0] == "fail") + unused
    skips = sum(1 for r in results.values() if r[0] == "skip")
    print()
    if fails:
        print("failed: " + ", ".join(fails))
    passed = len(results) - skips
    verdict = ("%d suite(s) failed" % len(fails) if fails
               else "all %d suite%s passed" % (passed, "" if passed == 1 else "s"))
    if skips:
        verdict += " (%d skipped)" % skips
    print("total %.1fs, -j %d: %s" % (total, args.j, verdict))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
