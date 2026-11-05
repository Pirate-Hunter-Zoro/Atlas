#!/usr/bin/env python3
"""`scripts/setup-opencode.sh`: OpenCode, DeepSeek and the parity layer.

    python3 board/test/opencode_setup.py

A temp HOME per case, and fakes first on PATH for opencode, npm, brew,
launchctl, curl, ps and gh, so neither the real HOME nor the real OpenCode
server is reached. The script runs the real `upkeep install` and `upkeep
opencode`, which install the real `upkeep/opencode/` layer into the temp HOME.
Checks: the missing key is a named failure; a key installs the plugin, agents,
commands, capabilities, config, coder, the plugin's packages and OpenCode's
auth.json (mode 600); with the agents, the first run restarts the server and
the second changes no file and restarts nothing; a server older than its files
(setup-mac.sh's upkeep run installed them) is restarted once, and the run
after changes and restarts nothing; `--dry-run` writes nothing and names the
restart it would make, by the same rule as the real run; setup-mac.sh counts a
missing key once.
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
SCRIPT = os.path.join(ROOT, "scripts", "setup-opencode.sh")
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
tool("gh", "exit 1")
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
for name in ("opencode", "npm", "brew", "launchctl", "curl", "ps", "gh"):
    got = shutil.which(name, path=BASE["PATH"])
    if got != os.path.join(fake, name):
        sys.exit("REFUSED: %s resolves to %s, not the fake" % (name, got))


def env_for(home):
    return dict(BASE, HOME=home)


ENV = env_for(os.path.join(work, "home"))


def home(*parts, env=None):
    return os.path.join((env or ENV)["HOME"], *parts)


def run(*args, env=None):
    p = subprocess.run(["bash", SCRIPT] + list(args), env=env or ENV,
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
    mac = read(os.path.join(ROOT, "scripts", "setup-mac.sh"))
    check("setup-mac.sh runs this script, the contract left to its own step",
          "bash scripts/setup-opencode.sh --no-contract" in mac
          and "install-clis.sh" not in mac)
    check("this script keeps no key code of its own: upkeep's key sync is the one order",
          "DEEPSEEK_API_KEY" not in read(SCRIPT) and "auth.json" not in read(SCRIPT))

    # ---- no key: the tools still install, and the key is a named problem ----
    code, out = run("--no-agents", "--no-contract")
    check("a missing DeepSeek key is a named failure",
          code == 1 and "no DeepSeek key" in out
          and "api-keys/deepseek_key" in out, (code, out))
    check("and no auth.json is written without a key",
          not os.path.exists(home(".local", "share", "opencode", "auth.json")))
    check("--no-agents loads no LaunchAgent",
          not [c for c in launchctl_calls() if c.split()[0] != "print"], launchctl_calls())

    # ---- a key installs the whole layer --------------------------------
    write(home(".config", "api-keys", "deepseek_key"), "sk-test-key\n", 0o600)
    code, out = run("--no-agents", "--no-contract")
    check("with the key in api-keys/deepseek_key the script succeeds",
          code == 0, (code, out))
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
    code, again = run("--no-agents", "--no-contract")
    check("a second run changes nothing",
          code == 0 and "nothing changed" in again, (code, again))
    check("and installs no package again",
          "install" not in read(NPM_LOG), read(NPM_LOG))

    # ---- a key from keys.env reaches OpenCode and the canonical file ----
    write(home(".config", "api-keys", "deepseek_key"), "")
    write(home(".config", "tutor-board", "keys.env"),
          "# comment\nexport DEEPSEEK_API_KEY='sk-from-env'\n", 0o600)
    code, out = run("--no-agents", "--no-contract")
    check("a key in keys.env is copied to auth.json and the canonical file",
          code == 0 and auth()["deepseek"]["key"] == "sk-from-env"
          and read(home(".config", "api-keys", "deepseek_key")).strip() == "sk-from-env",
          (code, out))
    check("and that key never reaches the output", "sk-from-env" not in out, out)

    # ---- dry-run writes nothing, and names the restart it would make ----
    dry = env_for(os.path.join(work, "dry"))
    write(home(".config", "api-keys", "deepseek_key", env=dry), "sk-dry\n", 0o600)
    before = snapshot(dry["HOME"])
    code, out = run("--dry-run", "--no-contract", env=dry)
    check("--dry-run says what it would do and writes nothing",
          code == 0 and "would" in out and snapshot(dry["HOME"]) == before
          and not os.path.exists(home(".config", "opencode", env=dry))
          and not os.path.exists(home(".local", env=dry)), (code, out))
    check("--dry-run names the server restart it would make",
          "would restart the OpenCode server" in out, out)
    check("--dry-run touches no LaunchAgent",
          not [c for c in launchctl_calls() if c.split()[0] != "print"], launchctl_calls())

    # ---- with the agents: a first run restarts, a second changes nothing ----
    agents = env_for(os.path.join(work, "agents"))
    write(home(".config", "api-keys", "deepseek_key", env=agents), "sk-agents\n", 0o600)
    code, out = run("--no-contract", env=agents)
    calls = launchctl_calls()
    check("with the agents the first run succeeds", code == 0, (code, out))
    check("the server's LaunchAgent is written into the temp HOME and loaded",
          os.path.isfile(home("Library", "LaunchAgents", SERVE + ".plist", env=agents))
          and any(c.startswith("bootstrap ") and SERVE in c for c in calls), calls)
    check("the first run restarts the server once, because its files changed",
          len([c for c in calls if c.startswith("kickstart -k ")
               and c.endswith("/" + SERVE)]) == 1
          and "restarted the OpenCode server" in out, (calls, out))
    check("the upkeep block is in the temp ~/.zprofile",
          "# >>> upkeep >>>" in read(home(".zprofile", env=agents)))
    check("the agents key never reaches the output", "sk-agents" not in out, out)

    os.remove(LAUNCHCTL_LOG)
    before = snapshot(agents["HOME"])
    code, out = run("--no-contract", env=agents)
    calls = launchctl_calls()
    after = snapshot(agents["HOME"])
    moved = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
    check("with the agents the second run succeeds", code == 0, (code, out))
    check("the second run changes no file in HOME", moved == [], moved)
    check("the second run restarts nothing and reloads nothing",
          not [c for c in calls if c.split()[0] in ("kickstart", "bootstrap", "bootout")]
          and "left running: nothing it reads changed" in out, (calls, out))
    code, out = run("--dry-run", "--no-contract", env=agents)
    check("--dry-run after a run names no restart",
          code == 0 and "would restart" not in out
          and "left running" in out, (code, out))

    # ---- a server older than its files: setup-mac.sh's upkeep run (or an
    # hourly one) installed them without a restart. This run restarts it once,
    # and the run after changes and restarts nothing.
    write(LAUNCHCTL_LOG + ".pid", "4321\n")
    write(LSTART, time.strftime("%a %b %d %H:%M:%S %Y",
                                time.localtime(time.time() - 3600)) + "\n")
    os.remove(LAUNCHCTL_LOG)
    code, out = run("--dry-run", "--no-contract", env=agents)
    check("--dry-run names the restart a server older than its files is due",
          code == 0 and "would restart the OpenCode server" in out
          and "newer than it" in out
          and not [c for c in launchctl_calls() if c.split()[0] != "print"],
          (code, launchctl_calls(), out))
    code, out = run("--no-contract", env=agents)
    calls = launchctl_calls()
    check("a server started before the files it reads is restarted once",
          code == 0 and len([c for c in calls if c.startswith("kickstart -k ")]) == 1
          and "restarted the OpenCode server" in out and "newer than it" in out,
          (code, calls, out))
    os.remove(LAUNCHCTL_LOG)
    before = snapshot(agents["HOME"])
    code, out = run("--no-contract", env=agents)
    calls = launchctl_calls()
    moved = sorted(k for k, v in snapshot(agents["HOME"]).items() if before.get(k) != v)
    check("and the run after it changes nothing and restarts nothing",
          code == 0 and moved == [] and not [c for c in calls if c.startswith("kickstart")]
          and "left running" in out, (code, moved, calls, out))
    write(LSTART, time.strftime("%a %b %d %H:%M:%S %Y",
                                time.localtime(time.time() + 300)) + "\n")
    os.remove(LAUNCHCTL_LOG)
    code, out = run("--no-contract", env=agents)
    calls = launchctl_calls()
    check("a server started after them is left running, and nothing is named",
          code == 0 and not [c for c in calls if c.startswith("kickstart")]
          and "left running" in out and "newer than it" not in out, (code, calls, out))

    # ---- the dry run and the real run restart by one rule ----------------
    os.remove(LAUNCHCTL_LOG + ".pid")
    jsonc = home(".config", "opencode", "opencode.jsonc", env=agents)
    cfg = config(env=agents)
    cfg["permission"] = "ask"
    write(jsonc, json.dumps(cfg, indent=2) + "\n")
    os.remove(LAUNCHCTL_LOG)
    code, out = run("--dry-run", "--no-contract", env=agents)
    check("a config the server reads, due a repair: --dry-run names the restart",
          code == 0 and "would restart the OpenCode server" in out, (code, out))
    code, out = run("--no-contract", env=agents)
    check("and the real run makes it",
          code == 0 and config(env=agents).get("permission") == "allow"
          and len([c for c in launchctl_calls() if c.startswith("kickstart -k ")]) == 1,
          (code, launchctl_calls(), out))
    os.remove(home("bin", "coder", env=agents))
    os.remove(LAUNCHCTL_LOG)
    code, out = run("--dry-run", "--no-contract", env=agents)
    check("a file the server does not read (~/bin/coder): --dry-run names no restart",
          code == 0 and "would restart" not in out and "left running" in out, (code, out))
    code, out = run("--no-contract", env=agents)
    check("and the real run restores it without one",
          code == 0 and os.access(home("bin", "coder", env=agents), os.X_OK)
          and not [c for c in launchctl_calls() if c.startswith("kickstart")]
          and "left running" in out, (code, launchctl_calls(), out))

    # ---- setup-mac.sh step 4 counts a missing key once ----------------------
    # Its setup-opencode block, run alone against a fake setup-opencode.sh.
    start = mac.index("if [ ! -f scripts/setup-opencode.sh ]")
    block = mac[start:mac.index('echo "== 5.', start)]
    step4 = os.path.join(work, "step4")
    write(os.path.join(step4, "scripts", "setup-opencode.sh"),
          "echo '  restarted the OpenCode server: 3 file(s) it reads changed'\n"
          "echo 'problem: no DeepSeek key: put it in ~/.config/api-keys/deepseek_key'\n"
          "echo 'problem: opencode does not run'\nexit 2\n")
    harness = ("problems=0\ngood() { printf '  ok    %s\\n' \"$*\"; }\n"
               "warn() { printf '  ----  %s\\n' \"$*\"; problems=$((problems + 1)); }\n"
               "LOGS=\"$1\"\ncd \"$2\" || exit 9\n" + block + "echo \"problems=$problems\"\n")

    def step4_run(upkeep_log):
        logs = os.path.join(work, "step4-logs")
        write(os.path.join(logs, "upkeep.log"), upkeep_log)
        p = subprocess.run(["bash", "-c", harness, "step4", logs, step4],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           universal_newlines=True, timeout=60)
        return p.stdout

    out = step4_run("== what only you can do\n  1. Put the DeepSeek API key in "
                    "~/.config/api-keys/deepseek_key (one line, chmod 600)\n")
    check("setup-mac.sh counts a missing key once when step 3 named it",
          "problems=1" in out and "no DeepSeek key" not in out
          and "opencode does not run" in out
          and "ok    restarted the OpenCode server" in out, out)
    out = step4_run("== what only you can do\n  1. Install Xcode\n")
    check("and counts it in step 4 when step 3 did not",
          "problems=2" in out and "----  no DeepSeek key" in out, out)
finally:
    shutil.rmtree(work, ignore_errors=True)

print("%d FAILURES" % len(fails) if fails
      else "the OpenCode setup script installs the layer and the key, once")
sys.exit(1 if fails else 0)
