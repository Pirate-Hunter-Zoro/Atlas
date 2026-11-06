#!/usr/bin/env python3
"""`scripts/setup-mac.sh` step 4: OpenCode, DeepSeek and the parity layer.

    python3 board/test/opencode_setup.py

Step 4's opencode block runs alone, cut from setup-mac.sh, with a temp HOME
per case and fakes first on PATH for opencode, npm, brew, launchctl, curl and
ps, so neither the real HOME nor the real OpenCode server is reached. The block
runs the real `upkeep.py opencode`, which installs the real `upkeep/opencode/`
layer into the temp HOME; the agents case first runs the real `upkeep.py
install --repo`, as step 3 does. Checks: the missing key is a named problem,
counted once when step 3 already named it; a key installs the plugin, agents,
commands, capabilities, config, coder, the plugin's packages and OpenCode's
auth.json (mode 600); a second run changes nothing; with the server's agent
loaded, the first run restarts it and the second restarts nothing, and with
it not loaded a change it would need is a named problem; a server older than
its files (step 3's upkeep run installed them) is restarted once, and the run
after changes and restarts nothing; an opencode that does not run and a server
that does not answer are named problems.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = subprocess.run(["git", "-C", HERE, "rev-parse", "--show-toplevel"],
                      stdout=subprocess.PIPE, universal_newlines=True,
                      check=True).stdout.strip()
MAC = os.path.join(ROOT, "scripts", "setup-mac.sh")
SERVE = "com.mikeyferguson.opencode-serve"

work = tempfile.mkdtemp(prefix="opencode-setup-")
fake = os.path.join(work, "bin")
os.makedirs(fake)
NPM_LOG = os.path.join(work, "npm.log")
LAUNCHCTL_LOG = os.path.join(work, "launchctl.log")

fails = []


def check(name, cond, detail=""):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name + (("\n       " + str(detail)) if detail else ""))


def write(path, text, mode=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    if mode is not None:
        os.chmod(path, mode)


def read(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return ""


def tool(name, body, shell="/bin/sh"):
    write(os.path.join(fake, name), "#!" + shell + "\n" + body + "\n", 0o755)


tool("opencode", 'if [ "${1:-}" = "--version" ]; then echo 1.19.5; fi\nexit 0')
tool("brew", "exit 0")
tool("curl", "exit 0")
LSTART = os.path.join(work, "serve.lstart")
# ps: the server's start time, when a case sets one; nothing else.
tool("ps", 'if [ "$1 $2" = "-o lstart=" ] && [ -f "%s" ]; then cat "%s"; fi\nexit 0'
     % (LSTART, LSTART))
# npm: logs its argv; names opencode-ai in allow-scripts; an install into a
# prefix lays down the pinned packages that prefix's package.json names.
tool("npm", r'''
import json, os, sys
args = sys.argv[1:]
with open(%r, "a") as fh:
    fh.write(" ".join(args) + "\n")
if args[:3] == ["config", "get", "allow-scripts"]:
    print("opencode-ai")
elif args[:1] == ["install"] and "--prefix" in args:
    prefix = args[args.index("--prefix") + 1]
    with open(os.path.join(prefix, "package.json")) as fh:
        pins = json.load(fh).get("dependencies") or {}
    for name, version in pins.items():
        d = os.path.join(prefix, "node_modules", name)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "package.json"), "w") as fh:
            json.dump({"name": name, "version": version}, fh)
''' % NPM_LOG, shell="/usr/bin/python3")
# launchctl: logs its argv and keeps the loaded labels in a file beside it.
tool("launchctl", r'''
import json, os, sys
args = sys.argv[1:]
log = %r
state = log + ".loaded"
with open(log, "a") as fh:
    fh.write(" ".join(args) + "\n")
try:
    with open(state) as fh:
        have = json.load(fh)
except (OSError, ValueError):
    have = []
if args[:1] == ["print"]:
    if args[1].split("/")[-1] not in have:
        sys.exit(113)
    if os.path.exists(log + ".pid"):
        print("x = {\n\tpid = 4321\n}")
    sys.exit(0)
if args[:1] == ["kickstart"] and os.path.exists(log + ".pid"):
    import time
    with open(%r, "w") as fh:
        fh.write(time.strftime("%%a %%b %%d %%H:%%M:%%S %%Y") + "\n")
if args[:1] == ["bootstrap"]:
    label = os.path.basename(args[2])[:-len(".plist")]
    have = have if label in have else have + [label]
elif args[:1] == ["bootout"]:
    have = [l for l in have if l != args[1].split("/")[-1]]
with open(state, "w") as fh:
    json.dump(have, fh)
''' % (LAUNCHCTL_LOG, LSTART), shell="/usr/bin/python3")

# Apple's /usr/bin/python3 caches bytecode under ~/Library/Caches; that is
# the interpreter's, not a file setup installs.
BASE = dict(os.environ, PATH=fake + ":/usr/bin:/bin", PYTHONDONTWRITEBYTECODE="1")
for name in ("DEEPSEEK_API_KEY", "OPENCODE_CONFIG_CONTENT", "UPKEEP_HOME",
             "UPKEEP_STATE_DIR", "UPKEEP_REEXEC", "XPC_SERVICE_NAME", "XDG_CONFIG_HOME",
             "XDG_STATE_HOME", "PYTHONPATH"):
    BASE.pop(name, None)
for name in ("opencode", "npm", "brew", "launchctl", "curl", "ps"):
    got = shutil.which(name, path=BASE["PATH"])
    if got != os.path.join(fake, name):
        sys.exit("REFUSED: %s resolves to %s, not the fake" % (name, got))


def env_for(home):
    return dict(BASE, HOME=home)


ENV = env_for(os.path.join(work, "home"))


def home(*parts, env=None):
    return os.path.join((env or ENV)["HOME"], *parts)


def step4_block():
    """setup-mac.sh's step 4 from the line that makes OpenCode's data
    directory to step 5: everything after ai-config."""
    mac = read(MAC)
    start = mac.index('mkdir -p -m 700 "$HOME/.local/share/opencode"')
    return mac[start:mac.index('echo "== 5.', start)]


HARNESS = ("problems=0\ngood() { printf '  ok    %s\\n' \"$*\"; }\n"
           "warn() { printf '  ----  %s\\n' \"$*\"; problems=$((problems + 1)); }\n"
           "LOGS=\"$1\"\ncd \"$2\" || exit 9\n" + step4_block()
           + "echo \"problems=$problems\"\nexit \"$problems\"\n")
STEP3_NAMED_KEY = ("== what only you can do\n  1. Put the DeepSeek API key in "
                   "~/.config/api-keys/deepseek_key (one line, chmod 600)\n")


def run(env=None, upkeep_log="== what only you can do\n  nothing\n"):
    """Step 4's opencode block; (its problem count, its output)."""
    env = env or ENV
    logs = os.path.join(work, "logs-" + os.path.basename(env["HOME"]))
    write(os.path.join(logs, "upkeep.log"), upkeep_log)
    p = subprocess.run(["bash", "-c", HARNESS, "step4", logs, ROOT], env=env,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       universal_newlines=True, timeout=300)
    return p.returncode, p.stdout


