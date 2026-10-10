#!/usr/bin/env python3
"""`board doctor` is a one-turn smoke test per provider.

    python3 test/doctor.py

Fake providers stand in: one script that answers its prompt's code word, one
that answers without it, one that fails the way a provider out of allowance
does, and one that hangs. Each runs the way the runner sends a turn: the
recipe's `headless_first` argv with the usage flags, the recipe's environment,
nothing on stdin, in a scratch directory with `PWD` saying so.

  - BY DEFAULT IT ASKS THE PROVIDER AND THE FALLBACK, one line each.
  - A PASS IS AN ANSWER CARRYING THE CODE WORD, which is in the prompt and
    nowhere else; exit 0 alone is not one.
  - A RECIPE THAT CANNOT TAKE A TURN HERE IS NAMED, with the resolver's reason,
    and no process is started for it.
  - ONE FAILURE IS EXIT 1, and nothing is written outside the scratch
    directory: no limit mark, no cost line.
  - `--dry` SPENDS NO TURN, and neither does a doctor run inside a turn.
    `board doctor --dry` runs on a fixture config, from the command line.
"""

import contextlib
import importlib.machinery
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

box = tempfile.mkdtemp(prefix="doctor-test-")
os.environ["BOARD_STATE_DIR"] = os.path.join(box, "state")
os.environ.setdefault("BOARD_NO_TAILNET", "1")

from tutorboard import limits                                  # noqa: E402
from tutorboard.agents import doctor, recipes                  # noqa: E402

loader = importlib.machinery.SourceFileLoader("boardcli", os.path.join(ROOT, "bin", "board"))
spec = importlib.util.spec_from_loader("boardcli", loader)
board = importlib.util.module_from_spec(spec)
loader.exec_module(board)

fails = []


def check(name, cond, detail=""):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name + (("\n       " + str(detail)) if detail else ""))


SEEN = os.path.join(box, "seen.jsonl")
FAKE = os.path.join(box, "fake-provider")
with open(FAKE, "w") as fh:
    fh.write(r'''#!/usr/bin/env python3
import json, os, re, sys, time
mode, argv = sys.argv[1], sys.argv[2:]
with open(%(seen)r, "a") as fh:
    fh.write(json.dumps({"mode": mode, "argv": argv, "cwd": os.getcwd(),
                         "pwd": os.environ.get("PWD"),
                         "key": os.environ.get("FAKE_RECIPE_ENV"),
                         "stdin": sys.stdin.read()}) + "\n")
prompt = [a for a in argv if "code word" in a][0]
word = re.search(r"code word (\S+)", prompt).group(1)
if mode == "good":
    print(json.dumps({"type": "result", "is_error": False, "result": word}))
elif mode == "mute":
    print(json.dumps({"type": "result", "is_error": False, "result": "Hello!"}))
elif mode == "limited":
    print("API Error: Claude AI usage limit reached")
    sys.exit(1)
elif mode == "hang":
    time.sleep(60)
''' % {"seen": SEEN})
os.chmod(FAKE, 0o755)


def fake(mode, **kw):
    s = {"cmd": [FAKE], "headless_first": [FAKE, mode, "{prompt}"],
         "usage": "claude-json", "usage_args": ["--output-format", "json"],
         "env": {"FAKE_RECIPE_ENV": "from-the-recipe"}}
    s.update(kw)
    return s


CFG = {"provider": "good", "fallback": "mute", "agents": {
    "good": fake("good"), "mute": fake("mute"), "limited": fake("limited"),
    "hang": fake("hang"),
    "gone": fake("good", cmd=["a-command-no-machine-has"]),
    "colibri": fake("good", private="it reads phi")}}


def seen():
    try:
        return [json.loads(l) for l in open(SEEN)]
    except OSError:
        return []


def run(args, cfg=CFG, dry=False):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = doctor.cmd_doctor(cfg, args, dry=dry)
    return code, out.getvalue()


