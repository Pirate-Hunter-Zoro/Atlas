#!/usr/bin/env python3
"""A coding laptop: `scripts/setup-mac.sh --coding`, and `board pull` there.

    python3 test/laptop.py

The real setup-mac.sh, setup.sh, tools.sh, bootstrap.sh and install.sh (and
board/tutorboard, linked) run in a fixture Atlas
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
  - THE PULL, scripts/setup.sh and ai-config's fast-forward and install run;
    setup.sh bundles the union, builds a mise subject and installs a
    descriptor, and a second run, --coding or as the host, changes nothing.
  - A MISSING ai-config/policy/phi.py IS A PROBLEM, named.
  - `board pull` FAST-FORWARDS ai-config, relinks it, and names the subjects
    whose lockfiles moved, with --quiet too, a mise.lock, a Cargo.lock or a
    build.zig.zon one directory down included; ai-config that will not fast-forward is exit 1.
  - --CODING ASKS FOR THE MAC MINI'S TAILNET NAME and writes it as config.json
    `host`, keeping the other keys; a rerun does not ask again.
  - `board pull --materials` RSYNCS THE IGNORED INPUTS ONLY. An rsync shim
    logs the command, maps `host:<path>` to a fixture Mac and runs the real
    rsync there, so the include and exclude lists are proved by rsync itself:
    materials, textbooks, readings, lectures and assignments arrive; `.ink/`,
    `sessions/`, any `.env*`, phi/ and anything else never do; nothing here is
    deleted; named subjects limit it; no `host` is a plain refusal.
"""

import json
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


