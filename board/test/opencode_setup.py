#!/usr/bin/env python3
"""`scripts/setup-opencode.sh`: OpenCode, DeepSeek and the parity layer.

    python3 test/opencode_setup.py

A temp HOME and fake opencode/npm/brew on PATH. The script installs the real
`upkeep/opencode/install.py` into the temp config directory; `--no-agents`
keeps launchd and upkeep out of it. Checks: the missing key is a named
failure, a key installs the plugin, agents, commands, capabilities, config,
coder and OpenCode auth.json (mode 600), a second run is idempotent, and
`--dry-run` writes nothing.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SCRIPT = os.path.join(ROOT, "scripts", "setup-opencode.sh")

work = tempfile.mkdtemp(prefix="opencode-setup-")
fake = os.path.join(work, "bin")
os.makedirs(fake)
LOG = os.path.join(work, "npm.log")

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


def tool(name, body):
    write(os.path.join(fake, name), "#!/bin/sh\n" + body + "\n", 0o755)


tool("opencode", 'if [ "${1:-}" = "--version" ]; then echo 1.19.5; fi\nexit 0')
tool("npm", 'printf "%s\\n" "$*" >> "' + LOG + '"\nexit 0')
tool("brew", "exit 0")
tool("launchctl", "exit 0")

ENV = dict(os.environ, HOME=os.path.join(work, "home"),
           PATH=fake + ":/usr/bin:/bin")
for name in ("DEEPSEEK_API_KEY", "OPENCODE_CONFIG_CONTENT"):
    ENV.pop(name, None)


def home(*parts):
    return os.path.join(ENV["HOME"], *parts)


def run(*args, env=None):
    p = subprocess.run(["bash", SCRIPT] + list(args), env=env or ENV,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       universal_newlines=True, timeout=120)
    return p.returncode, p.stdout


def config():
    with open(home(".config", "opencode", "opencode.jsonc"), encoding="utf-8") as fh:
        return json.load(fh)


def auth():
    with open(home(".local", "share", "opencode", "auth.json"), encoding="utf-8") as fh:
        return json.load(fh)


try:
    # ---- no key: the tools still install, and the key is a named problem ----
    code, out = run("--no-agents", "--no-contract")
    check("a missing DeepSeek key is a named failure",
          code == 1 and "no DeepSeek key" in out
          and "api-keys/deepseek_key" in out, (code, out))
    check("and no auth.json is written without a key",
          not os.path.exists(home(".local", "share", "opencode", "auth.json")),
          os.listdir(home(".local", "share", "opencode"))
          if os.path.isdir(home(".local", "share", "opencode")) else [])

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
    with open(LOG, encoding="utf-8") as fh:
        logged = fh.read()
    check("the pinned plugin SDK is installed in the config directory",
          ("--prefix " + home(".config", "opencode")) in logged, logged)

    # ---- idempotent ----------------------------------------------------
    code, again = run("--no-agents", "--no-contract")
    check("a second run changes nothing",
          code == 0 and "parity layer up to date" in again, (code, again))

    # ---- a key from keys.env reaches OpenCode and the canonical file ----
    write(home(".config", "api-keys", "deepseek_key"), "")
    write(home(".config", "tutor-board", "keys.env"),
          "# comment\nexport DEEPSEEK_API_KEY='sk-from-env'\n", 0o600)
    code, out = run("--no-agents", "--no-contract")
    check("a key in keys.env is copied to auth.json and the canonical file",
          code == 0 and auth()["deepseek"]["key"] == "sk-from-env"
          and open(home(".config", "api-keys", "deepseek_key"),
                   encoding="utf-8").read().strip() == "sk-from-env",
          (code, out))

    # ---- dry-run writes nothing ----------------------------------------
    dry_home = os.path.join(work, "dry")
    os.makedirs(os.path.dirname(os.path.join(dry_home, "x")))
    write(os.path.join(dry_home, ".config", "api-keys", "deepseek_key"),
          "sk-dry\n", 0o600)
    dry_env = dict(ENV, HOME=dry_home)
    code, out = run("--dry-run", "--no-agents", "--no-contract", env=dry_env)
    check("--dry-run says what it would do and writes nothing",
          code == 0 and "would" in out
          and not os.path.exists(os.path.join(dry_home, ".config", "opencode"))
          and not os.path.exists(os.path.join(dry_home, ".local")), (code, out))
finally:
    shutil.rmtree(work, ignore_errors=True)

print("%d FAILURES" % len(fails) if fails
      else "the OpenCode setup script installs the layer and the key")
sys.exit(1 if fails else 0)
