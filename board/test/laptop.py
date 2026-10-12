#!/usr/bin/env python3
"""A coding laptop: `scripts/setup-mac.sh --coding`, and `board pull` there.

    python3 test/laptop.py

The real setup-mac.sh, bootstrap.sh and install.sh run in a fixture Atlas
cloned from a bare origin, with ai-config cloned inside it from its own. HOME
is a temp dir, and every tool that could touch this machine is a shim first on
the PATH: launchctl keeps its "loaded" agents in a file, and tailscale, curl
and brew only log. The machine's own directories follow the shims on the PATH,
so setup-mac.sh, which puts them in front only when they are missing, cannot
reach the real ones. The suite refuses to run if `launchctl` resolves to
anything but the shim.

  - --CODING WRITES THE ROLE FILE, and a rerun without it stays a coding
    checkout.
  - NO BOARD LAUNCHAGENT IS LOADED; atlas.brew-upgrade is. A stray
    `tutor-board` is booted out with its plist; without the role, install.sh
    does load it.
  - TAILSCALE AND PORT 8778 ARE NEVER ASKED.
  - THE PULL, scripts/setup.sh and ai-config's fast-forward and install run.
  - A MISSING ai-config/policy/phi.py IS A PROBLEM, named.
  - `board pull` FAST-FORWARDS ai-config, relinks it, and names the subjects
    whose lockfiles moved, with --quiet too; ai-config that will not
    fast-forward is exit 1.
"""

import os
import shutil
import stat
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ATLAS = os.path.dirname(ROOT)
BOARD = os.path.join(ROOT, "bin", "board")

fails = []


def check(name, cond, detail=""):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name + (("\n       " + str(detail)) if detail else ""))


work = tempfile.mkdtemp(prefix="laptop-")
home = os.path.join(work, "home")
shims = os.path.join(work, "shims")
CALLS = os.path.join(work, "calls.log")
LOADED = os.path.join(work, "loaded")
PATH = os.pathsep.join([shims, "/opt/homebrew/bin", "/usr/local/bin",
                        os.path.join(home, ".local", "bin"),
                        "/usr/bin", "/bin", "/usr/sbin", "/sbin"])
ENV = dict(os.environ, HOME=home, PATH=PATH,
           XDG_CONFIG_HOME=os.path.join(home, ".config"),
           XDG_STATE_HOME=os.path.join(home, ".local", "state"),
           BOARD_STATE_DIR=os.path.join(work, "state"),
           LAPTOP_CALLS=CALLS, LAPTOP_LOADED=LOADED,
           GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
           GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t",
           GIT_TERMINAL_PROMPT="0")
for k in ("XDG_BIN_HOME", "TUTORBOARD_COURSES", "TUTORBOARD_SESSION",
          "TUTORBOARD_TURN", "PYTHON", "GIT_DIR", "GIT_WORK_TREE"):
    ENV.pop(k, None)
ROLE = os.path.join(home, ".config", "tutor-board", "role")
AGENT = os.path.join(home, "Library", "LaunchAgents", "tutor-board.plist")


