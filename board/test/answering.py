#!/usr/bin/env python3
"""A turn with a fake provider answers with a card.

The runner end to end, in this process, against a recipe that is a script: a
message in a stored session's inbox, `service.Runner` takes it, `take_turn`
runs the fake provider through `run_turn` in the Atlas root; the provider
writes a card into TUTORBOARD_SESSION and a `claude-json` result line. Then
End queues the wrap-up, which writes the handoff with the same provider.
Nothing here reaches a network or a real provider.

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
from tutorboard import sessions                                      # noqa: E402
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


# The provider: a card for a turn, HANDOFF.md for the wrap-up, and the result
# object Claude Code prints under `--output-format json` either way.
PROVIDER = os.path.join(BOX, "provider.py")
write(PROVIDER, r'''import json, os, sys
prompt = sys.argv[1]
session = os.environ["TUTORBOARD_SESSION"]
if "This session is ending now" in prompt:
    with open(os.path.join("courses", "Fixture", "HANDOFF.md"), "w",
              encoding="utf-8") as fh:
        fh.write("# Handoff\n\nThe student answered x^2 + 1.\n")
else:
    with open(os.path.join(session, "cards", "0001-answer.md"), "w",
              encoding="utf-8") as fh:
        fh.write("---\nkind: lesson\n---\n\nIrreducible over the reals: "
                 "%s\n" % ("handwriting" in prompt))
print(json.dumps({"type": "result", "is_error": False, "result": "done",
                  "num_turns": 2, "total_cost_usd": 0.01, "session_id": "fx",
                  "usage": {"input_tokens": 100, "output_tokens": 20,
                            "cache_creation_input_tokens": 0,
                            "cache_read_input_tokens": 300}}))
''')
write(recipes.CONFIG, json.dumps({
    "provider": "fake",
    "agents": {"fake": {"cmd": [sys.executable], "prompt": "argv",
                        "headless": [sys.executable, PROVIDER, "{prompt}"],
                        "usage": "claude-json"}},
    "fallback": None}))

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
    cfg = recipes.load_config()
    name = recipes.resolve(cfg)[0]
    check("the fixture's config resolves its fake recipe", name == "fake")
    check("a line that wakes queues a turn", runner.wake(SID))
    wait(lambda: settled(1))
    body = open(CARD, encoding="utf-8").read() if os.path.exists(CARD) else ""
    check("the turn answered with a card", "Irreducible over the reals" in body)
    check("and the provider was handed the student's message in its prompt",
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
          and rec.get("agent") == "fake", rec)
    log = open(os.path.join(LIVE, "agent.log"), encoding="utf-8").read()
    check("no wrap-up ran without End", "handoff ===" not in log)
    check("End queues the wrap-up", runner.end(SID))
    wait(lambda: settled(2))
    with open(os.path.join(LIVE, "cost.jsonl"), encoding="utf-8") as fh:
        costs = [json.loads(l) for l in fh if l.strip()]
    check("the turn and the wrap-up each wrote what they cost",
          [c.get("turn") for c in costs] == [1, 2]
          and all(c.get("tokens") == 420 and c.get("agent") == "fake"
                  for c in costs))
    handoff = os.path.join(WS, "HANDOFF.md")
    check("and the wrap-up turn wrote the handoff",
          os.path.exists(handoff)
          and "x^2 + 1" in open(handoff, encoding="utf-8").read())
    log = open(os.path.join(LIVE, "agent.log"), encoding="utf-8").read()
    check("the log says the handoff was written", "handoff written" in log)
finally:
    runner.shutdown()
    shutil.rmtree(BOX, ignore_errors=True)

print("%d FAILURES" % len(fails) if fails
      else "a turn with a fake provider answers with a card")
sys.exit(1 if fails else 0)
