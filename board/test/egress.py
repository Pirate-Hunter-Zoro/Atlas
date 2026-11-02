#!/usr/bin/env python3
"""Whether a turn can get out of this machine, and what to do when it cannot.

An exit node routes all of this machine's outbound traffic somewhere else. Every
part of serving a lesson is untouched -- tailnet traffic does not go through it,
so the iPad reaches the board exactly as before -- and every part of *teaching*
one goes through it, because DeepSeek is on the ordinary internet. Commercial
VPN egress is precisely the address a service geo-blocks, rate-limits or
challenges, and when that happens the symptom is a tutor which listens, fails
every turn, and says so only in a log nobody opens.

Three rules, and this file holds them:

  - a failed turn is not assumed to be a network fault, it is asked about, and
    only after it has already failed -- probing before every turn would put a
    round trip to the internet in front of every card a student is waiting for;
  - the endpoint probed is DeepSeek's own, the host every turn opens, unless
    config.json's `egress_probe` names others;
  - a repair never turns the exit node off. Somebody routing everything through
    one is doing it deliberately, and dropping back to the bare connection to fix
    a tutoring session would expose the address they arranged not to expose.
"""

import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


sandbox = tempfile.mkdtemp(prefix="tutor-egress-")
os.environ["BOARD_STATE_DIR"] = sandbox
sys.path.insert(0, ROOT)
from tutorboard import paths
from tutorboard.net import egress, tailscale

# --- reading the tailscale picture ------------------------------------------
STATUS = {
    "Peer": {
        "a": {"HostName": "si-lju-wg-001", "TailscaleIPs": ["100.97.155.16"],
              "ExitNode": True, "ExitNodeOption": True, "Online": True},
        "b": {"HostName": "gb-lon-wg-001", "TailscaleIPs": ["100.1.1.1"],
              "ExitNodeOption": True, "Online": True},
        "c": {"HostName": "jp-tyo-wg-001", "TailscaleIPs": ["100.2.2.2"],
              "ExitNodeOption": True, "Online": False},
        "d": {"HostName": "somebodys-laptop", "TailscaleIPs": ["100.3.3.3"],
              "Online": True},
        "e": {"HostName": "us-lax-wg-001", "TailscaleIPs": ["100.4.4.4"],
              "ExitNodeOption": True, "Online": True},
    }
}

node = egress.exit_node(STATUS)
check("the exit node in use is found, by name and address",
      node == {"name": "si-lju-wg-001", "ip": "100.97.155.16"})
check("no exit node reads as none rather than as an error",
      egress.exit_node({"Peer": {"d": STATUS["Peer"]["d"]}}) is None)

opts = egress.exit_node_options(STATUS)
names = [o["name"] for o in opts]
check("every peer offering to be an exit node is an option", len(opts) == 4)
check("and a peer that is not offering is not one", "somebodys-laptop" not in names)
check("each option carries an address, because a bare name is refused by tailscale",
      all(o["ip"] for o in opts))

# --- the probe --------------------------------------------------------------
# ANY answer proves the path. A 401 to an unauthenticated POST is the healthiest
# possible result: the packets arrived, were understood, and were turned away for
# the one reason that says nothing about the network.
import urllib.error  # noqa: E402

calls = []


def fake_urlopen(req, timeout=None):
    calls.append(req.full_url)
    raise urllib.error.HTTPError(req.full_url, 401, "Unauthorized", {}, None)


import urllib.request  # noqa: E402
real_urlopen = urllib.request.urlopen
urllib.request.urlopen = fake_urlopen
check("a 401 means reachable -- we asked whether packets arrive, not whether we may in",
      egress.egress_ok() is True)


def dead(req, timeout=None):
    raise urllib.error.URLError("nope")


urllib.request.urlopen = dead
check("a connection failure means not reachable", egress.egress_ok() is False)
urllib.request.urlopen = real_urlopen

check("the default probe is DeepSeek's own endpoint",
      egress.DEFAULT_EGRESS_PROBE == ("https://api.deepseek.com/chat/completions",))
lib = open(os.path.join(ROOT, "tutorboard", "net", "egress.py"), encoding="utf-8").read()
check("and no other vendor's host is named",
      "anthropic" not in lib and "chatgpt" not in lib)

cfg_tmp = tempfile.mkdtemp(prefix="tutor-egress-cfg-")
was_cfg = paths.CONFIG
try:
    paths.CONFIG = os.path.join(cfg_tmp, "config.json")
    egress.paths.CONFIG = paths.CONFIG

    def write_cfg(doc):
        with open(paths.CONFIG, "w", encoding="utf-8") as fh:
            json.dump(doc, fh)

    write_cfg({"provider": "claude"})
    check("a leftover provider key changes nothing: the probe is DeepSeek's",
          egress.egress_probe_urls() == egress.DEFAULT_EGRESS_PROBE)
    write_cfg({"egress_probe": "https://example.invalid/x"})
    check("and a list written in the config beats the default",
          egress.egress_probe_urls() == ("https://example.invalid/x",))
