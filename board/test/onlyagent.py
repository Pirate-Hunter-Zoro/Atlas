#!/usr/bin/env python3
"""Claude is gone: the system runs with `only_agent` set and no other assistant.

    python3 test/onlyagent.py

A temporary `XDG_CONFIG_HOME` holds a copy of this machine's `config.json`
(the built-in defaults where there is none) with `"only_agent": "deepseek"`
laid over it, and a `keys.env` with a fake DeepSeek key. PATH is rebuilt as a
directory of links to every executable on it except `claude`, `codex` and
`opencode`; a fake `opencode` stands in front, so nothing here spends a cent.
Under that environment:

  - A WORKSPACE NAMING CLAUDE RESOLVES TO DEEPSEEK, with the policy line, and
    so does a config whose `default_agent` and `vision_agent` still say claude.
  - THE BOARD'S LISTING SHOWS THE OTHERS BARRED, read the way the board reads
    it (`assistants.listing`, which runs `tutor --agents --json`).
  - A HEADLESS TURN IS BUILT FOR OPENCODE and runs: the recipe's argv with the
    model on the command line, the key through the environment, the resumed
    form with `--continue`.
  - AN IMAGE HAS A ROUTE with nobody running and a vision_agent of claude.
  - THE SUITES THAT TOUCH AGENTS PASS under the same environment.
"""

import io
import json
import os
import atexit
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

GONE = ("claude", "codex")
POLICY = "this machine is running DeepSeek only"
FAKE_KEY = "sk-onlyagent-test-not-a-key"

fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


box = tempfile.mkdtemp(prefix="onlyagent-")
# Removed however the suite ends, an exception included.
atexit.register(shutil.rmtree, box, True)

# ---- the configuration: the machine's, copied, plus the switch ---------------
real_dir = os.path.join(os.environ.get("XDG_CONFIG_HOME")
                        or os.path.join(os.path.expanduser("~"), ".config"),
                        "tutor-board")
xdg = os.path.join(box, "xdg")
conf_dir = os.path.join(xdg, "tutor-board")
os.makedirs(conf_dir)
machine = {}
try:
    with open(os.path.join(real_dir, "config.json"), encoding="utf-8") as fh:
        machine = json.load(fh) or {}
except (OSError, ValueError):
    pass
machine["only_agent"] = "deepseek"
with open(os.path.join(conf_dir, "config.json"), "w", encoding="utf-8") as fh:
    json.dump(machine, fh, indent=2)
with open(os.path.join(conf_dir, "keys.env"), "w", encoding="utf-8") as fh:
    fh.write("DEEPSEEK_API_KEY=%s\n" % FAKE_KEY)
os.chmod(os.path.join(conf_dir, "keys.env"), 0o600)

# ---- PATH: everything except the other assistants ---------------------------
farm = os.path.join(box, "bin")
os.makedirs(farm)
for d in os.environ.get("PATH", "").split(os.pathsep):
    try:
        names = os.listdir(d)
    except OSError:
        continue
    for n in names:
        if n in GONE + ("opencode",) or os.path.lexists(os.path.join(farm, n)):
            continue
        p = os.path.join(d, n)
        if os.path.isfile(p) and os.access(p, os.X_OK):
            os.symlink(p, os.path.join(farm, n))

fake_dir = os.path.join(box, "fake")
os.makedirs(fake_dir)
state = os.path.join(box, "state")
os.makedirs(state)
FAKE = r'''#!/usr/bin/env python3
import json, os, sys
with open(os.path.join(os.environ["ONLY_FAKE_STATE"], "argv.jsonl"), "a") as fh:
    fh.write(json.dumps({"argv": sys.argv[1:],
                         "key": os.environ.get("DEEPSEEK_API_KEY", ""),
                         "anthropic": sorted(k for k in os.environ
                                             if k.startswith("ANTHROPIC_")),
                         "pwd": os.environ.get("PWD", ""),
                         "cwd": os.getcwd()}) + "\n")
print(json.dumps({"type": "text", "sessionID": "ses_only",
                  "part": {"type": "text", "text": "answered"}}))
'''
with open(os.path.join(fake_dir, "opencode"), "w", encoding="utf-8") as fh:
    fh.write(FAKE)
os.chmod(os.path.join(fake_dir, "opencode"), 0o755)

ENV = dict(os.environ,
           XDG_CONFIG_HOME=xdg,
           PATH=fake_dir + os.pathsep + farm,
           ONLY_FAKE_STATE=state,
           BOARD_STATE_DIR=os.path.join(box, "board-state"),
           BOARD_NO_TAILNET="1")
# The shell's own provider variables would stand in for the copy's keys.env.
for k in [k for k in ENV if k.startswith("ANTHROPIC_") or k == "DEEPSEEK_API_KEY"]:
    del ENV[k]
os.environ.clear()
os.environ.update(ENV)

check("claude and codex are not on this PATH",
      all(shutil.which(n) is None for n in GONE))
check("and the fake opencode is",
      shutil.which("opencode") == os.path.join(fake_dir, "opencode"))
check("python3, git and node still are",
      all(shutil.which(n) for n in ("python3", "git", "node")))

# Loaded after the environment is set: CONFIG and the key store are read off
# XDG_CONFIG_HOME at import.
from tutorboard.agents import recipes  # noqa: E402
from tutorboard.runner import turn as runturn  # noqa: E402
from tutorboard.agents import usage  # noqa: E402
from tutorboard import assistants, keys, seeing                  # noqa: E402

check("tutor reads the temporary config", recipes.CONFIG ==
      os.path.join(conf_dir, "config.json"))
