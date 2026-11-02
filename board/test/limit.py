#!/usr/bin/env python3
"""An allowance that has run out, and the lesson that waits for it.

The strangest kind of broken: the board answers, the machine is healthy, the
network is fine, opencode is installed, and no lesson can be taught, because
DeepSeek says the balance is spent or the requests too many. Treated as an
ordinary failed turn it is invisible in the worst way -- the board shows a
tutor listening, the student sends again, and nothing comes back.

So the tutor says so where it can be read, the message stays owed, and the
board says when the allowance returns.

Three rules underneath, and each is here because getting it wrong is silent:

  - a limit belongs to this machine's DeepSeek account: one record, with the
    node, because the home directory is shared;
  - it expires by itself, and a turn that goes through clears it. A limit
    cleared by hand outlives itself;
  - and what a limit LOOKS like is DeepSeek's own words, which config.json's
    `usage_limit_says` may replace.
"""

import json
import os
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

errors = []


def ok(m):
    print("ok   " + m)


def fail(m):
    errors.append(m)
    print("FAIL " + m)


def check(m, cond):
    ok(m) if cond else fail(m)


# A state directory of our own. BOARD_STATE_DIR exists for exactly this: a test
# that wrote the real one would take this machine out of service.
box = tempfile.mkdtemp()
os.environ["BOARD_STATE_DIR"] = box
os.environ["BOARD_NODE_NAME"] = "test-node"
# And no real tailnet. Anything here that asks where a course is served knocks
# on every peer the netmap lists, and with a Mullvad exit-node subscription on
# the tailnet that is 544 machines -- so `bash test/all.sh` once stopped here and
# never came back. The whole suite hung on a unit test about arithmetic over
# `/health` documents.
os.environ["BOARD_NO_TAILNET"] = "1"

from tutorboard import limits, paths

paths.STATE_DIR = box
limits.LIMIT_RECORD = os.path.join(box, "limited.json")
paths.CONFIG = os.path.join(box, "config.json")           # no user config

# ---- reading a failed turn -------------------------------------------------
now = 1_700_000_000.0

check("DeepSeek's exhausted balance is a limit",
      limits.reads_as_usage_limit("Insufficient Balance", now)
      == now + limits.DEFAULT_LIMIT_WINDOW)
check("and so is the HTTP 402 that carries it",
      limits.reads_as_usage_limit("API Error: 402 Payment Required: balance", now))
check("and a rate limit, in either of the words it comes in",
      limits.reads_as_usage_limit('{"type":"rate_limit_error"}', now)
      and limits.reads_as_usage_limit("429 Too Many Requests", now))
check("an ordinary broken turn is not a limit",
      limits.reads_as_usage_limit("Error: ENOENT no such file", now) is None)
check("a dropped connection is NOT a limit: it is the network, and the egress "
      "check answers that one",
      limits.reads_as_usage_limit(
          "API Error: Connection dropped (ECONNRESET)", now) is None)
check("nor is a turn that said nothing at all",
      limits.reads_as_usage_limit("", now) is None)
check("and no other vendor's phrasing is in the defaults",
      not any("usage limit reached" in p or "quota" in p
              for p in limits.DEFAULT_USAGE_LIMIT_SAYS))
with open(paths.CONFIG, "w") as fh:
    json.dump({"usage_limit_says": [r"out of tokens\|(\d{9,})"]}, fh)
check("config.json's own phrases replace the defaults, and a captured epoch "
      "is believed when it is within a day",
      abs(limits.reads_as_usage_limit("out of tokens|%d" % int(now + 7200), now)
          - (now + 7200)) < 2
      and limits.reads_as_usage_limit("Insufficient Balance", now) is None)
check("one a year out is a misread, and gets the ordinary window",
      limits.reads_as_usage_limit("out of tokens|%d" % int(now + 400 * 86400), now)
      == now + limits.DEFAULT_LIMIT_WINDOW)
