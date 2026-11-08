#!/usr/bin/env python3
"""The one Mac: `scripts/setup-mac.sh` as the Atlas host, and `board pull`.

    python3 test/host.py

The real setup-mac.sh, setup.sh, tools.sh, bootstrap.sh and install.sh (and
board/tutorboard, linked) run in a fixture Atlas cloned from a bare origin,
with ai-config cloned inside it from its own. HOME is a temp dir, and every
tool that could touch this machine is a shim first on the PATH: launchctl
keeps its "loaded" agents in a file, and tailscale, curl and brew only log.
The machine's own directories follow the shims on the PATH, so setup-mac.sh,
which puts them in front only when they are missing, cannot reach the real
ones. The suite refuses to run if `launchctl` resolves to anything but the shim.

  - SETUP-MAC.SH IS THE HOST. It pulls main, installs the board LaunchAgent,
    serves 8778 on the tailnet, runs scripts/setup.sh, ai-config's install,
    upkeep's opencode phase, the whisper model, and checks the board and the
    DeepSeek key. It loads no coding role and asks no host name.
  - A SECOND RUN CHANGES NOTHING: no union rewritten, no tool installed, no
    agent loaded, no tailscale serve, and the whisper model left alone.
  - A RETIRED PROJECT GOES ONLY WHEN IT HOLDS NOTHING BUT CACHES: one holding
    the owner's files, ignored or untracked, is kept and named, and so is every
    one when git does not answer.
  - `board pull` fast-forwards Atlas and ai-config, names the subjects whose
    lockfiles moved (a mise.lock, a Cargo.lock or a build.zig.zon one
    directory down included), and is exit 1 when ai-config will not
    fast-forward.
"""

import hashlib
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


work = tempfile.mkdtemp(prefix="host-")
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
           HOST_CALLS=CALLS, HOST_LOADED=LOADED,
           GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
           GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t",
           GIT_TERMINAL_PROMPT="0")
for k in ("XDG_BIN_HOME", "TUTORBOARD_COURSES", "TUTORBOARD_SESSION",
          "TUTORBOARD_TURN", "PYTHON", "GIT_DIR", "GIT_WORK_TREE"):
    ENV.pop(k, None)
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
LOG = 'echo "$(basename "$0") $*" >>"$HOST_CALLS"\n'
# launchctl: print answers from the loaded file; bootstrap and bootout edit it.
write(os.path.join(shims, "launchctl"), "#!/bin/bash\n" + LOG + """\
touch "$HOST_LOADED"
case "$1" in
  print) grep -qx "${2##*/}" "$HOST_LOADED" ;;
  bootout) grep -vx "${2##*/}" "$HOST_LOADED" >"$HOST_LOADED.new"
           mv "$HOST_LOADED.new" "$HOST_LOADED" ;;
  bootstrap) b="${3##*/}"; echo "${b%.plist}" >>"$HOST_LOADED" ;;
esac
""", EXE)
# tailscale: serve --bg is remembered, and serve status then answers it.
write(os.path.join(shims, "tailscale"), "#!/bin/bash\n" + LOG + """\
case "$*" in
  "serve status") [ -f "$HOST_LOADED.served" ] && echo "|-- / proxy http://127.0.0.1:8778" ;;
  "serve --bg"*) touch "$HOST_LOADED.served" ;;
esac
exit 0
""", EXE)
write(os.path.join(shims, "curl"), "#!/bin/bash\n" + LOG + "printf 200\n", EXE)
# The whisper model: a fetch that logs and writes known bytes, checked
# against their own SHA-256 (scripts/speech-model.sh), so no host is contacted.
write(os.path.join(shims, "model-fetch"), "#!/bin/bash\n" + LOG
      + 'printf "model bytes" >"$2"\n', EXE)
ENV.pop("TUTORBOARD_MODELS", None)
ENV.update(SPEECH_MODEL_FETCH=os.path.join(shims, "model-fetch"),
           SPEECH_MODEL_SHA256=hashlib.sha256(b"model bytes").hexdigest())
write(os.path.join(shims, "brew"), "#!/bin/bash\n" + LOG, EXE)
write(os.path.join(shims, "mise"), "#!/bin/bash\n" + LOG, EXE)
# The assistant setup checks for; nothing here runs a turn.
write(os.path.join(shims, "opencode"), "#!/bin/bash\n" + LOG
      + '[ "$1" = --version ] && echo 1.0\nexit 0\n', EXE)
# setup-mac.sh refuses anything but a Mac; the shim keeps the suite independent of uname.
write(os.path.join(shims, "uname"), "#!/bin/bash\necho Darwin\n", EXE)

