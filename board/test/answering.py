#!/usr/bin/env python3
"""A turn with a fake opencode answers with a card.

The runner end to end, in this process, against a fake opencode
(`TUTORBOARD_OPENCODE`): a message in a stored session's inbox,
`service.Runner` takes it, `take_turn` runs the fake through `run_turn` in the
Atlas root; it writes a card into TUTORBOARD_SESSION and an OpenCode
`step_finish` event. Then End queues the wrap-up, which writes the handoff the
same way. Nothing here reaches a network or DeepSeek.

Stdlib only.
"""

import json
import os
import shutil
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOX = tempfile.mkdtemp(prefix="tutor-answering-")
os.environ["XDG_CONFIG_HOME"] = os.path.join(BOX, "config")
os.environ["BOARD_STATE_DIR"] = os.path.join(BOX, "state")
os.environ.pop("TUTORBOARD_COURSES", None)
os.environ.pop("TUTORBOARD_SESSION", None)
sys.path.insert(0, ROOT)
from tutorboard import paths, sessions                               # noqa: E402
from tutorboard.agents import recipes                                # noqa: E402
from tutorboard.runner import daemon, service                        # noqa: E402

fails = []


def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name
          + (("\n       %s" % (detail,)) if detail and not cond else ""))
    if not cond:
        fails.append(name)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


# The fake: a card for a turn, TUTOR.md for the wrap-up, and the `step_finish`
# event `opencode run --format json` prints either way.
FAKE = os.path.join(BOX, "opencode")
write(FAKE, r'''#!/usr/bin/env python3
import json, os, sys
prompt = sys.argv[-1]
session = os.environ["TUTORBOARD_SESSION"]
if "This session is ending now" in prompt:
    with open(os.path.join("courses", "Fixture", "TUTOR.md"), "w",
              encoding="utf-8") as fh:
        fh.write("# Fixture\n\n## Now\n\nThe student answered x^2 + 1.\n")
else:
    with open(os.path.join(session, "cards", "0001-answer.md"), "w",
              encoding="utf-8") as fh:
        fh.write("---\nkind: lesson\n---\n\nIrreducible over the reals: "
                 "%s\n" % ("handwriting" in prompt))
print(json.dumps({"type": "step_finish", "sessionID": "fx", "part": {
    "cost": 0.01, "tokens": {"input": 100, "output": 20, "reasoning": 0,
                             "cache": {"read": 300, "write": 0}}}}))
''')
os.chmod(FAKE, 0o755)
os.environ["TUTORBOARD_OPENCODE"] = FAKE
write(paths.KEYS, "DEEPSEEK_API_KEY=sk-test\n")
os.chmod(paths.KEYS, 0o600)

ATLAS = os.path.join(BOX, "atlas")
WS = os.path.join(ATLAS, "courses", "Fixture")
write(os.path.join(WS, "tutorboard.json"), json.dumps({"name": "Fixture"}))
SID = sessions.new("fixture", base=ATLAS)["id"]
sessions.bind(SID, "courses/Fixture", base=ATLAS)
LIVE = sessions.path(SID, ATLAS)
with open(os.path.join(LIVE, "inbox", "messages.jsonl"), "a", encoding="utf-8") as fh:
    fh.write(json.dumps({"iso": "2026-10-08 12:00:00", "t": time.time(),
                         "text": "my handwriting says x^2 + 1",
                         "read": False}) + "\n")
CARD = os.path.join(LIVE, "cards", "0001-answer.md")


def record():
    return daemon.agent_record_at(LIVE) or {}


def settled(n_costs):
    """The runner is idle and `cost.jsonl` has `n_costs` rows."""
    try:
        with open(os.path.join(LIVE, "cost.jsonl"), encoding="utf-8") as fh:
            n = sum(1 for l in fh if l.strip())
    except OSError:
        n = 0
    return n >= n_costs and not runner.busy() and record().get("state") == "listening"


def wait(cond, timeout=120):
    end = time.time() + timeout
    while time.time() < end and not cond():
        time.sleep(0.1)


runner = service.Runner(ATLAS, concurrency=2).start()
try:
    check("the fixture can take a turn: the fake opencode and a key",
          recipes.ready() is None, recipes.ready())
    check("a line that wakes queues a turn", runner.wake(SID))
    wait(lambda: settled(1))
    body = open(CARD, encoding="utf-8").read() if os.path.exists(CARD) else ""
    check("the turn answered with a card", "Irreducible over the reals" in body)
    check("and DeepSeek was handed the student's message in its prompt",
          "True" in body)
    with open(os.path.join(LIVE, "inbox", "messages.jsonl"),
              encoding="utf-8") as fh:
        msgs = [json.loads(l) for l in fh if l.strip()]
    check("the message was taken: the inbox holds it read",
          msgs and all(m.get("read") is True for m in msgs))
    rec = record()
    check("the record says one turn, no failure, nothing owed, and listening",
          rec.get("turns") == 1 and not rec.get("last_error")
          and not rec.get("owed") and rec.get("state") == "listening"
          and rec.get("agent") == "deepseek", rec)
    log = open(os.path.join(LIVE, "agent.log"), encoding="utf-8").read()
    check("no wrap-up ran without End", "wrap-up ===" not in log)
    check("End queues the wrap-up", runner.end(SID))
    wait(lambda: settled(2))
    with open(os.path.join(LIVE, "cost.jsonl"), encoding="utf-8") as fh:
        costs = [json.loads(l) for l in fh if l.strip()]
    check("the turn and the wrap-up each wrote what they cost",
          [c.get("turn") for c in costs] == [1, 2]
          and all(c.get("tokens") == 420 and c.get("agent") == "deepseek"
                  and c.get("rate") for c in costs))
    memo_file = os.path.join(WS, "TUTOR.md")
    check("and the wrap-up turn brought TUTOR.md up to date",
          os.path.exists(memo_file)
          and "x^2 + 1" in open(memo_file, encoding="utf-8").read())
    log = open(os.path.join(LIVE, "agent.log"), encoding="utf-8").read()
    check("the log says TUTOR.md was written", "TUTOR.md written" in log)
finally:
    runner.shutdown()
    shutil.rmtree(BOX, ignore_errors=True)

print("%d FAILURES" % len(fails) if fails
      else "a turn with a fake opencode answers with a card")
sys.exit(1 if fails else 0)