os.remove(paths.CONFIG)

# ---- the record ------------------------------------------------------------
check("with nothing written, the machine has its allowance", limits.limited_until() == 0)
limits.mark_limited(time.time() + 900)
check("a limit reads back", limits.limited_until() > time.time())
check("one record, the machine's: until and node",
      set(limits.limit_record()) == {"until", "node"})
limits.clear_limited()
check("and clearing it clears it", limits.limited_until() == 0)

# A RECORD FROM WHEN THERE WERE SEVERAL ASSISTANTS counts only DeepSeek's entry.
with open(limits.LIMIT_RECORD, "w", encoding="utf-8") as fh:
    json.dump({"node": "test-node", "at": time.time(),
               "agents": {"claude": time.time() + 900}}, fh)
check("a per-agent record with only another assistant's limit is no limit",
      limits.limited_until() == 0)
with open(limits.LIMIT_RECORD, "w", encoding="utf-8") as fh:
    json.dump({"node": "test-node", "at": time.time(),
               "agents": {"claude": time.time() + 900,
                          "deepseek": time.time() + 1800}}, fh)
check("and DeepSeek's entry in one is the limit",
      limits.limited_until() > time.time() + 1700)

limits.mark_limited(time.time() - 60)
check("a limit that has expired is no limit; it does not need clearing by hand",
      limits.limited_until() == 0)

# The home directory is shared between compute nodes. A limit hit by the
# allocation that ended yesterday is not this machine's news.
with open(limits.LIMIT_RECORD, "w", encoding="utf-8") as fh:
    json.dump({"until": time.time() + 900, "node": "some-other-node"}, fh)
check("a limit written by another machine is not this machine's",
      limits.limited_until() == 0)

with open(limits.LIMIT_RECORD, "w", encoding="utf-8") as fh:
    fh.write("{not json")
check("a corrupt record is an allowance, not a crash", limits.limited_until() == 0)

# ---- what the tutor does about it ------------------------------------------
src = "".join(open(os.path.join(ROOT, "tutorboard", "runner", f), encoding="utf-8").read()
              for f in ("loop.py", "daemon.py", "service.py"))

check("a limit is asked about before the network is blamed -- the turn itself "
      "answered that one, and DeepSeek saying so means it was reached",
      src.index("reads_as_usage_limit") < src.index("if not egress.egress_ok():"))
check("the machine is marked, which is what /health then publishes",
      "limits.mark_limited(until)" in src)
check("the message whose turn was lost is carried, not dropped -- and to "
      "DISK, because the process holding it is the thing most likely to be "
      "signalled next",
      "return {\"owed\": owe(ctx, out), \"error\": err}" in src
      and "def owe(ctx, msg):" in src
      and "agent_state(ctx.live, owed=msg or None)" in src)
check("and the next turn answers what was owed first, since the inbox lines it "
      "came from are already marked read",
      "owed = daemon.owed_message(repo.live)" in src and "def owed_message(live):" in src)
check("and the board is told the message is held, so it does not advise "
      "sending the same work again",
      "limited=until, retrying=True)" in src)
check("and the log says it waits, and where to see until when",
      "message waits for it" in src and "`board limit` says when" in src)
check("a turn that goes through clears the limit", "limits.clear_limited()" in src)
check("and `ready` refuses a turn while the limit stands, so none is spent on it",
      "limits.limited_until(now=now)" in open(os.path.join(
          ROOT, "tutorboard", "agents", "recipes.py"), encoding="utf-8").read())

health = open(os.path.join(ROOT, "tutorboard", "server", "routes",
                           "machines.py"), encoding="utf-8").read()
check("a board publishes its machine's allowance, because only it can know",
      '"limited": limits.limited_until()' in health)

print("\n%d FAILURES" % len(errors) if errors
      else "\na spent allowance is said, and the message waits for it")
sys.exit(1 if errors else 0)
