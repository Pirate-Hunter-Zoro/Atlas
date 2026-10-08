#!/usr/bin/env python3
"""A turn with a fake provider answers with a card.

The daemon end to end, in this process, against a recipe that is a script: an
unread message in the inbox, `runner.loop.headless` blocks on the real `board
wait`, hands the message to `take_turn`, which runs the fake provider through
`run_turn`; the provider writes a card and a `claude-json` result line. Then
the daemon is signalled, writes its handoff with the same provider, and leaves
`stopped` on its record. Nothing here reaches a network or a real provider, and
`board start` is not run: `daemon.board` is a stub.

Stdlib only.
"""

import json
import os
import shutil
import signal
import sys
import tempfile
import threading
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOX = tempfile.mkdtemp(prefix="tutor-answering-")
os.environ["XDG_CONFIG_HOME"] = os.path.join(BOX, "config")
os.environ["BOARD_STATE_DIR"] = os.path.join(BOX, "state")
os.environ.pop("TUTORBOARD_COURSES", None)
sys.path.insert(0, ROOT)
from tutorboard.agents import recipes                                # noqa: E402
from tutorboard.runner import daemon, loop                           # noqa: E402

fails = []


def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
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
if "This session is ending now" in prompt:
    with open("HANDOFF.md", "w", encoding="utf-8") as fh:
        fh.write("# Handoff\n\nThe student answered x^2 + 1.\n")
else:
    os.makedirs(os.path.join("live", "cards"), exist_ok=True)
    with open(os.path.join("live", "cards", "0001-answer.md"), "w",
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
    "default_agent": "fake",
    "agents": {"fake": {"cmd": [sys.executable], "prompt": "argv",
                        "headless": [sys.executable, PROVIDER, "{prompt}"],
                        "usage": "claude-json"}},
    "fallback": None, "only_agent": None}))

WS = os.path.join(BOX, "Fixture")
write(os.path.join(WS, "tutorboard.json"), json.dumps({"name": "Fixture"}))
write(os.path.join(WS, "live", "inbox", "messages.jsonl"), json.dumps(
    {"iso": "2026-10-08 12:00:00", "text": "my handwriting says x^2 + 1",
     "read": False}) + "\n")
CARD = os.path.join(WS, "live", "cards", "0001-answer.md")
course = {"root": WS, "dir": "Fixture", "name": "Fixture"}

# No board server: the daemon's `board start` and `board open` are a stub.
started = []
daemon.board = lambda root, *args: (started.append(list(args)) or (0, ""))


def stop_when_answered():
    end = time.time() + 120
    while time.time() < end and not os.path.exists(CARD):
        time.sleep(0.1)
    rec = os.path.join(WS, "live", "agent.json")
    while time.time() < end:
        try:
            with open(rec, encoding="utf-8") as fh:
                if json.load(fh).get("state") == "listening":
                    break
        except (OSError, ValueError):
            pass
        time.sleep(0.1)
    os.kill(os.getpid(), signal.SIGTERM)


try:
    cfg = recipes.load_config()
    name = recipes.resolve_agent(cfg, course)
    check("the fixture's config resolves its fake recipe", name == "fake")
    threading.Thread(target=stop_when_answered, daemon=True).start()
    code = loop.headless(cfg, course, name, None)
    check("the daemon comes up, takes a turn and exits 0 when signalled",
          code == 0 and started == [["start"]])
    body = open(CARD, encoding="utf-8").read() if os.path.exists(CARD) else ""
    check("the turn answered with a card", "Irreducible over the reals" in body)
    check("and the provider was handed the student's message in its prompt",
          "True" in body)
    with open(os.path.join(WS, "live", "inbox", "messages.jsonl"),
              encoding="utf-8") as fh:
        msgs = [json.loads(l) for l in fh if l.strip()]
    check("the message was taken: the inbox holds it read",
          len(msgs) == 1 and msgs[0].get("read") is True)
    with open(os.path.join(WS, "live", "agent.json"), encoding="utf-8") as fh:
        rec = json.load(fh)
    check("the record says one turn, no failure, nothing owed, and stopped",
          rec.get("turns") == 1 and not rec.get("last_error")
          and not rec.get("owed") and rec.get("state") == "stopped"
          and rec.get("agent") == "fake")
    with open(os.path.join(WS, "live", "cost.jsonl"), encoding="utf-8") as fh:
        costs = [json.loads(l) for l in fh if l.strip()]
    check("the turn and the wrap-up each wrote what they cost",
          [c.get("turn") for c in costs] == [1, 2]
          and all(c.get("tokens") == 420 and c.get("agent") == "fake"
                  for c in costs))
    handoff = os.path.join(WS, "HANDOFF.md")
    check("and the wrap-up turn wrote the handoff",
          os.path.exists(handoff)
          and "x^2 + 1" in open(handoff, encoding="utf-8").read())
    log = open(os.path.join(WS, "live", "agent.log"), encoding="utf-8").read()
    check("the log says the handoff was written", "handoff written" in log)
finally:
    shutil.rmtree(BOX, ignore_errors=True)

print("%d FAILURES" % len(fails) if fails
      else "a turn with a fake provider answers with a card")
sys.exit(1 if fails else 0)