finally:
    paths.CONFIG = was_cfg
    egress.paths.CONFIG = was_cfg
    shutil.rmtree(cfg_tmp, ignore_errors=True)

# --- rotation ---------------------------------------------------------------
moved = []
tailscale._ts_status = lambda: STATUS
egress.set_exit_node = lambda ip: (moved.append(ip), True)[1]

# Nothing works: the one the person chose has to be put back.
egress.egress_ok = lambda timeout=12: False
ok, detail = egress.rotate_exit_node(tries=2, log=None, settle=0)
check("when nothing works the rotation gives up rather than wandering", not ok)
check("and puts back the exit node the person actually chose",
      moved and moved[-1] == "100.97.155.16")
check("it never turns the exit node off, which would expose the real address",
      None not in moved and "" not in moved)
check("an offline exit node is never tried", "100.2.2.2" not in moved)

# The second one works.
moved[:] = []
tried = {"n": 0}


def works_on_second(timeout=12):
    tried["n"] += 1
    return tried["n"] >= 2


egress.egress_ok = works_on_second
ok, detail = egress.rotate_exit_node(tries=4, log=None, settle=0)
check("a working exit node is found and kept", ok)
check("and it is not the broken one it started on", moved[-1] != "100.97.155.16")
check("and it is remembered, since the only evidence one works is that it did",
      moved[-1] in json.load(open(egress.EGRESS_KNOWN_GOOD)))

# Known-good goes first next time.
moved[:] = []
tried["n"] = 0
egress.egress_ok = lambda timeout=12: True
ok, detail = egress.rotate_exit_node(tries=4, log=None, settle=0)
check("an exit node known to have worked is tried before the rest",
      ok and moved[0] in json.load(open(egress.EGRESS_KNOWN_GOOD)))

# With no exit node at all there is nothing here to repair, and the fault is
# real -- it must not be reported as fixed.
tailscale._ts_status = lambda: {"Peer": {}}
ok, detail = egress.rotate_exit_node(tries=2, log=None, settle=0)
check("with no exit node in use, a broken egress is not claimed to be repaired",
      not ok and "no exit node" in detail)

# --- DeepSeek dark from here --------------------------------------------------
# A filter that drops DeepSeek's hostname is a fact the board says, with the
# host and an expiry, until a turn goes through. Nothing waits on it: the next
# message tries again.
import time as _time                                           # noqa: E402

egress.mark_unreachable("api.deepseek.com", _time.time() + 3600)
check("DeepSeek not answering is written down, with the host and an expiry",
      (egress.stood_down() or {}).get("host") == "api.deepseek.com")
check("one record, not one per assistant",
      set(json.load(open(egress.UNREACHABLE_RECORD))) ==
      {"node", "at", "host", "strikes", "until"})
egress.clear_unreachable()
check("a turn that goes through clears it: the expiry is a guess, a card is a "
      "measurement", egress.stood_down() is None)
egress.mark_unreachable("api.deepseek.com", _time.time() - 1)
check("and it expires on its own, so a lifted filter is picked up the same evening",
      egress.stood_down() is None)
egress.clear_unreachable()

# --- and the second finding is believed for longer ---------------------------
first = egress.mark_unreachable("api.deepseek.com")
one = egress.stood_down()["until"] - _time.time()
egress.mark_unreachable("api.deepseek.com")
two = egress.stood_down()["until"] - _time.time()
check("found dark again, it is believed for longer, so a permanent block is "
      "said for as long as it lasts",
      two > one * 1.9 and two <= egress.UNREACHABLE_MAX)
check("and the doubling has a ceiling, so a filter lifted overnight is still "
      "picked up the next day", egress.UNREACHABLE_MAX <= 24 * 3600)
egress.clear_unreachable()
egress.mark_unreachable("api.deepseek.com")
back = egress.stood_down()["until"] - _time.time()
check("a turn that goes through resets the count as well as the mark",
      abs(back - one) < 5)
egress.clear_unreachable()

check("a turn that keeps failing is not stood down: `ready`'s reasons are a "
      "missing binary, a missing key and a usage limit",
      not hasattr(egress, "mark_failing"))

# --- where it is used -------------------------------------------------------
# The loop first, then the recipe, what a turn said, and the runner.
tutor_src = "".join(
    open(os.path.join(ROOT, *p), encoding="utf-8").read()
    for p in (("tutorboard", "runner", "loop.py"), ("tutorboard", "agents", "recipes.py"),
              ("tutorboard", "agents", "usage.py"),
              ("tutorboard", "runner", "service.py")))
check("the tutor asks whether the MACHINE can get out only after a turn has "
      "actually failed -- a round trip in front of every card is a round trip "
      "the student waits for",
      "if err:" in tutor_src and
      tutor_src.index("if err:") < tutor_src.index("if not egress.egress_ok():"))
check("and DeepSeek is not probed before a turn: `ready` reads files only",
      "probe_before_turn" not in tutor_src and "PROBE_TTL" not in tutor_src)
check("and rotates when it is the network rather than the tutor",
      "egress.rotate_exit_node(" in tutor_src)