def write(path, text, mode=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    if mode:
        os.chmod(path, mode)


def read(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return ""


def run(argv, cwd=None):
    p = subprocess.run(argv, cwd=cwd or work, env=ENV, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, universal_newlines=True,
                       timeout=300)
    return p.returncode, p.stdout


def git(root, *args):
    return run(["git", "-C", root] + list(args))[1].strip()


def calls(tool):
    return [l for l in read(CALLS).splitlines() if l.split(" ", 1)[0] == tool]


def commit(repo, files, message):
    for rel, text in files.items():
        write(os.path.join(repo, rel), text)
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", message)
    git(repo, "push", "-q", "origin", "main")


EXE = stat.S_IRWXU
LOG = 'echo "$(basename "$0") $*" >>"$LAPTOP_CALLS"\n'
# launchctl: print answers from the loaded file; bootstrap and bootout edit it.
write(os.path.join(shims, "launchctl"), "#!/bin/bash\n" + LOG + """\
touch "$LAPTOP_LOADED"
case "$1" in
  print) grep -qx "${2##*/}" "$LAPTOP_LOADED" ;;
  bootout) grep -vx "${2##*/}" "$LAPTOP_LOADED" >"$LAPTOP_LOADED.new"
           mv "$LAPTOP_LOADED.new" "$LAPTOP_LOADED" ;;
  bootstrap) b="${3##*/}"; echo "${b%.plist}" >>"$LAPTOP_LOADED" ;;
esac
""", EXE)
write(os.path.join(shims, "tailscale"), "#!/bin/bash\n" + LOG, EXE)
write(os.path.join(shims, "curl"), "#!/bin/bash\n" + LOG + "printf 200\n", EXE)
write(os.path.join(shims, "brew"), "#!/bin/bash\n" + LOG, EXE)
# setup-mac.sh refuses anything but a Mac; the suite runs on the cluster too.
write(os.path.join(shims, "uname"), "#!/bin/bash\necho Darwin\n", EXE)

try:
    for tool in ("launchctl", "tailscale", "curl", "brew", "uname"):
        where = shutil.which(tool, path=PATH)
        if where != os.path.join(shims, tool):
            print("REFUSED: %s resolves to %s, not the shim; nothing was run"
                  % (tool, where))
            sys.exit(1)

    # ai-config: its own origin, with the PHI policy and two install scripts
    # that only say they ran.
    aorigin = os.path.join(work, "ai-config.git")
    run(["git", "init", "-q", "--bare", "-b", "main", aorigin])
    aseed = os.path.join(work, "ai-config-seed")
    run(["git", "init", "-q", "-b", "main", aseed])
    git(aseed, "remote", "add", "origin", aorigin)
    commit(aseed, {"scripts/install.sh": 'echo ai-install >>"$LAPTOP_CALLS"\n',
                   "scripts/install-clis.sh": 'echo install-clis >>"$LAPTOP_CALLS"\n',
                   "policy/phi.py": "def names_phi(path):\n    return False\n"},
           "a1")

    # Atlas: the real setup scripts, the rest stubbed.
    origin = os.path.join(work, "atlas.git")
    run(["git", "init", "-q", "--bare", "-b", "main", origin])
    seed = os.path.join(work, "atlas-seed")
    run(["git", "init", "-q", "-b", "main", seed])
    git(seed, "remote", "add", "origin", origin)
    real = {}
    for rel in ("scripts/setup-mac.sh", "board/bootstrap.sh", "board/install.sh",
                "board/scripts/launchd/tutor-board.plist", "scripts/brew-upgrade.py",
                "scripts/launchd/atlas.brew-upgrade.plist"):
        real[rel] = read(os.path.join(ATLAS, rel))
    real.update({
        ".gitignore": "/ai-config/\n",
        "scripts/setup.sh": 'echo setup.sh >>"$LAPTOP_CALLS"\necho "workspaces ok"\n',
        "board/test/tracked.py": "import sys\nsys.exit(0)\n",
        "projects/A/uv.lock": "a 1\n", "projects/B/go.sum": "b 1\n",
        "courses/C/notes.md": "c 1\n"})
    commit(seed, real, "seed")
    laptop = os.path.join(work, "laptop")
    run(["git", "clone", "-q", origin, laptop])
    run(["git", "clone", "-q", aorigin, os.path.join(laptop, "ai-config")])
    setup = os.path.join(laptop, "scripts", "setup-mac.sh")

    # A stray board from before, loaded, with its plist.
    write(AGENT, "<plist/>\n")
    write(LOADED, "tutor-board\n")
    commit(seed, {"courses/C/notes.md": "c 2\n"}, "elsewhere")

    # =======================================================================
    # setup-mac.sh --coding
    # =======================================================================
    code, out = run(["bash", setup, "--coding"])
    check("--coding ends clean, as a coding checkout",
          code == 0 and "THIS CODING CHECKOUT IS UP TO DATE" in out, out)
    check("and writes the role file", read(ROLE).strip() == "coding", read(ROLE))
    check("it pulls main", git(laptop, "rev-parse", "HEAD")
          == git(origin, "rev-parse", "main"), out)
    check("and runs scripts/setup.sh, ai-config's install.sh and install-clis.sh",
          calls("setup.sh") and calls("ai-install") and calls("install-clis"),
          read(CALLS))
    check("a stray tutor-board is booted out, its plist removed",
          any("bootout" in l and l.endswith("/tutor-board") for l in calls("launchctl"))
          and not os.path.exists(AGENT) and "tutor-board" not in read(LOADED),
          "\n".join(calls("launchctl")))
    check("no tutor-board bootstrap, and atlas.brew-upgrade is loaded",
          not any(l.startswith("launchctl bootstrap") and "tutor-board" in l
                  for l in calls("launchctl"))
          and "no LaunchAgent: a coding checkout runs no board" in out
          and "atlas.brew-upgrade" in read(LOADED).split()
          and "atlas.brew-upgrade loaded;" in out, out)
    check("tailscale and port 8778 are never asked",
          not calls("tailscale") and not calls("curl")
          and "skipped: a coding checkout serves no board" in out, read(CALLS))
    check("and bootstrap offers no tailnet name or tailscale serve",
          "will call itself" not in out and "tailscale serve --bg" not in out, out)
    check("the PHI policy is found", "ai-config/policy/phi.py is there" in out, out)

    # A rerun with no flag, after ai-config moved on.
    open(CALLS, "w").close()
    commit(aseed, {"rules.md": "new\n"}, "a2")
    code, out = run(["bash", setup])
    check("a rerun without --coding stays a coding checkout",
          code == 0 and read(ROLE).strip() == "coding"
          and "THIS CODING CHECKOUT IS UP TO DATE" in out, out)
    check("and still loads nothing and asks neither tailscale nor 8778",
          not any(l.startswith("launchctl bootstrap") for l in calls("launchctl"))
          and not calls("tailscale") and not calls("curl"), read(CALLS))
    check("ai-config is fast-forwarded and installed",
          git(os.path.join(laptop, "ai-config"), "rev-parse", "HEAD")
          == git(aorigin, "rev-parse", "main") and calls("ai-install"), out)

    os.remove(os.path.join(laptop, "ai-config", "policy", "phi.py"))
    code, out = run(["bash", setup])
    check("a missing ai-config/policy/phi.py is a problem, named",
          code == 1 and "no ai-config/policy/phi.py" in out
          and "1 thing(s) above still need a person" in out, out)
    git(os.path.join(laptop, "ai-config"), "checkout", "--", "policy/phi.py")

    # Without the role, the same install.sh does load the agent: the gate is
    # the role, not the shim. Needs plutil, which only a Mac has.
    if shutil.which("plutil"):
        os.remove(ROLE)
        open(CALLS, "w").close()
        code, out = run(["bash", os.path.join(laptop, "board", "install.sh")])
        check("without the role install.sh loads tutor-board",
              any(l.startswith("launchctl bootstrap") for l in calls("launchctl"))
              and os.path.exists(AGENT), out)
        write(ROLE, "coding\n")
        code, out = run(["bash", os.path.join(laptop, "board", "install.sh")])
        check("and with it again, boots it out",
              "booted out tutor-board" in out and not os.path.exists(AGENT)
              and "tutor-board" not in read(LOADED), out)
    else:
        print("skip the host-role install.sh check: no plutil here")

    # =======================================================================
    # board pull
    # =======================================================================
    open(CALLS, "w").close()
    commit(seed, {"projects/A/uv.lock": "a 2\n", "courses/C/notes.md": "c 3\n"},
           "A's lock moves")
    commit(aseed, {"rules.md": "newer\n"}, "a3")
    code, out = run([sys.executable, BOARD, "pull", "--atlas", laptop])
    check("`board pull` fast-forwards Atlas", code == 0
          and git(laptop, "rev-parse", "HEAD") == git(origin, "rev-parse", "main"), out)
    check("and names the subject whose lockfile moved, and no other",
          "lockfiles moved in projects/A;" in out and "projects/B" not in out
          and "courses/C" not in out, out)
    check("and fast-forwards ai-config, relinking it",
          git(os.path.join(laptop, "ai-config"), "rev-parse", "HEAD")
          == git(aorigin, "rev-parse", "main")
          and "ai-config: moved to" in out and calls("ai-install"), out)

    commit(seed, {"projects/B/go.sum": "b 2\n"}, "B's lock moves")
    code, out = run([sys.executable, BOARD, "pull", "--quiet", "--atlas", laptop])
    check("--quiet still names it", code == 0
          and "lockfiles moved in projects/B;" in out and "projects/A" not in out, out)

    code, out = run([sys.executable, BOARD, "pull", "--atlas", laptop])
    check("nothing new names nothing", code == 0 and "lockfiles" not in out, out)

    acopy = os.path.join(laptop, "ai-config")
    write(os.path.join(acopy, "mine.md"), "local\n")
    git(acopy, "add", "-A")
    git(acopy, "commit", "-qm", "local")
    commit(aseed, {"theirs.md": "x\n"}, "a4")
    code, out = run([sys.executable, BOARD, "pull", "--atlas", laptop])
    check("an ai-config that will not fast-forward is exit 1, said",
          code == 1 and "ai-config: not moved forward" in out, out)
finally:
    shutil.rmtree(work, ignore_errors=True)

print()
if fails:
    print("%d FAILURES" % len(fails))
    sys.exit(1)
print("a coding laptop loads no board, asks no tailnet, and its pull names what to rebuild")