try:
    for tool in ("launchctl", "tailscale", "curl", "brew", "mise", "uname"):
        where = shutil.which(tool, path=PATH)
        if where != os.path.join(shims, tool):
            print("REFUSED: %s resolves to %s, not the shim; nothing was run"
                  % (tool, where))
            sys.exit(1)

    # ai-config: its own origin, with two install scripts that only say they
    # ran.
    aorigin = os.path.join(work, "ai-config.git")
    run(["git", "init", "-q", "--bare", "-b", "main", aorigin])
    aseed = os.path.join(work, "ai-config-seed")
    run(["git", "init", "-q", "-b", "main", aseed])
    git(aseed, "remote", "add", "origin", aorigin)
    commit(aseed, {"scripts/install.sh": 'echo ai-install >>"$HOST_CALLS"\n',
                   "scripts/install-clis.sh": 'echo install-clis >>"$HOST_CALLS"\n'},
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
                "scripts/speech-model.sh",
                "board/bootstrap.sh", "board/install.sh", "Brewfile",
                "board/scripts/launchd/tutor-board.plist", "scripts/brew-upgrade.py"):
        real[rel] = read(os.path.join(ATLAS, rel))
    real["mise.toml"] = '[tools]\nnode = "22"\n'
    real["mise.lock"] = "root 1\n"
    real.update({
        ".gitignore": "/ai-config/\n",
        "projects/M/tools/widget.sh": (
            'T_NAME="widget"\nT_BIN="widget"\nT_BIN_DIR="$HOME/.widget/bin"\n'
            'T_INSTALL=\'mkdir -p "$HOME/.widget/bin" && '
            'printf "#!/bin/sh\\necho widget 1.0\\n" >"$HOME/.widget/bin/widget" && '
            'chmod +x "$HOME/.widget/bin/widget" && echo widget-install >>"$HOST_CALLS"\'\n'
            'T_MANUAL="by hand"\nT_UPDATE="true"\nT_VERSION="widget"\nT_CHECK="widget"\n'
            'T_EVERY_DAYS=1\nT_STALE_DAYS=14\n'),
        "board/test/tracked.py": "import sys\nsys.exit(0)\n",
        "upkeep/upkeep.py": ('import os, sys\n'
                             'with open(os.environ["HOST_CALLS"], "a") as fh:\n'
                             '    fh.write("upkeep.py " + " ".join(sys.argv[1:]) + "\\n")\n'
                             'print("changed: 0")\n'),
        "upkeep/setup-mac.sh": ('echo upkeep-setup >>"$HOST_CALLS"\n'
                                'echo "== what only you can do"\n'
                                'echo "  nothing: open a new terminal"\n'),
        "projects/A/uv.lock": "a 1\n", "projects/B/go.sum": "b 1\n",
        "projects/M/mise.toml": '[tools]\nrust = "1.80.0"\n',
        "projects/M/mise.lock": "m 1\n", "projects/M/app/Cargo.toml": "[package]\n",
        "projects/M/app/Cargo.lock": "m 1\n", "courses/C/notes.md": "c 1\n"})
    os.makedirs(os.path.join(seed, "board"))
    os.symlink(os.path.join(ROOT, "tutorboard"), os.path.join(seed, "board", "tutorboard"))
    commit(seed, real, "seed")
    host = os.path.join(work, "host")
    run(["git", "clone", "-q", origin, host])
    run(["git", "clone", "-q", aorigin, os.path.join(host, "ai-config")])
    setup = os.path.join(host, "scripts", "setup-mac.sh")

    # A retired project's virtualenv, which subjects.walk would list.
    write(os.path.join(host, "projects", "Paper-Writer", ".venv", "pyvenv.cfg"), "x\n")
    # A stray board from before, loaded, with its plist.
    write(AGENT, "<plist/>\n")
    write(LOADED, "tutor-board\natlas.brew-upgrade\n")
    RETIRED = os.path.join(home, "Library", "LaunchAgents", "atlas.brew-upgrade.plist")
    write(RETIRED, "<plist/>\n")
    commit(seed, {"courses/C/notes.md": "c 2\n"}, "elsewhere")

    # Mode 600: setup's check is the board's, which refuses a key file every
    # account can read.
    write(os.path.join(home, ".config", "tutor-board", "keys.env"),
          "DEEPSEEK_API_KEY=sk-test\n", stat.S_IRUSR | stat.S_IWUSR)

    # =======================================================================
    # setup-mac.sh, the host
    # =======================================================================
    open(CALLS, "w").close()
    code, out = run(["bash", setup])
    check("setup-mac.sh as the host ends clean", code == 0
          and "THE MAC IS UP TO DATE" in out and "FAILED" not in out, out)
    check("a retired project holding only caches is deleted, and said",
          not os.path.exists(os.path.join(host, "projects", "Paper-Writer"))
          and "deleted projects/Paper-Writer" in out, out)
    check("it pulls main", git(host, "rev-parse", "HEAD")
          == git(origin, "rev-parse", "main"), out)
    check("and runs scripts/setup.sh, ai-config's install.sh and upkeep's opencode phase",
          "Brewfile.all rewritten" in out and calls("ai-install")
          and calls("upkeep.py") == ["upkeep.py opencode"]
          and "ok    opencode 1.0" in out, (out, read(CALLS)))
    check("setup.sh bundles the union, builds the mise subject and installs its tool",
          [l for l in calls("brew") if l.startswith("brew bundle install --no-upgrade")]
          and "mise install --locked -- rust" in calls("mise")
          and "mise install --locked -- node" in calls("mise")
          and "mise exec -- cargo fetch --locked" in calls("mise")
          and calls("widget-install") == ["widget-install"]
          and "1 tool(s) declared, 0 problem(s)" in out, (out, read(CALLS)))
    check("it installs the one board LaunchAgent",
          any(l.startswith("launchctl bootstrap") and l.endswith("/tutor-board.plist")
              for l in calls("launchctl"))
          and os.path.exists(AGENT) and "tutor-board" in read(LOADED),
          "\n".join(calls("launchctl")))
    check("retires atlas.brew-upgrade and links atlas-brew",
          "atlas.brew-upgrade" not in read(LOADED).split()
          and not os.path.exists(RETIRED)
          and os.path.islink(os.path.join(home, ".local", "bin", "atlas-brew")), out)
    check("serves the board on the tailnet and checks 8778",
          any(l.startswith("tailscale serve --bg") for l in calls("tailscale"))
          and calls("curl") and "the board answers on 127.0.0.1:8778" in out,
          (calls("tailscale"), calls("curl")))
    check("fetches the whisper model once",
          len(calls("model-fetch")) == 1 and "whisper model" in out, out)

    # The second run changes nothing.
    open(CALLS, "w").close()
    code, out = run(["bash", setup])
    said = read(CALLS).splitlines()
    check("a second run ends clean and says the Mac is up to date",
          code == 0 and "THE MAC IS UP TO DATE" in out and "FAILED" not in out, out)
    check("and changes nothing: no union rewritten, no tool installed",
          "Brewfile.all unchanged" in out and "widget-install" not in said, (out, said))
    check("no agent reloaded and no tailscale serve",
          not [l for l in said if l.startswith("launchctl bootstrap")
               or l.startswith("tailscale serve --bg")], said)
    check("and the whisper model left alone",
          "whisper model ggml-small-q5_1.bin unchanged" in out
          and not calls("model-fetch"), out)

    # A retired project holding anything but caches may hold the owner's only
    # copy of their work, ignored or untracked: it is kept and named. One
    # holding only caches goes. And when git does not answer, an empty answer
    # is not "nothing tracked": every one is kept.
    proj = lambda *rel: os.path.join(host, "projects", *rel)
    write(proj("Paper-Writer", "Manuscripts", "paper.md"), "the owner's draft\n")
    write(proj("Paper-Writer", ".venv", "pyvenv.cfg"), "x\n")
    write(proj("Meetings", "agenda-2026.md"), "the owner's agenda\n")
    write(proj("TRD-EHR", ".venv", "pyvenv.cfg"), "x\n")
    write(proj("TRD-EHR", "pkg", "__pycache__", "m.cpython-313.pyc"), "x\n")
    write(proj("TRD-EHR", ".DS_Store"), "x\n")
    code, out = run(["bash", setup])
    check("a retired project holding the owner's files is kept, and said",
          read(proj("Paper-Writer", "Manuscripts", "paper.md")) == "the owner's draft\n"
          and read(proj("Meetings", "agenda-2026.md")) == "the owner's agenda\n"
          and "projects/Paper-Writer was kept" in out
          and "projects/Meetings was kept" in out and code != 0, out)
    check("and one holding only caches is deleted",
          not os.path.exists(proj("TRD-EHR")) and "deleted projects/TRD-EHR" in out, out)
    shutil.rmtree(proj("Paper-Writer"))
    shutil.rmtree(proj("Meetings"))
    gitfail = os.path.join(work, "gitfail")
    write(os.path.join(gitfail, "git"), "#!/bin/bash\n"
          'for a in "$@"; do [ "$a" = ls-files ] && exit 128; done\n'
          'exec %s "$@"\n' % shutil.which("git", path=PATH), EXE)
    write(proj("PSYCH-ASR", ".venv", "pyvenv.cfg"), "x\n")
    p = subprocess.run(["bash", setup], cwd=work, input="",
                       env=dict(ENV, PATH=gitfail + os.pathsep + ENV["PATH"]),
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       universal_newlines=True, timeout=300)
    check("when git does not answer, a retired project is kept, and said",
          os.path.exists(proj("PSYCH-ASR", ".venv", "pyvenv.cfg"))
          and "projects/PSYCH-ASR was kept: git did not answer" in p.stdout, p.stdout)
    shutil.rmtree(proj("PSYCH-ASR"))

    # =======================================================================
    # board pull
    # =======================================================================
    open(CALLS, "w").close()
    commit(seed, {"projects/A/uv.lock": "a 2\n", "courses/C/notes.md": "c 3\n"},
           "A's lock moves")
    commit(aseed, {"rules.md": "new\n"}, "a3")
    code, out = run([sys.executable, BOARD, "pull", "--atlas", host])
    check("`board pull` fast-forwards Atlas", code == 0
          and git(host, "rev-parse", "HEAD") == git(origin, "rev-parse", "main"), out)
    check("and names the subject whose lockfile moved, and no other",
          "lockfiles moved in projects/A;" in out and "projects/B" not in out
          and "courses/C" not in out, out)
    check("and fast-forwards ai-config, relinking it",
          git(os.path.join(host, "ai-config"), "rev-parse", "HEAD")
          == git(aorigin, "rev-parse", "main")
          and "ai-config: moved to" in out and calls("ai-install"), out)

    commit(seed, {"projects/B/go.sum": "b 2\n"}, "B's lock moves")
    code, out = run([sys.executable, BOARD, "pull", "--quiet", "--atlas", host])
    check("--quiet still names it", code == 0
          and "lockfiles moved in projects/B;" in out and "projects/A" not in out, out)

    commit(seed, {"projects/M/mise.lock": "m 2\n"}, "M's mise lock moves")
    code, out = run([sys.executable, BOARD, "pull", "--atlas", host])
    check("a subject with a mise.toml is named when its mise.lock moves",
          code == 0 and "lockfiles moved in projects/M;" in out, out)
    commit(seed, {"projects/M/app/Cargo.lock": "m 2\n"}, "M's Cargo lock moves")
    code, out = run([sys.executable, BOARD, "pull", "--atlas", host])
    check("and when a lockfile one directory down moves",
          code == 0 and "lockfiles moved in projects/M;" in out, out)
    commit(seed, {"projects/M/target/Cargo.lock": "out\n",
                  "projects/M/app/src/Cargo.lock": "deep\n"}, "not a marker's")
    code, out = run([sys.executable, BOARD, "pull", "--atlas", host])
    check("but not one in target/ or two down", code == 0 and "lockfiles" not in out, out)
    commit(seed, {"projects/M/warden/build.zig.zon": ".{ .version = \"2\" }\n"},
           "M's warden manifest moves")
    code, out = run([sys.executable, BOARD, "pull", "--atlas", host])
    check("a build.zig.zon one directory down is its own lockfile, and named",
          code == 0 and "lockfiles moved in projects/M;" in out, out)
    commit(seed, {"projects/M/zig-pkg/build.zig.zon": "fetched\n"}, "a fetched package's")
    code, out = run([sys.executable, BOARD, "pull", "--atlas", host])
    check("but not one in zig-pkg/", code == 0 and "lockfiles" not in out, out)

    code, out = run([sys.executable, BOARD, "pull", "--atlas", host])
    check("nothing new names nothing", code == 0 and "lockfiles" not in out, out)

    acopy = os.path.join(host, "ai-config")
    write(os.path.join(acopy, "mine.md"), "local\n")
    git(acopy, "add", "-A")
    git(acopy, "commit", "-qm", "local")
    commit(aseed, {"theirs.md": "x\n"}, "a4")
    code, out = run([sys.executable, BOARD, "pull", "--atlas", host])
    check("an ai-config that will not fast-forward is exit 1, said",
          code == 1 and "ai-config: not moved forward" in out, out)
finally:
    shutil.rmtree(work, ignore_errors=True)

print()
if fails:
    print("%d FAILURES" % len(fails))
    sys.exit(1)
print("the one Mac is the host: setup installs and serves the board, a rerun "
      "changes nothing, and its pull names what to rebuild")