check("and re-answers the message whose turn was lost, rather than waiting",
      "pending = owe(ctx, out)" in tutor_src
      and "owed = daemon.owed_message(repo.live)" in tutor_src)
check("and says plainly when it could not repair it",
      "turns will keep " in tutor_src)

check("a failed turn's probe writes no stand-down, and a turn that goes "
      "through clears one", "egress.mark_unreachable(" not in tutor_src
      and "egress.clear_unreachable()" in tutor_src)
check("and DeepSeek's own words are what the board reports, not `exit 1`",
      "said = opencode_error(text)" in tutor_src)

board_src = open(os.path.join(ROOT, "bin", "board"), encoding="utf-8").read()
check("there is a command to ask, and to repair, by hand",
      "def cmd_egress(" in board_src and '"egress": cmd_egress' in board_src)
check("and doctor says so, since an exit node is invisible until it is not",
      "every request a tutor makes leaves from there" in board_src)

from tutorboard.runner import daemon  # noqa: E402
from tutorboard.agents import usage  # noqa: E402

# --- the message a turn was taking, when the daemon does not come back ------
#
# `board wait` marks the inbox line read before the turn runs, so between the
# message being taken and something answering it the daemon's own record is the
# only copy of it anywhere. A turn is minutes long and that is exactly the
# window the 23 September sitting was killed in.
owed_live = os.path.join(sandbox, "live-owed")
os.makedirs(owed_live, exist_ok=True)
check("a record with nothing owed on it owes nothing, and a missing one does "
      "not raise", daemon.owed_message(owed_live) is None
      and daemon.owed_message(os.path.join(sandbox, "nowhere")) is None)
daemon.agent_state(owed_live, owed="[inbox] the student's working, handed in")
check("a message owed outlives the process that owed it, because it is on the "
      "filer rather than in a local",
      daemon.owed_message(owed_live) == "[inbox] the student's working, handed in")
daemon.agent_state(owed_live, owed=None)
check("and answering it settles the debt, so the next daemon does not teach "
      "the same message twice", daemon.owed_message(owed_live) is None)
check("and the debt is taken on when the message is TAKEN rather than when a "
      "turn fails, since a daemon signalled mid-turn never reaches the failure "
      "path at all",
      tutor_src.index("    owe(ctx, out)\n    ctx.turns += 1") > 0)
check("and every path out of a turn settles it once, off what the turn left "
      "owed, rather than every path having to remember to",
      "    owe(ctx, pending)\n" in tutor_src)

# --- the wrap-up reads the recipe afresh, and is skipped when it cannot run --
check("the wrap-up reads the recipe and readiness afresh",
      "ctx.cfg, ctx.spec = recipes.load_config(), recipes.spec()\n"
      "    why_not = recipes.ready()" in tutor_src.split("def wrap_up(")[1])
check("and it is skipped rather than spent when it cannot run here",
      "no wrap-up was attempted" in tutor_src)

# --- what the board is given to say it with ---------------------------------
state_src = open(os.path.join(ROOT, "tutorboard", "lesson", "state.py"),
                 encoding="utf-8").read()
check("the lesson payload carries the stand-down itself -- the host and the "
      "hour the board stops saying so -- because the log is a place an iPad "
      "cannot look", "st[\"stood_down\"] = _stood_down()" in state_src)
board_js = open(os.path.join(ROOT, "web", "board.js"), encoding="utf-8").read()
check("and it lands somewhere a finger can reach, since a title is a hover "
      "tooltip on a device with no hover",
      "if (st && st.stood_down)" in board_js
      and "return failed || aside;" in board_js)
check("in words rather than as a hostname the reader did not choose",
      "DeepSeek does not answer from this machine" in board_js)
check("and the board no longer paints a swap: there is nobody to swap to",
      "agent_why" not in board_js)

# --- and the reason a machine-wide outage gives is the one the board has a
#     word for, rather than the exit code computed over the top of it ---------
check("`no egress` survives to the record instead of being recomputed as "
      "`exit 1`, which is the one case `failWord` has a sentence for",
      "why = \"no egress\" if dark_machine else usage.failure_reason(said, err)" in tutor_src)

# --- a failing turn whose last event is long is still read whole -----------
long_line = json.dumps({"type": "error", "sessionID": "s",
                        "error": {"data": {"message": "API Error: " + "x" * 40000}}})
logfile = os.path.join(sandbox, "agent.log")
with open(logfile, "w", encoding="utf-8") as fh:
    fh.write("chatter\n" * 200 + long_line + "\n")
said = usage.turn_output(logfile, 0)
check("an event longer than the 20 KB tail is read WHOLE, because a JSON line "
      "cut at the front is no longer read",
      usage.opencode_error(said) == json.loads(long_line)["error"]["data"]["message"])
check("and the tail is still a tail -- the whole log is not read back into "
      "memory to find one line", len(said) < len(long_line) + 40000)

shutil.rmtree(sandbox, ignore_errors=True)
print()
print("%d FAILURES" % len(fails) if fails else "a turn can get out, or says why not")
sys.exit(1 if fails else 0)