cfg = recipes.load_config()
check("which carries the switch", recipes.only_agent(cfg) == "deepseek")

# ---- resolution --------------------------------------------------------------
ws = os.path.join(box, "ws")
os.makedirs(os.path.join(ws, "live"))
said, why = [], []
check("a workspace naming claude resolves to deepseek",
      recipes.resolve_agent(cfg, {"root": ws, "agent": "claude"},
                          say=said.append, why=why) == "deepseek")
check("with the policy line, naming the layer and the config line",
      len(why) == 1 and POLICY in why[0]
      and "this workspace's tutorboard.json asks for 'claude'" in why[0]
      and '"only_agent": "deepseek"' in why[0])
claude_cfg = dict(cfg, default_agent="claude", vision_agent="claude")
check("so does a machine whose default_agent still says claude",
      recipes.resolve_agent(claude_cfg, {}, say=lambda m: None) == "deepseek")
check("claude and codex are barred by the switch, not merely missing",
      recipes.agent_unavailable(cfg, "claude") == POLICY
      and recipes.agent_unavailable(cfg, "codex") == POLICY)
check("deepseek is available: installed, keyed, not barred",
      recipes.agent_unavailable(cfg, "deepseek") is None
      and keys.unkeyed(cfg["agents"]["deepseek"]) is None)
check("a turn wanted by claude is handed to deepseek, never elsewhere",
      recipes.choose_agent(cfg, "claude")[0] == "deepseek")

# ---- the board's listing -----------------------------------------------------
assistants.forget()
table = assistants.listing() or {}
rows = {a["name"]: a for a in table.get("agents") or []}
check("the board's listing names the switch",
      (table.get("only") or {}).get("agent") == "deepseek"
      and (table.get("only") or {}).get("why") == POLICY)
check("and shows claude and codex barred with its sentence",
      all((rows.get(n) or {}).get("barred") == POLICY for n in GONE))
check("deepseek unbarred, installed and keyed",
      not rows.get("deepseek", {}).get("barred")
      and not rows.get("deepseek", {}).get("missing")
      and not rows.get("deepseek", {}).get("unkeyed"))
check("and the machine's own answer is deepseek", table.get("machine") == "deepseek")
p = subprocess.run([sys.executable, os.path.join(ROOT, "bin", "tutor"), "--agents"],
                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
text = p.stdout.decode()
check("`tutor --agents` says the switch and marks the others off",
      p.returncode == 0 and "only: this machine is running DeepSeek only" in text
      and all(any(line.lstrip(" *").split()[:1] == [n]
                  and "off: " + POLICY in line
                  for line in text.splitlines())
              for n in GONE))

# ---- an image, with nobody running and a vision_agent of claude --------------
got, no = seeing.route(None, dict(table, vision_agent="claude", default="claude"))
check("an image routes through the switch's recipe when vision_agent and "
      "default still name claude",
      (got or {}).get("agent") == "deepseek"
      and seeing.route_host(got) == "api.deepseek.com")

# ---- a headless turn, built and run for opencode -----------------------------
dspec = cfg["agents"]["deepseek"]
use, template, fresh = runturn.turn_plan(dspec, 0, 1)
cmd = usage.with_usage(dspec, [a.replace("{prompt}", "hello from the test")
                               for a in use])
check("a fresh headless turn is opencode run with the model on the command line",
      fresh and os.path.basename(cmd[0]) == "opencode" and "run" in cmd
      and cmd[cmd.index("-m") + 1] == "deepseek/deepseek-flash"
      and "hello from the test" in cmd)
env = runturn.turn_environment(dspec)
check("its environment carries the key from keys.env and no Anthropic routing",
      (env or {}).get("DEEPSEEK_API_KEY") == FAKE_KEY
      and not any(k.startswith("ANTHROPIC_") for k in env))
log = io.open(os.path.join(box, "turn.log"), "w")
rc, timed_out = runturn.run_turn(cmd, ws, log, 30, env=env)
log.close()
ran = [json.loads(line) for line in open(os.path.join(state, "argv.jsonl"))]
check("the turn runs through opencode and exits 0",
      rc == 0 and not timed_out and len(ran) == 1)
check("with the key, the model, no ANTHROPIC_* and PWD at the workspace",
      ran and ran[0]["key"] == FAKE_KEY and not ran[0]["anthropic"]
      and "deepseek/deepseek-flash" in ran[0]["argv"]
      and os.path.realpath(ran[0]["pwd"]) == os.path.realpath(ws))
use2, _, fresh2 = runturn.turn_plan(dspec, 1, 0)
check("a resumed turn is the --continue form of the same harness",
      not fresh2 and os.path.basename(use2[0]) == "opencode" and "--continue" in use2)

# ---- the suites that touch agents, under the same environment ----------------
SUITES = ["agents.py", "provider.py", "doctor.py", "seeing.py", "keys.py",
          "limit.py", "egress.py", "resume.py", "who.js"]
for name in SUITES:
    argv = (["node"] if name.endswith(".js") else [sys.executable]) + \
        [os.path.join(HERE, name)]
    p = subprocess.run(argv, cwd=ROOT, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=900)
    out = p.stdout.decode(errors="replace")
    check("test/%s passes with claude gone" % name, p.returncode == 0)
    if p.returncode:
        for line in out.splitlines():
            if line.startswith("FAIL") or "Error" in line:
                print("       " + line)

print()
if fails:
    print("%d check(s) failed" % len(fails))
    sys.exit(1)
print("with claude and codex gone and only_agent deepseek, every turn, listing "
      "and agent suite lands on deepseek")
