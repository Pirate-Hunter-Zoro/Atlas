#!/usr/bin/env python3
"""One prompt down the provider chain: AI use outside the board.

  * THE FIRST THAT CAN ANSWERS. A provider that is missing, unkeyed or fails
    hands the prompt to the next, and each one passed over says why.
  * THE WORK DECIDES, NOT THE EXIT CODE. `done` False moves on.
  * A LONG PROMPT GOES IN A FILE the agent is told to read, and the file is
    gone afterwards.

No model: the recipes are shell commands.
"""

import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("BOARD_STATE_DIR", tempfile.mkdtemp(prefix="oneshot-state-"))
from tutorboard import limits                                   # noqa: E402
from tutorboard.agents import oneshot                           # noqa: E402

limits.LIMIT_RECORD = os.path.join(os.environ["BOARD_STATE_DIR"], "limited.json")
fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


def sh(script):
    return {"cmd": ["sh"], "headless_first": ["sh", "-c", script, "x", "{prompt}"]}


box = tempfile.mkdtemp(prefix="oneshot-")
try:
    cfg = {"provider": "broken", "agents": {
        "broken": sh("echo down >&2; exit 1"),
        "ghost": {"cmd": ["no-such-agent-cli"],
                  "headless_first": ["no-such-agent-cli", "{prompt}"]},
        "idle": sh("echo did nothing"),
        "writer": sh('printf "%s" "$1" > answer.txt; echo wrote it'),
    }}
    got = oneshot.run("the brief", box, timeout=20, cfg=cfg,
                      done=lambda n: os.path.exists(os.path.join(box, "answer.txt")))
    check("the first provider that does the work answers",
          got["ok"] and got["name"] == "writer" and "wrote it" in got["text"])
    check("every one passed over says why, in order",
          [n for n, _ in got["tried"]] == ["broken", "ghost", "idle"]
          and "not on the path" in got["tried"][1][1]
          and "did not do the work" in got["tried"][2][1])
    with open(os.path.join(box, "answer.txt")) as fh:
        check("and it got the prompt", fh.read() == "the brief")

    os.remove(os.path.join(box, "answer.txt"))
    long = "x" * (oneshot.ARGV_PROMPT + 10)
    got = oneshot.run(long, box, timeout=20, cfg=cfg, names=["writer"])
    with open(os.path.join(box, "answer.txt")) as fh:
        said = fh.read()
    check("a long prompt is handed over as a file to read",
          got["ok"] and said.startswith("Your full instructions are in the file")
          and len(said) < 300)
    check("and the file is gone afterwards",
          not [n for n in os.listdir(box) if n.startswith(".atlas-prompt-")])

    got = oneshot.run("x", box, timeout=20, cfg=cfg, names=["broken", "ghost"])
    check("when nobody can, it says so for each", not got["ok"]
          and len(got["tried"]) == 2)
finally:
    shutil.rmtree(box, ignore_errors=True)

print()
print("%d FAILURES" % len(fails) if fails else "a prompt reaches whichever "
      "provider can answer it")
sys.exit(1 if fails else 0)