try:
    code, out = run([])
    lines = out.strip().splitlines()
    check("by default it asks the provider and the fallback, one line each",
          len(lines) == 2 and lines[0].split()[1] == "good"
          and lines[1].split()[1] == "mute", out)
    check("the provider that says the code word back passes",
          lines[0].startswith("ok   good") and "answered in" in lines[0], out)
    check("one that exits 0 without it fails, and says what it said instead",
          lines[1].startswith("FAIL mute") and "Hello" in lines[1], out)
    check("and one failure is exit 1", code == 1)
    first = seen()[0]
    check("the turn is the runner's: the recipe's argv with the usage flags",
          first["argv"][-2:] == ["--output-format", "json"])
    check("in a scratch directory that PWD names, and gone afterwards",
          first["pwd"] and os.path.realpath(first["pwd"]) == os.path.realpath(first["cwd"])
          and "tutor-doctor-" in first["cwd"] and not os.path.exists(first["cwd"]))
    check("with the recipe's own environment, and nothing on stdin",
          first["key"] == "from-the-recipe" and first["stdin"] == "")
    check("and the code word is in the prompt",
          re.search(r"code word doctor-\d{6}", " ".join(first["argv"])) is not None)

    code, out = run(["good"])
    check("a named recipe is the only one asked, and a pass is exit 0",
          code == 0 and out.startswith("ok   good") and len(out.splitlines()) == 1, out)

    code, out = run(["limited"])
    check("a provider out of allowance fails in its own words",
          code == 1 and "usage limit reached" in out, out)
    check("and doctor writes no limit mark: the runner owns that",
          not limits.limited_until("limited"))

    before = len(seen())
    code, out = run(["gone", "colibri"])
    check("a recipe whose binary is missing is named, with the reason",
          "FAIL gone" in out and "not on the path" in out, out)
    check("and an in-fence model is refused, in words",
          "FAIL colibri" in out and "in-fence" in out, out)
    check("and no process is started for either", len(seen()) == before)

    real_timeout = doctor.DOCTOR_TURN_SECONDS
    ok, line = doctor.smoke(CFG, "hang", timeout=2)
    check("a provider that hangs is cut at the cap and says so",
          not ok and "timed out" in line, line)

    # --- dry: no turn ----------------------------------------------------
    before = len(seen())
    code, out = run([], dry=True)
    check("--dry names each recipe and what would run, and starts nothing",
          code == 0 and "dry  good" in out and "dry  mute" in out
          and FAKE in out and len(seen()) == before, out)
    code, out = run(["gone"], dry=True)
    check("and a recipe that cannot take a turn still fails it, with the reason",
          code == 1 and "FAIL gone" in out and "not on the path" in out, out)

    # --- `board doctor`, the command ---------------------------------------
    board.machine_check = lambda: True
    real = recipes.load_config
    recipes.load_config = lambda: CFG
    try:
        out = io.StringIO()
        os.environ["TUTORBOARD_TURN"] = "1"
        with contextlib.redirect_stdout(out):
            code = board.main(["doctor"])
        check("inside a turn `board doctor` is dry: a turn never starts a turn",
              code == 0 and "inside a turn: dry" in out.getvalue()
              and "dry  good" in out.getvalue() and len(seen()) == before,
              out.getvalue())
        del os.environ["TUTORBOARD_TURN"]
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = board.main(["doctor", "good"])
        check("and outside one it spends the turn on the recipe named",
              code == 0 and "ok   good" in out.getvalue()
              and len(seen()) == before + 1, out.getvalue())
    finally:
        recipes.load_config = real
        os.environ.pop("TUTORBOARD_TURN", None)

    xdg = os.path.join(box, "xdg")
    os.makedirs(os.path.join(xdg, "tutor-board"))
    with open(os.path.join(xdg, "tutor-board", "config.json"), "w") as fh:
        json.dump(CFG, fh)
    env = dict(os.environ, XDG_CONFIG_HOME=xdg)
    env.pop("TUTORBOARD_TURN", None)
    before = len(seen())
    p = subprocess.run([sys.executable, os.path.join(ROOT, "bin", "board"),
                        "doctor", "--dry"], env=env, cwd=box,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       universal_newlines=True, timeout=180)
    check("`board doctor --dry` runs on a fixture config: the machine, then a "
          "dry line each for its provider and fallback, and no turn",
          "python:" in p.stdout and "dry  good" in p.stdout
          and "dry  mute" in p.stdout and len(seen()) == before, p.stdout[-800:])
    help_out = subprocess.run([sys.executable, os.path.join(ROOT, "bin", "board"),
                               "help"], stdout=subprocess.PIPE,
                              universal_newlines=True, timeout=60).stdout
    check("`board doctor` is documented as the smoke test, with --dry",
          "board doctor [--dry] [name ...]" in help_out
          and "one real turn" in help_out)
finally:
    shutil.rmtree(box, ignore_errors=True)

print("%d FAILURES" % len(fails) if fails
      else "one turn per provider says whether it can answer")
sys.exit(1 if fails else 0)