def unloaded(out):
    """1 when step 4 named the server's agent as not loaded, else 0: in a
    HOME with no step 3, every run that changes a file the server reads."""
    return int("----  the OpenCode server agent is not loaded" in out)


def step3(env):
    """What step 3's upkeep run does that step 4 relies on: `upkeep.py install
    --repo`, which writes and loads the server's LaunchAgent."""
    p = subprocess.run(["/usr/bin/python3", os.path.join(ROOT, "upkeep", "upkeep.py"),
                        "install", "--repo", ROOT], env=env,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       universal_newlines=True, timeout=300)
    return p.returncode, p.stdout


def config(env=None):
    with open(home(".config", "opencode", "opencode.jsonc", env=env), encoding="utf-8") as fh:
        return json.load(fh)


def auth(env=None):
    with open(home(".local", "share", "opencode", "auth.json", env=env),
              encoding="utf-8") as fh:
        return json.load(fh)


def snapshot(root):
    """{relative path: (kind, content hash, mode, mtime)} of every file and
    link under root. upkeep's log, which every run appends to, and its lock,
    which holds the running pid, are left out."""
    out = {}
    skip = [os.path.join(".local", "state", "upkeep", n) for n in ("upkeep.log",
                                                                  "upkeep.lock")]
    for dirpath, dirnames, filenames in os.walk(root):
        for name in filenames + [d for d in dirnames
                                 if os.path.islink(os.path.join(dirpath, d))]:
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, root)
            if rel in skip:
                continue
            st = os.lstat(path)
            if os.path.islink(path):
                out[rel] = ("link", os.readlink(path), st.st_mode, st.st_mtime_ns)
            else:
                with open(path, "rb") as fh:
                    digest = hashlib.sha1(fh.read()).hexdigest()
                out[rel] = ("file", digest, st.st_mode, st.st_mtime_ns)
    return out


def launchctl_calls():
    return [l for l in read(LAUNCHCTL_LOG).splitlines() if l.strip()]


