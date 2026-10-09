#!/usr/bin/env python3
"""`tutor doctor` is a one-turn smoke test per provider.

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
"""

import contextlib
import importlib.machinery
import importlib.util
import io
import json
import os
import re
import shutil
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

loader = importlib.machinery.SourceFileLoader("tutor", os.path.join(ROOT, "bin", "tutor"))
spec = importlib.util.spec_from_loader("tutor", loader)
tutor = importlib.util.module_from_spec(spec)
loader.exec_module(tutor)

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


def run(args, cfg=CFG):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = doctor.cmd_doctor(cfg, args)
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

    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = tutor.main(["--help"])
    check("`tutor doctor` is documented as the smoke test",
          "tutor doctor [agent]" in out.getvalue()
          and "one real turn per provider" in out.getvalue())
finally:
    shutil.rmtree(box, ignore_errors=True)

print("%d FAILURES" % len(fails) if fails
      else "one turn per provider says whether it can answer")
sys.exit(1 if fails else 0)
