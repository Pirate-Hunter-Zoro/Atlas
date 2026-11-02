#!/usr/bin/env python3
"""`board doctor` is a one-turn DeepSeek smoke test and one vision probe.

    python3 test/doctor.py

A fake opencode (`TUTORBOARD_OPENCODE`) stands in: it answers its prompt's code
word, answers without it, fails the way a spent balance does, or hangs. It runs
the way the runner sends a turn: the recipe's `headless_first` argv, the
recipe's environment, nothing on stdin, in a scratch directory with `PWD`
saying so. The vision endpoint is a socket on this machine.

  - ONE TURN, ONE LINE, THEN ONE LINE FOR THE VISION ROUTE.
  - A PASS IS AN ANSWER CARRYING THE CODE WORD, which is in the prompt and
    nowhere else; exit 0 alone is not one.
  - A TURN THAT CANNOT RUN HERE IS NAMED, with `recipes.ready`'s reason, and no
    process is started.
  - ONE FAILURE IS EXIT 1, and nothing is written outside the scratch
    directory: no limit mark, no cost line.
  - THE VISION PROBE IS THE WITNESS STRIP ALONE, whose digits must come back.
  - `--dry` SPENDS NO TURN, and neither does a doctor run inside a turn.
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
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

box = tempfile.mkdtemp(prefix="doctor-test-")
os.environ["BOARD_STATE_DIR"] = os.path.join(box, "state")
os.environ.setdefault("BOARD_NO_TAILNET", "1")

from tutorboard import keys, limits, paths, seeing             # noqa: E402
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


XDG = os.path.join(box, "xdg")
os.makedirs(os.path.join(XDG, "tutor-board"))
paths.KEYS = os.path.join(XDG, "tutor-board", "keys.env")
paths.DEEPSEEK_KEY = os.path.join(XDG, "api-keys", "deepseek_key")
with open(paths.KEYS, "w") as fh:
    fh.write("DEEPSEEK_API_KEY=sk-doctor\n")
os.chmod(paths.KEYS, 0o600)
keys.forget()

SEEN = os.path.join(box, "seen.jsonl")
MODE = os.path.join(box, "mode")
FAKE = os.path.join(box, "opencode")
with open(FAKE, "w") as fh:
    fh.write(r'''#!/usr/bin/env python3
import json, os, re, sys, time
mode = open(%(mode)r).read().strip()
argv = sys.argv[1:]
with open(%(seen)r, "a") as fh:
    fh.write(json.dumps({"mode": mode, "argv": argv, "cwd": os.getcwd(),
                         "pwd": os.environ.get("PWD"),
                         "key": os.environ.get("DEEPSEEK_API_KEY"),
                         "stdin": sys.stdin.read()}) + "\n")
word = re.search(r"code word (\S+)", argv[-1]).group(1)
def text(t):
    print(json.dumps({"type": "text", "sessionID": "s", "part": {"text": t}}))
if mode == "good":
    text(word)
elif mode == "mute":
    text("Hello!")
elif mode == "limited":
    print(json.dumps({"type": "error", "sessionID": "s",
                      "error": {"data": {"message": "Insufficient Balance"}}}))
    sys.exit(1)
elif mode == "hang":
    time.sleep(60)
''' % {"seen": SEEN, "mode": MODE})
os.chmod(FAKE, 0o755)
os.environ["TUTORBOARD_OPENCODE"] = FAKE


def mode(m):
    with open(MODE, "w") as fh:
        fh.write(m)


# The vision endpoint: answers with the witness code, or without it.
seeing._code = lambda: "424-242"
SAYS = {"text": "CODE: 424-242\na strip"}


class Eyes(BaseHTTPRequestHandler):
    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length") or 0))
        body = json.dumps({"choices": [{"message": {"content": SAYS["text"]}}]})
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body.encode())

    def log_message(self, *a):
        pass


srv = HTTPServer(("127.0.0.1", 0), Eyes)
threading.Thread(target=srv.serve_forever, daemon=True).start()
recipes.DEEPSEEK["vision"]["endpoint"] = ("http://127.0.0.1:%d/chat/completions"
                                          % srv.server_port)


def seen():
    try:
        return [json.loads(l) for l in open(SEEN)]
    except OSError:
        return []


def run(dry=False):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = doctor.cmd_doctor(dry=dry)
    return code, out.getvalue()


try:
    mode("good")
    code, out = run()
    lines = out.strip().splitlines()
    check("one line for the turn, then one for the vision route",
          len(lines) == 2 and lines[0].split()[1] == "deepseek"
          and lines[1].split()[1] == "vision", out)
    check("a turn that says the code word back passes, and so does the exit",
          lines[0].startswith("ok   deepseek") and "answered in" in lines[0]
          and code == 0, out)
    check("the vision route that reads the witness strip back passes",
          lines[1].startswith("ok   vision") and "deepseek-flash" in lines[1], out)
    first = seen()[0]
    check("the turn is the runner's: the recipe's argv, the prompt last",
          first["argv"][:3] == ["--pure", "run", "--auto"]
          and "--format" in first["argv"])
    check("in a scratch directory that PWD names, and gone afterwards",
          first["pwd"] and os.path.realpath(first["pwd"]) == os.path.realpath(first["cwd"])
          and "tutor-doctor-" in first["cwd"] and not os.path.exists(first["cwd"]))
    check("with the key in the environment, and nothing on stdin",
          first["key"] == "sk-doctor" and first["stdin"] == "")
    check("and the code word is in the prompt",
          re.search(r"code word doctor-\d{6}", first["argv"][-1]) is not None)

    mode("mute")
    code, out = run()
    check("one that exits 0 without the code word fails, says what it said "
          "instead, and is exit 1",
          code == 1 and out.startswith("FAIL deepseek") and "Hello" in out, out)

    mode("good")
    SAYS["text"] = "I see no image"
    code, out = run()
    vline = out.strip().splitlines()[-1]
    check("a vision route that answers without the strip's digits fails",
          code == 1 and vline.startswith("FAIL vision") and "cannot see" in vline, out)
    SAYS["text"] = "CODE: 424-242\na strip"

    mode("limited")
    code, out = run()
    check("a spent balance fails in DeepSeek's own words",
          code == 1 and "Insufficient Balance" in out, out)
    check("and doctor writes no limit mark: the runner owns that",
          not limits.limited_until())

    before = len(seen())
    os.environ["TUTORBOARD_OPENCODE"] = "a-command-no-machine-has"
    code, out = run()
    check("a missing opencode is named, with the reason",
          code == 1 and "FAIL deepseek" in out and "not on the path" in out, out)
    check("and no process is started for it", len(seen()) == before)
    os.environ["TUTORBOARD_OPENCODE"] = FAKE

    mode("hang")
    ok, line = doctor.smoke(timeout=2)
    check("a turn that hangs is cut at the cap and says so",
          not ok and "timed out" in line, line)

    # --- dry: no turn ----------------------------------------------------
    mode("good")
    before = len(seen())
    code, out = run(dry=True)
    check("--dry says what would run, and starts nothing",
          code == 0 and "dry  deepseek" in out and FAKE in out
          and len(seen()) == before, out)
    check("and names the vision route without asking it",
          "dry  vision    would ask 127.0.0.1 deepseek-flash" in out, out)

    # --- `board doctor`, the command ---------------------------------------
    board.machine_check = lambda: True
    out = io.StringIO()
    os.environ["TUTORBOARD_TURN"] = "1"
    with contextlib.redirect_stdout(out):
        code = board.main(["doctor"])
    check("inside a turn `board doctor` is dry: a turn never starts a turn",
          "inside a turn: dry" in out.getvalue()
          and "dry  deepseek" in out.getvalue() and len(seen()) == before,
          out.getvalue())
    del os.environ["TUTORBOARD_TURN"]

    env = dict(os.environ, XDG_CONFIG_HOME=XDG)
    env.pop("TUTORBOARD_TURN", None)
    p = subprocess.run([sys.executable, os.path.join(ROOT, "bin", "board"),
                        "doctor", "--dry"], env=env, cwd=box,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       universal_newlines=True, timeout=180)
    check("`board doctor --dry` runs from the command line: the machine, then "
          "a dry line for the turn and the vision route, and no turn",
          "python:" in p.stdout and "dry  deepseek" in p.stdout
          and "dry  vision" in p.stdout and len(seen()) == before, p.stdout[-800:])
    help_out = subprocess.run([sys.executable, os.path.join(ROOT, "bin", "board"),
                               "help"], stdout=subprocess.PIPE,
                              universal_newlines=True, timeout=60).stdout
    check("`board doctor` is documented as the smoke test, with --dry",
          "board doctor [--dry]" in help_out
          and "one real" in help_out and "vision route" in help_out)
finally:
    srv.shutdown()
    shutil.rmtree(box, ignore_errors=True)

print("%d FAILURES" % len(fails) if fails
      else "one DeepSeek turn and one look say whether it can teach")
sys.exit(1 if fails else 0)