try:
    # ---- one command sets up a Mac -------------------------------------
    block = step4_block()
    check("setup-mac.sh step 4 runs upkeep's opencode phase itself",
          "upkeep/upkeep.py opencode" in block
          and not os.path.exists(os.path.join(ROOT, "scripts", "setup-opencode.sh")))
    check("step 4 keeps no key code of its own: upkeep's key sync is the one order",
          "DEEPSEEK_API_KEY" not in block and "api-keys" not in block)

    # ---- no key: the tools still install, and the key is a named problem ----
    code, out = run()
    check("a missing DeepSeek key is a named problem when step 3 did not name it",
          code == 1 + unloaded(out) and "----  no DeepSeek key" in out
          and "api-keys/deepseek_key" in out, (code, out))
    check("files the server reads changed with its agent not loaded: one named problem",
          unloaded(out) and "file(s) it reads changed; log out and in" in out, out)
    code, out = run(upkeep_log=STEP3_NAMED_KEY)
    check("and is counted once, in step 3, when step 3 named it",
          code == 0 and "----  no DeepSeek key" not in out
          and "the DeepSeek key is step 3's owner step" in out, (code, out))
    check("no auth.json is written without a key",
          not os.path.exists(home(".local", "share", "opencode", "auth.json")))
    check("step 4 loads no LaunchAgent and restarts nothing",
          not [c for c in launchctl_calls() if c.split()[0] != "print"], launchctl_calls())
    check("with no server agent loaded, nothing is said of the server",
          "OpenCode server" not in out, out)

    # ---- a key installs the whole layer --------------------------------
    write(home(".config", "api-keys", "deepseek_key"), "sk-test-key\n", 0o600)
    code, out = run()
    check("with the key in api-keys/deepseek_key step 4 succeeds",
          code == unloaded(out) and "ok    opencode, the DeepSeek key and the parity layer" in out
          and "ok    opencode 1.19.5" in out, (code, out))
    check("the key never reaches the output", "sk-test-key" not in out, out)
    check("the parity plugin is installed",
          os.path.isfile(home(".config", "opencode", "plugins", "parity.ts")))
    check("capabilities, agents and commands are installed",
          os.path.isfile(home(".config", "opencode", "capabilities.md"))
          and os.path.isfile(home(".config", "opencode", "agents", "deep.md"))
          and os.path.isfile(home(".config", "opencode", "commands", "ultracode.md")))
    check("opencode.jsonc names DeepSeek and the parity primary tools",
          config().get("model") == "deepseek/deepseek-flash"
          and "wakeup" in config().get("experimental", {}).get("primary_tools", []),
          config())
    check("the coder link is executable",
          os.access(home("bin", "coder"), os.X_OK))
    check("the parity state directory is made",
          os.path.isdir(home(".local", "state", "opencode")))
    check("OpenCode's auth.json carries the key, mode 600",
          auth().get("deepseek", {}).get("key") == "sk-test-key"
          and (os.stat(home(".local", "share", "opencode", "auth.json")).st_mode
               & 0o777) == 0o600,
          auth())
    check("the key file stays mode 600",
          (os.stat(home(".config", "api-keys", "deepseek_key")).st_mode
           & 0o777) == 0o600)
    check("the pinned plugin packages are installed in the config directory",
          ("--prefix " + home(".config", "opencode")) in read(NPM_LOG)
          and os.path.isfile(home(".config", "opencode", "node_modules", "@opencode-ai",
                                  "plugin", "package.json")), read(NPM_LOG))

    # ---- idempotent ----------------------------------------------------
    os.remove(NPM_LOG)
    code, again = run()
    check("a second run changes nothing",
          code == 0 and "(0 change(s))" in again, (code, again))
    check("and installs no package again",
          "install" not in read(NPM_LOG), read(NPM_LOG))

    # ---- a key from keys.env reaches OpenCode and the canonical file ----
    write(home(".config", "api-keys", "deepseek_key"), "")
    write(home(".config", "tutor-board", "keys.env"),
          "# comment\nexport DEEPSEEK_API_KEY='sk-from-env'\n", 0o600)
    code, out = run()
    check("a key in keys.env is copied to auth.json and the canonical file",
          code == unloaded(out) and auth()["deepseek"]["key"] == "sk-from-env"
          and read(home(".config", "api-keys", "deepseek_key")).strip() == "sk-from-env",
          (code, out))
    check("and that key never reaches the output", "sk-from-env" not in out, out)

    # ---- with the server's agent: a first run restarts, a second changes nothing ----
    agents = env_for(os.path.join(work, "agents"))
    write(home(".config", "api-keys", "deepseek_key", env=agents), "sk-agents\n", 0o600)
    code, said = step3(agents)
    check("step 3's upkeep install writes the server's LaunchAgent and loads it",
          code == 0
          and os.path.isfile(home("Library", "LaunchAgents", SERVE + ".plist", env=agents))
          and any(c.startswith("bootstrap ") and SERVE in c for c in launchctl_calls()),
          (code, said, launchctl_calls()))
    os.remove(LAUNCHCTL_LOG)
    code, out = run(env=agents)
    calls = launchctl_calls()
    check("with the agent loaded the first run succeeds", code == 0, (code, out))
    check("the first run restarts the server once, because its files changed",
          len([c for c in calls if c.startswith("kickstart -k ")
               and c.endswith("/" + SERVE)]) == 1
          and "ok    restarted the OpenCode server" in out, (calls, out))
    check("and finds it answering on 4096",
          "ok    the OpenCode server answers on 127.0.0.1:4096" in out, out)
    check("the agents key never reaches the output", "sk-agents" not in out, out)

    os.remove(LAUNCHCTL_LOG)
    before = snapshot(agents["HOME"])
    code, out = run(env=agents)
    calls = launchctl_calls()
    after = snapshot(agents["HOME"])
    moved = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
    check("with the agent loaded the second run succeeds", code == 0, (code, out))
    check("the second run changes no file in HOME", moved == [], moved)
    check("the second run restarts nothing and reloads nothing",
          not [c for c in calls if c.split()[0] in ("kickstart", "bootstrap", "bootout")]
          and "left running: nothing it reads changed" in out, (calls, out))

    # ---- a server older than its files: step 3's upkeep run (or an hourly
    # one) installed them without a restart. This run restarts it once, and
    # the run after changes and restarts nothing.
    write(LAUNCHCTL_LOG + ".pid", "4321\n")
    write(LSTART, time.strftime("%a %b %d %H:%M:%S %Y",
                                time.localtime(time.time() - 3600)) + "\n")
    os.remove(LAUNCHCTL_LOG)
    code, out = run(env=agents)
    calls = launchctl_calls()
    check("a server started before the files it reads is restarted once",
          code == 0 and len([c for c in calls if c.startswith("kickstart -k ")]) == 1
          and "restarted the OpenCode server" in out and "newer than it" in out,
          (code, calls, out))
    os.remove(LAUNCHCTL_LOG)
    before = snapshot(agents["HOME"])
    code, out = run(env=agents)
    calls = launchctl_calls()
    moved = sorted(k for k, v in snapshot(agents["HOME"]).items() if before.get(k) != v)
    check("and the run after it changes nothing and restarts nothing",
          code == 0 and moved == [] and not [c for c in calls if c.startswith("kickstart")]
          and "left running" in out, (code, moved, calls, out))
    write(LSTART, time.strftime("%a %b %d %H:%M:%S %Y",
                                time.localtime(time.time() + 300)) + "\n")
    os.remove(LAUNCHCTL_LOG)
    code, out = run(env=agents)
    calls = launchctl_calls()
    check("a server started after them is left running, and nothing is named",
          code == 0 and not [c for c in calls if c.startswith("kickstart")]
          and "left running" in out and "newer than it" not in out, (code, calls, out))

    # ---- a repair restarts the server; a file it does not read does not ----
    os.remove(LAUNCHCTL_LOG + ".pid")
    jsonc = home(".config", "opencode", "opencode.jsonc", env=agents)
    cfg = config(env=agents)
    cfg["permission"] = "ask"
    write(jsonc, json.dumps(cfg, indent=2) + "\n")
    os.remove(LAUNCHCTL_LOG)
    code, out = run(env=agents)
    check("a config the server reads, repaired: the server restarts",
          code == 0 and config(env=agents).get("permission") == "allow"
          and len([c for c in launchctl_calls() if c.startswith("kickstart -k ")]) == 1,
          (code, launchctl_calls(), out))
    os.remove(home("bin", "coder", env=agents))
    os.remove(LAUNCHCTL_LOG)
    code, out = run(env=agents)
    check("a file the server does not read (~/bin/coder) is restored without a restart",
          code == 0 and os.access(home("bin", "coder", env=agents), os.X_OK)
          and not [c for c in launchctl_calls() if c.startswith("kickstart")]
          and "left running" in out, (code, launchctl_calls(), out))

    # ---- a server that does not answer, and an opencode that does not run ----
    tool("curl", "exit 7")
    tool("opencode", "exit 1")
    code, out = run(env=agents)
    check("an opencode that does not run and a server that does not answer are named",
          code == 3 and "----  opencode is broken after a reinstall" in out
          and "----  opencode does not run" in out
          and "----  the OpenCode server does not answer" in out, (code, out))
finally:
    shutil.rmtree(work, ignore_errors=True)

print("%d FAILURES" % len(fails) if fails
      else "setup-mac.sh step 4 installs the layer and the key, once")
sys.exit(1 if fails else 0)
