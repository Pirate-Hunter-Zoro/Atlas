#!/usr/bin/env python3
"""An allowance that has run out, and the lesson that still has to be taught.

The strangest kind of broken: the board answers, the machine is healthy, the
network is fine, the agent is installed, and no lesson can be taught, because
the tutor has been told it has no quota left. Treated as an ordinary failed turn
it is invisible in the worst way -- the board shows a tutor listening, the
student sends again, and nothing comes back for four hours.

So the tutor says so where it can be read, and the next turn goes to whoever
can still take one, because a lesson that carries on beats a board where nobody
is home.

Three rules underneath, and each is here because getting it wrong is silent:

  - a limit belongs to an AGENT on a machine, not to a course and not to the
    machine: an allowance belongs to an account, so one provider running out
    says nothing about another, and marking the machine would take the fallback
    out along with the thing it is falling back from;
  - it expires by itself, and a turn that goes through on an agent clears that
    agent's. A limit cleared by hand outlives itself and quietly teaches worse
    for days;
  - and what a limit LOOKS like is configuration, because the board is not
    allowed to know which assistant is driving it.
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
from tutorboard.net import egress

paths.STATE_DIR = box
limits.LIMIT_RECORD = os.path.join(box, "limited.json")
paths.CONFIG = os.path.join(box, "config.json")           # no user config

# ---- reading a failed turn -------------------------------------------------
#
# The agent said why it failed; the only question is whether we listened. What a
# limit LOOKS like is configuration, for the same reason the egress probe is --
# the board is not allowed to know which assistant is driving it.

now = 1_700_000_000.0

check("the reset time a provider names is believed over any window we'd guess",
      abs(limits.reads_as_usage_limit(
          "Claude AI usage limit reached|%d" % int(now + 7200), now) - (now + 7200)) < 2)
check("a limit with no time on it gets the ordinary window",
      limits.reads_as_usage_limit("Claude AI usage limit reached", now)
      == now + limits.DEFAULT_LIMIT_WINDOW)
check("the five-hour form is a limit too",
      limits.reads_as_usage_limit("5-hour limit reached ∙ resets 3pm", now))
check("and so is the API's own word for it",
      limits.reads_as_usage_limit('{"type":"rate_limit_error"}', now))

check("DeepSeek's own word for an exhausted balance is a limit too -- none of "
      "the phrases written for one provider matched it",
      limits.reads_as_usage_limit("Insufficient Balance", now))
check("an ordinary broken turn is not a limit, and must not demote the machine",
      limits.reads_as_usage_limit("Error: ENOENT no such file", now) is None)
check("nor is a turn that said nothing at all",
      limits.reads_as_usage_limit("", now) is None)

# A reset time in the past, or absurdly far away, is a misread rather than news.
check("a reset time already gone falls back to the window",
      limits.reads_as_usage_limit("usage limit reached|100", now)
      == now + limits.DEFAULT_LIMIT_WINDOW)
check("and one a year out does not take the machine out for a year",
      limits.reads_as_usage_limit("usage limit reached|%d" % int(now + 400 * 86400), now)
      == now + limits.DEFAULT_LIMIT_WINDOW)

# ---- the record ------------------------------------------------------------

check("with nothing written, the machine has its allowance", limits.limited_until() == 0)
limits.mark_limited(time.time() + 900, agent="claude")
check("a limit reads back", limits.limited_until() > time.time())
check("and says which tutor ran out", limits.limit_record().get("agent") == "claude")

# ---- A LIMIT BELONGS TO AN AGENT --------------------------------------------
#
# It was recorded per MACHINE, and that was the right answer when there was one
# tutor. There are three, and an allowance belongs to an account: Claude running
# out says nothing at all about DeepSeek, and a machine-wide mark would take the
# fallback out along with the thing it is falling back from.
limits.clear_limited()
limits.mark_limited(time.time() + 900, agent="claude")
check("a limit is that agent's", limits.limited_until("claude") > time.time())
check("and is not another's", limits.limited_until("deepseek") == 0)

limits.mark_limited(time.time() + 1800, agent="deepseek")
check("a second one does not erase the first -- a whole-file write would send "
      "the daemon climbing home to an agent that is still limited",
      limits.limited_until("claude") > 0 and limits.limited_until("deepseek") > 0)
check("and the bare question is still answerable, for /health and `board limit`",
      limits.limited_until() > 0)
check("with the one that lasts longest, because that is when the machine is "
      "unconstrained", limits.limit_record().get("agent") == "deepseek")

limits.clear_limited("claude")
check("clearing one clears one",
      limits.limited_until("claude") == 0 and limits.limited_until("deepseek") > 0)
limits.clear_limited()
check("and clearing nothing in particular clears the lot",
      limits.limited_until() == 0)

# A RECORD FROM THE VERSION BEFORE MUST NOT CRASH AND MUST NOT DEMOTE EVERY
# AGENT. The second half is the one that is easy to get wrong.
with open(limits.LIMIT_RECORD, "w", encoding="utf-8") as fh:
    json.dump({"until": time.time() + 900, "agent": "claude",
               "node": "test-node", "at": time.time()}, fh)
check("an old single-tutor record reads as one entry under the name it carries",
      limits.limited_until("claude") > 0)
check("and does not demote the agent it never mentioned",
      limits.limited_until("deepseek") == 0)
with open(limits.LIMIT_RECORD, "w", encoding="utf-8") as fh:
    json.dump({"until": time.time() + 900, "node": "test-node"}, fh)
check("one that named nobody is still the machine's answer",
      limits.limited_until() > 0)
check("and still demotes nobody", limits.limited_until("claude") == 0)

limits.clear_limited()
limits.mark_limited(time.time() + 900, agent="claude")

limits.mark_limited(time.time() - 60, agent="claude")
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

limits.mark_limited(time.time() + 900, agent="claude")
limits.clear_limited()
check("and a turn going through clears it", limits.limited_until() == 0)

# ---- what the tutor does about it ------------------------------------------

src = open(os.path.join(ROOT, "bin", "tutor"), encoding="utf-8").read()

check("a limit is asked about before the network is blamed -- the turn itself "
      "answered that one, and a provider that could say so is a provider we "
      "plainly reached",
      src.index("reads_as_usage_limit")
      < src.index("if not egress.egress_ok():"))
check("the machine is marked, which is what /health then publishes",
      "limits.mark_limited(until, agent=agent_name)" in src)
check("the message whose turn was lost is carried, not dropped",
      "pending = out" in src)
check("the transcript is pushed before the turn is given up on, so the message "
      "it failed to answer is somewhere a later session can read it",
      "sync_transcript(root, log)" in src)
check("and then the next turn climbs down to whoever can take it, which is "
      "the whole reason to have three",
      "nxt, _ = choose_agent(load_config(), agent_name)" in src)
check("and where there is nobody to climb down to it says so and goes on "
      "failing where that is visible, which is what one tutor always did",
      "nothing else here can take it" in src)
check("a turn that goes through proves THAT agent's allowance, not the "
      "machine's", "limits.clear_limited(agent_name)" in src)
check("the handoff is still attempted, because it is the only continuity there "
      "is", "is a session the next one has to reconstruct" in src)

health = open(os.path.join(ROOT, "tutorboard", "server", "routes",
                           "machines.py"), encoding="utf-8").read()
check("a board publishes its machine's allowance, because only it can know",
      '"limited": limits.limited_until()' in health)

print("\n%d FAILURES" % len(errors) if errors
      else "\nthe lesson goes where there is an allowance to teach it")
sys.exit(1 if errors else 0)
