#!/usr/bin/env python3
"""One prompt to DeepSeek: AI use outside the board.

  * ONE ATTEMPT, ON THE BOARD'S RECIPE. A machine that cannot run a turn
    (no opencode, no key) says why without running anything.
  * THE WORK DECIDES, NOT THE EXIT CODE. `done` False is a failure.
  * A LONG PROMPT GOES IN A FILE the agent is told to read, and the file is
    gone afterwards.

No model: opencode is a fake (`TUTORBOARD_OPENCODE`).
"""

import json
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("BOARD_STATE_DIR", tempfile.mkdtemp(prefix="oneshot-state-"))
from tutorboard import keys, limits, paths                      # noqa: E402
from tutorboard.agents import oneshot                           # noqa: E402

limits.LIMIT_RECORD = os.path.join(os.environ["BOARD_STATE_DIR"], "limited.json")
fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


box = tempfile.mkdtemp(prefix="oneshot-")
paths.KEYS = os.path.join(box, "keys.env")
paths.DEEPSEEK_KEY = os.path.join(box, "deepseek_key")
FAKE = os.path.join(box, "opencode")
with open(FAKE, "w") as fh:
    fh.write("""#!/usr/bin/env python3
import json, os, sys
mode = open(os.path.join(%r, "mode")).read().strip()
with open(os.path.join(%r, "argv.json"), "w") as fh:
    json.dump({"argv": sys.argv[1:], "key": os.environ.get("DEEPSEEK_API_KEY")}, fh)
if mode == "write":
    with open("answer.txt", "w") as fh:
        fh.write(sys.argv[-1])
if mode == "fail":
    print(json.dumps({"type": "error", "sessionID": "s",
                      "error": {"data": {"message": "Insufficient Balance"}}}))
    sys.exit(1)
print(json.dumps({"type": "text", "sessionID": "s", "part": {"text": "wrote it"}}))
""" % (box, box))
os.chmod(FAKE, 0o755)
os.environ["TUTORBOARD_OPENCODE"] = FAKE
work = os.path.join(box, "work")
os.makedirs(work)


def mode(m):
    with open(os.path.join(box, "mode"), "w") as fh:
        fh.write(m)


def landed():
    return os.path.exists(os.path.join(work, "answer.txt"))


try:
    mode("write")
    keys.forget()
    got = oneshot.run("the brief", work, timeout=20)
    check("with no key nothing runs, and it says which key and where",
          not got["ok"] and "DEEPSEEK_API_KEY" in got["why"]
          and not os.path.exists(os.path.join(box, "argv.json")))

    with open(paths.KEYS, "w") as fh:
        fh.write("DEEPSEEK_API_KEY=sk-test\n")
    os.chmod(paths.KEYS, 0o600)
    keys.forget()
    got = oneshot.run("the brief", work, timeout=20, done=landed)
    check("DeepSeek answers, in the words of its text events",
          got["ok"] and got["text"] == "wrote it" and got["why"] is None)
    with open(os.path.join(work, "answer.txt")) as fh:
        check("and it got the prompt", fh.read() == "the brief")
    with open(os.path.join(box, "argv.json")) as fh:
        seen = json.load(fh)
    check("on the board's recipe, the key in the environment and not argv",
          seen["argv"][:3] == ["--pure", "run", "--auto"]
          and seen["key"] == "sk-test" and "sk-test" not in seen["argv"])

    os.remove(os.path.join(work, "answer.txt"))
    mode("idle")
    got = oneshot.run("the brief", work, timeout=20, done=landed)
    check("a clean exit that did not do the work is a failure",
          not got["ok"] and "did not do the work" in got["why"])

    mode("fail")
    got = oneshot.run("the brief", work, timeout=20)
    check("a failed turn says why in DeepSeek's own words",
          not got["ok"] and "Insufficient Balance" in got["why"])

    mode("write")
    long = "x" * (oneshot.ARGV_PROMPT + 10)
    got = oneshot.run(long, work, timeout=20)
    with open(os.path.join(work, "answer.txt")) as fh:
        said = fh.read()
    check("a long prompt is handed over as a file to read",
          got["ok"] and said.startswith("Your full instructions are in the file")
          and len(said) < 300)
    check("and the file is gone afterwards",
          not [n for n in os.listdir(work) if n.startswith(".atlas-prompt-")])
finally:
    shutil.rmtree(box, ignore_errors=True)

print()
print("%d FAILURES" % len(fails) if fails else "a prompt reaches DeepSeek, "
      "and a failure says why")
sys.exit(1 if fails else 0)