def run(argv, cwd=None, stdin=""):
    p = subprocess.run(argv, cwd=cwd or work, env=ENV, input=stdin,
                       stdout=subprocess.PIPE,
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
# tailscale: serve --bg is remembered, and serve status then answers it.
write(os.path.join(shims, "tailscale"), "#!/bin/bash\n" + LOG + """\
case "$*" in
  "serve status") [ -f "$LAPTOP_LOADED.served" ] && echo "|-- / proxy http://127.0.0.1:8778" ;;
  "serve --bg"*) touch "$LAPTOP_LOADED.served" ;;
esac
exit 0
""", EXE)
write(os.path.join(shims, "curl"), "#!/bin/bash\n" + LOG + "printf 200\n", EXE)
write(os.path.join(shims, "brew"), "#!/bin/bash\n" + LOG, EXE)
write(os.path.join(shims, "mise"), "#!/bin/bash\n" + LOG, EXE)
# setup-mac.sh refuses anything but a Mac; the suite runs on the cluster too.
write(os.path.join(shims, "uname"), "#!/bin/bash\necho Darwin\n", EXE)
# rsync: logs its argv (one JSON list a line), maps `host:<path>` to
# <MACHOME>/<path>, drops `-e <ssh>`, and runs the real rsync, so the filter
# lists are rsync's to judge. No host is ever contacted. openrsync spawns its
# receiving half as `rsync --server`, which passes straight through.
MACHOME = os.path.join(work, "machome")
REAL_RSYNC = shutil.which("rsync", path=os.pathsep.join(
    PATH.split(os.pathsep)[1:])) or ""
RSYNC_LOG = os.path.join(work, "rsync.log")
ENV.update(LAPTOP_MACHOME=MACHOME, LAPTOP_REAL_RSYNC=REAL_RSYNC,
           LAPTOP_RSYNC_LOG=RSYNC_LOG)
write(os.path.join(shims, "rsync"), "#!%s\n" % sys.executable + """\
import json, os, re, subprocess, sys
args = sys.argv[1:]
real = os.environ.get("LAPTOP_REAL_RSYNC")
if "--server" in args:  # a local rsync's other half, spawned by name
    os.execv(real, [real] + args)
with open(os.environ["LAPTOP_RSYNC_LOG"], "a") as fh:
    fh.write(json.dumps(args) + "\\n")
out, skip = [], False
for a in args:
    if skip:
        skip = False
    elif a == "-e":
        skip = True
    elif re.match(r"^[^/:]+:", a):
        out.append(os.path.join(os.environ["LAPTOP_MACHOME"], a.split(":", 1)[1]))
    else:
        out.append(a)
sys.exit(subprocess.call([real] + out) if real else 0)
""", EXE)

try:
    for tool in ("launchctl", "tailscale", "curl", "brew", "mise", "uname", "rsync"):
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

    # Atlas: the real setup scripts and the toolplan they read (board/tutorboard,
    # a link to this checkout's), the rest stubbed.
    origin = os.path.join(work, "atlas.git")
    run(["git", "init", "-q", "--bare", "-b", "main", origin])
    seed = os.path.join(work, "atlas-seed")
    run(["git", "init", "-q", "-b", "main", seed])
    git(seed, "remote", "add", "origin", origin)
    real = {}
    for rel in ("scripts/setup-mac.sh", "scripts/setup.sh", "scripts/tools.sh",
                "board/bootstrap.sh", "board/install.sh", "Brewfile",
                "board/scripts/launchd/tutor-board.plist", "scripts/brew-upgrade.py",
                "scripts/launchd/atlas.brew-upgrade.plist"):
        real[rel] = read(os.path.join(ATLAS, rel))
    real.update({
        ".gitignore": "/ai-config/\n",
        "projects/M/tools/widget.sh": (
            'T_NAME="widget"\nT_BIN="widget"\nT_BIN_DIR="$HOME/.widget/bin"\n'
            'T_ROLES="host coding"\nT_INSTALL=\'mkdir -p "$HOME/.widget/bin" && '
            'printf "#!/bin/sh\\necho widget 1.0\\n" >"$HOME/.widget/bin/widget" && '
            'chmod +x "$HOME/.widget/bin/widget" && echo widget-install >>"$LAPTOP_CALLS"\'\n'
            'T_MANUAL="by hand"\nT_UPDATE="true"\nT_VERSION="widget"\nT_CHECK="widget"\n'
            'T_EVERY_DAYS=1\nT_STALE_DAYS=14\n'),
        "board/test/tracked.py": "import sys\nsys.exit(0)\n",
        "projects/A/uv.lock": "a 1\n", "projects/B/go.sum": "b 1\n",
        "projects/M/mise.toml": '[tools]\nrust = "1.80.0"\n',
        "projects/M/mise.lock": "m 1\n", "projects/M/app/Cargo.toml": "[package]\n",
        "projects/M/app/Cargo.lock": "m 1\n", "courses/C/notes.md": "c 1\n"})
    os.makedirs(os.path.join(seed, "board"))
    os.symlink(os.path.join(ROOT, "tutorboard"), os.path.join(seed, "board", "tutorboard"))
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
    CONFIG = os.path.join(home, ".config", "tutor-board", "config.json")
    write(CONFIG, '{"provider": "kept"}\n')
    code, out = run(["bash", setup, "--coding"], stdin="mac-mini\n")
    cfg = json.loads(read(CONFIG) or "{}")
    check("--coding asks for the Mac mini's tailnet name and writes it as host",
          cfg.get("host") == "mac-mini" and cfg.get("provider") == "kept"
          and "board pull --materials copies from mac-mini" in out, out)
    check("--coding ends clean, as a coding checkout",
          code == 0 and "THIS CODING CHECKOUT IS UP TO DATE" in out, out)
    check("and writes the role file", read(ROLE).strip() == "coding", read(ROLE))
    check("it pulls main", git(laptop, "rev-parse", "HEAD")
          == git(origin, "rev-parse", "main"), out)
    check("and runs scripts/setup.sh, ai-config's install.sh and install-clis.sh",
          "Brewfile.all rewritten" in out and calls("ai-install") and calls("install-clis"),
          read(CALLS))
    check("setup.sh bundles the union, builds the mise subject and installs its tool",
          [l for l in calls("brew") if l.startswith("brew bundle install --no-upgrade")]
          and "mise install --locked rust" in calls("mise")
          and "mise exec -- cargo fetch --locked" in calls("mise")
          and calls("widget-install") == ["widget-install"]
          and "1 tool(s) declared for a coding, 0 problem(s)" in out, (out, read(CALLS)))
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
    code, out = run(["bash", setup], stdin="elsewhere\n")
    check("a rerun without --coding stays a coding checkout",
          code == 0 and read(ROLE).strip() == "coding"
          and "THIS CODING CHECKOUT IS UP TO DATE" in out, out)
    check("and does not ask for the host again",
          json.loads(read(CONFIG)).get("host") == "mac-mini"
          and "copies from mac-mini" in out, out)
    check("and its setup.sh is clean and changes nothing",
          "Brewfile.all unchanged" in out and "FAILED" not in out
          and not calls("widget-install"), (out, read(CALLS)))
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

        # The host: setup-mac.sh with no role, twice. The second run changes
        # nothing: no union rewritten, no tool installed, no agent loaded and
        # no tailscale serve.
        os.remove(ROLE)
        coding_cfg = read(CONFIG)
        write(CONFIG, "{}\n")
        runs = []
        for _ in (1, 2):
            open(CALLS, "w").close()
            code, out = run(["bash", setup])
            runs.append((code, out, read(CALLS).splitlines()))
        check("setup-mac.sh as the host ends clean, twice",
              all(c == 0 and "THE MAC IS UP TO DATE" in o and "FAILED" not in o
                  for c, o, _ in runs), [o for _, o, _ in runs])
        code, out, said = runs[1]
        check("and its second run changes nothing",
              "Brewfile.all unchanged" in out and "widget-install" not in said
              and not [l for l in said if l.startswith("launchctl bootstrap")
                       or l.startswith("tailscale serve --bg")], (out, said))
        write(ROLE, "coding\n")
        write(CONFIG, coding_cfg)
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

    commit(seed, {"projects/M/mise.lock": "m 2\n"}, "M's mise lock moves")
    code, out = run([sys.executable, BOARD, "pull", "--atlas", laptop])
    check("a subject with a mise.toml is named when its mise.lock moves",
          code == 0 and "lockfiles moved in projects/M;" in out, out)
    commit(seed, {"projects/M/app/Cargo.lock": "m 2\n"}, "M's Cargo lock moves")
    code, out = run([sys.executable, BOARD, "pull", "--atlas", laptop])
    check("and when a lockfile one directory down moves",
          code == 0 and "lockfiles moved in projects/M;" in out, out)
    commit(seed, {"projects/M/target/Cargo.lock": "out\n",
                  "projects/M/app/src/Cargo.lock": "deep\n"}, "not a marker's")
    code, out = run([sys.executable, BOARD, "pull", "--atlas", laptop])
    check("but not one in target/ or two down", code == 0 and "lockfiles" not in out, out)
    commit(seed, {"projects/M/warden/build.zig.zon": ".{ .version = \"2\" }\n"},
           "M's warden manifest moves")
    code, out = run([sys.executable, BOARD, "pull", "--atlas", laptop])
    check("a build.zig.zon one directory down is its own lockfile, and named",
          code == 0 and "lockfiles moved in projects/M;" in out, out)
    commit(seed, {"projects/M/zig-pkg/build.zig.zon": "fetched\n"}, "a fetched package's")
    code, out = run([sys.executable, BOARD, "pull", "--atlas", laptop])
    check("but not one in zig-pkg/", code == 0 and "lockfiles" not in out, out)

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

    # =======================================================================
    # board pull --materials
    # =======================================================================
    mac = os.path.join(MACHOME, "Developer", "Atlas")
    SENT = {  # what crosses
        "materials/shared/m.pdf", "courses/C/materials/c.pdf",
        "courses/C/textbook/book.pdf", "courses/C/textbook/ch/1.pdf",
        "courses/C/chapters/ch1/reading/r.pdf",
        "courses/C/chapters/ch1/lectures/l.pdf",
        "courses/C/chapters/ch1/assignment-sheet.pdf",
        "courses/C/homework/hw1/assignment/a.pdf",
        "courses/C/homework/hw1/assignment/deep/b.pdf",
        "courses/C/assignment1.pdf", "courses/C/assignment/a.pdf",
        "courses/D/textbook/d.pdf", "projects/A/materials/q.txt"}
    KEPT = {  # what never does
        "courses/C/.ink/i.json", "courses/C/materials/.ink/k.json",
        "courses/C/textbook/.ink/t.json", "sessions/s1/session.json",
        "courses/C/materials/sessions/x.json", ".env",
        "courses/C/materials/.env", "courses/C/textbook/.env",
        "courses/C/materials/.envrc",
        "courses/C/chapters/ch1/lectures/.env.local",
        "projects/A/phi/materials/p.csv", "projects/A/results/materials/r.csv",
        "courses/C/chapters/ch1/notes.md", "courses/C/notes.md",
        "courses/C/chapters/ch1/reading.md", "projects/A/notes.md",
        "README.md", "vendor/v/materials/v.pdf",
        "projects/A/node_modules/materials/n.js"}
    for rel in SENT | KEPT:
        write(os.path.join(mac, rel), "mac\n")
    os.makedirs(os.path.join(laptop, "courses", "D"), exist_ok=True)
    write(os.path.join(laptop, "materials", "mine.pdf"), "laptop\n")
    write(os.path.join(laptop, "courses", "C", "notes.md"), "laptop's own\n")

    def landed():
        got = set()
        for top, dirs, files in os.walk(laptop):
            dirs[:] = [d for d in dirs if d not in (".git", "ai-config")]
            for f in files:
                rel = os.path.relpath(os.path.join(top, f), laptop)
                if read(os.path.join(laptop, rel)) == "mac\n":
                    got.add(rel)
        return got

    def rsyncs():
        return [json.loads(l) for l in read(RSYNC_LOG).splitlines()]

    saved_cfg = read(CONFIG)
    write(CONFIG, '{"provider": "kept"}\n')
    code, out = run([sys.executable, BOARD, "pull", "--materials", "--atlas", laptop])
    check("--materials without host refuses plainly, and runs no rsync",
          code == 1 and "no `host`" in out and "setup-mac.sh --coding" in out
          and not rsyncs(), out)
    write(CONFIG, saved_cfg)

    code, out = run([sys.executable, BOARD, "pull", "--materials", "--atlas", laptop])
    sent = rsyncs()[-1] if rsyncs() else []
    check("--materials runs one rsync from host:Developer/Atlas/ over batch ssh",
          len(rsyncs()) == 1 and "mac-mini:Developer/Atlas/" in sent
          and sent[-1] == os.path.join(laptop, "")
          and "-e" in sent and "BatchMode=yes" in sent[sent.index("-e") + 1]
          and not any(a.startswith("--delete") for a in sent), sent)
    excl = [a for a in sent if a.startswith("--exclude=")]
    incl = [a for a in sent if a.startswith("--include=")]
    check("every never-copy is excluded before any include",
          all(("--exclude=" + p) in excl for p in (".ink/", "sessions/", ".env*"))
          and incl and max(sent.index(a) for a in excl[:-1])
          < min(sent.index(a) for a in incl) and sent.index("--exclude=*")
          > max(sent.index(a) for a in incl), sent)
    if REAL_RSYNC:
        got = landed()
        check("rsync itself copies exactly the ignored inputs",
              code == 0 and got == SENT,
              "%s\nmissing %s\nextra %s" % (out, sorted(SENT - got),
                                              sorted(got - SENT)))
        check("and deletes nothing here, overwriting no tracked file",
              read(os.path.join(laptop, "materials", "mine.pdf")) == "laptop\n"
              and read(os.path.join(laptop, "courses", "C", "notes.md"))
              == "laptop's own\n", out)
        for rel in SENT:
            os.remove(os.path.join(laptop, rel))
        code, out = run([sys.executable, BOARD, "pull", "--materials", "D",
                         "--atlas", laptop])
        check("named subjects limit it: `D` brings courses/D's inputs only",
              code == 0 and landed() == {"courses/D/textbook/d.pdf"}
              and "--include=/courses/D/" in rsyncs()[-1], out)
    else:
        print("skip the real-rsync checks: no rsync here")
    code, out = run([sys.executable, BOARD, "pull", "--materials", "Nowhere",
                     "--atlas", laptop])
    check("an unknown subject is refused before rsync runs",
          code == 1 and "no subject 'Nowhere'" in out
          and len(rsyncs()) == (2 if REAL_RSYNC else 1), out)
finally:
    shutil.rmtree(work, ignore_errors=True)

print()
if fails:
    print("%d FAILURES" % len(fails))
    sys.exit(1)
print("a coding laptop loads no board, asks no tailnet, its pull names what to rebuild, "
      "and --materials copies the ignored inputs only")
