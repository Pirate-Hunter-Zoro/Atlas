#!/usr/bin/env python3
"""Whether a turn can get out of this machine, and what to do when it cannot.

An exit node routes all of this machine's outbound traffic somewhere else. Every
part of serving a lesson is untouched -- tailnet traffic does not go through it,
so the iPad reaches the board exactly as before -- and every part of *teaching*
one goes through it, because the tutor's provider is on the ordinary internet.
Commercial VPN egress is precisely the address a provider geo-blocks, rate-limits
or challenges, and when that happens the symptom is a tutor which listens, fails
every turn, and says so only in a log nobody opens.

Three rules, and this file holds them:

  - a failed turn is not assumed to be a network fault, it is asked about, and
    only after it has already failed -- probing before every turn would put a
    round trip to the internet in front of every card a student is waiting for;
  - which endpoints matter is CONFIGURATION. The board is not allowed to know
    which assistant is driving it, so this is a list of URLs with a default, the
    same way a model is a command recipe and never a field;
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

check("the endpoints are configuration with a default, never a fact in the code",
      egress.DEFAULT_EGRESS_PROBE and callable(egress.egress_probe_urls))
lib = open(os.path.join(ROOT, "tutorboard", "net", "egress.py"), encoding="utf-8").read()
check("and the default is the only place a provider is named",
      lib.count("api.anthropic.com") == 1)

# The probe has to ask after the host this machine's tutor will actually open a
# connection to. A probe aimed anywhere else answers a question about somebody
# else's server: it proves nothing when the tutor's provider is the one being
# challenged, and reports a broken machine that can teach perfectly well when it
# is not.
cfg_tmp = tempfile.mkdtemp(prefix="tutor-egress-cfg-")
was_cfg = paths.CONFIG
try:
    paths.CONFIG = os.path.join(cfg_tmp, "config.json")
    egress.paths.CONFIG = paths.CONFIG

    def write_cfg(doc):
        with open(paths.CONFIG, "w", encoding="utf-8") as fh:
            json.dump(doc, fh)

    write_cfg({"provider": "claude"})
    check("the default probes the default agent's provider",
          egress.egress_probe_urls() == egress.DEFAULT_EGRESS_PROBE)

    # The rule: the board is not allowed to know which assistant is driving it,
    # and a list in the config is how that stays true.
    write_cfg({"egress_probe": "https://example.invalid/x"})
    check("and a list written in the config beats the default",
          egress.egress_probe_urls() == ("https://example.invalid/x",))

    # EACH CONFIGURED PROVIDER'S ENDPOINT IS ON THE LIST, after the machine's
    # own and once each: on the Mac every provider is an ordinary choice, so a
    # filter on one hostname is not a machine with no way out.
    write_cfg({"provider": "claude"})
    got = egress.egress_probe_urls(also=["https://api.deepseek.test/a",
                                         egress.DEFAULT_EGRESS_PROBE[0],
                                         "https://api.deepseek.test/a"])
    check("each configured provider's endpoint joins the list, once, after "
          "the default's",
          got == egress.DEFAULT_EGRESS_PROBE + ("https://api.deepseek.test/a",))
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

# --- one provider dark, the rest of the internet fine -----------------------
# The failure this half is about: a filter drops ONE provider's hostname and
# leaves every other host answering. The machine-wide probe therefore reports a
# healthy network over a recipe whose every turn dies in the TLS handshake, and
# the board says `exit 1` about a fault no tutor can fix.
import time as _time                                           # noqa: E402

egress.mark_unreachable("deepseek", "api.deepseek.com", _time.time() + 3600)
check("a provider that does not answer is written down, with the host and an expiry",
      (egress.unreachable("deepseek") or {}).get("host") == "api.deepseek.com")
check("and it belongs to the agent, not the machine -- one dark provider says "
      "nothing about the next",
      egress.unreachable("claude") is None)

egress.clear_unreachable("deepseek")
check("a turn that goes through clears it: the expiry is a guess, a card is a "
      "measurement",
      egress.unreachable("deepseek") is None)

egress.mark_unreachable("deepseek", "api.deepseek.com", _time.time() - 1)
check("and it expires on its own, so a lifted filter is picked up the same evening",
      egress.unreachable("deepseek") is None)
egress.clear_unreachable("deepseek")

# --- and the second finding is cheaper than the first -----------------------
# A flat hour is right for a filter that lifts by itself and wrong for a
# firewall rule, which outlives every expiry: the window then costs one dead
# turn an hour for ever, each one a student waiting three minutes for nothing.
first = egress.mark_unreachable("deepseek", "api.deepseek.com")
one = egress.unreachable("deepseek")["until"] - _time.time()
egress.mark_unreachable("deepseek", "api.deepseek.com")
two = egress.unreachable("deepseek")["until"] - _time.time()
check("a provider found dark again is stood down for longer, so a permanent "
      "block is not rediscovered hourly for ever",
      two > one * 1.9 and two <= egress.UNREACHABLE_MAX)
check("and the doubling has a ceiling, so a filter lifted overnight is still "
      "picked up the next day", egress.UNREACHABLE_MAX <= 24 * 3600)
egress.clear_unreachable("deepseek")
egress.mark_unreachable("deepseek", "api.deepseek.com")
back = egress.unreachable("deepseek")["until"] - _time.time()
check("a turn that goes through resets the count as well as the mark: a "
      "provider that came back starts its next bad evening at an hour",
      abs(back - one) < 5)
egress.clear_unreachable("deepseek")

# --- no strike stand-down -----------------------------------------------------
check("a recipe that keeps failing is not stood down: the resolver's reasons are "
      "a missing binary, a missing key and a usage limit",
      not hasattr(egress, "mark_failing"))

check("asking about one provider is a different question from asking about the "
      "machine, and takes its own urls",
      "def egress_ok(timeout=12, urls=None, also=()):" in lib)

# --- where it is used -------------------------------------------------------
# The daemon's loop first, then the recipes, what a turn said, and the CLI.
tutor_src = "".join(
    open(os.path.join(ROOT, *p), encoding="utf-8").read()
    for p in (("tutorboard", "runner", "loop.py"), ("tutorboard", "agents", "recipes.py"),
              ("tutorboard", "agents", "usage.py"), ("bin", "tutor"),
              ("tutorboard", "runner", "service.py")))
check("the tutor asks whether the MACHINE can get out only after a turn has "
      "actually failed -- a round trip in front of every card is a round trip "
      "the student waits for",
      "if err:" in tutor_src and
      tutor_src.index("if err:") < tutor_src.index("if not egress.egress_ok(also="))
check("and no provider is probed before a turn: the resolver reads files only",
      "probe_before_turn" not in tutor_src and "PROBE_TTL" not in tutor_src)
check("and rotates when it is the network rather than the tutor",
      "egress.rotate_exit_node(" in tutor_src)
check("and re-answers the message whose turn was lost, rather than waiting",
      "pending = owe(ctx, out)" in tutor_src
      and "owed = daemon.owed_message(repo.live)" in tutor_src)
check("and says plainly when it could not repair it",
      "turns will keep " in tutor_src)

check("a dark host does not stand a turn's recipe down: nothing the resolver "
      "reads is written from a failed turn's probe",
      "egress.mark_unreachable(" not in tutor_src
      and "egress.stood_down(" not in tutor_src)
check("and the agent's own verdict is what the board reports, not `exit 1`",
      "def result_object_error(" in tutor_src and
      "said = result_object_error(text)" in tutor_src)

board_src = open(os.path.join(ROOT, "bin", "board"), encoding="utf-8").read()
check("there is a command to ask, and to repair, by hand",
      "def cmd_egress(" in board_src and '"egress": cmd_egress' in board_src)
check("and doctor says so, since an exit node is invisible until it is not",
      "every request a tutor makes leaves from there" in board_src)

# --- the machine-wide probe, run rather than grepped for ----------------------

from tutorboard.runner import daemon  # noqa: E402
from tutorboard.agents import recipes  # noqa: E402
from tutorboard.runner import loop as runloop  # noqa: E402
from tutorboard.agents import usage  # noqa: E402

# Both run under this interpreter, which `missing_command` always counts as
# installed: nothing below depends on which assistants this machine has.
CFG = {"agents": {
    "deepseek": {"cmd": [sys.executable], "headless": [sys.executable],
                 "egress_probe": ["https://api.deepseek.test/v1/chat/completions"]},
    "claude": {"cmd": [sys.executable], "headless": [sys.executable]},
}}

asked = []


def answering(what):
    """`egress_ok` that says yes to everything except the named provider."""
    def stub(timeout=12, urls=None, also=()):
        asked.append(tuple(urls or ()))
        return not (urls and any(what in u for u in urls))
    return stub


# THE MACHINE-WIDE PROBE ASKS AFTER EVERY CONFIGURED PROVIDER, and only those:
# a recipe whose command is here and whose key is in `keys.env`.
from tutorboard import keys as _keys                            # noqa: E402
was_unkeyed, was_missing = _keys.unkeyed, recipes.missing_command
_keys.unkeyed = lambda spec: None
recipes.missing_command = lambda cmd: None
check("the providers this machine can run add their own endpoints",
      recipes.provider_probe_urls(CFG)
      == ["https://api.deepseek.test/v1/chat/completions"])
check("Codex names its own host, so a filter on it is asked after",
      recipes.agent_probe_urls(recipes.DEFAULT_CONFIG["agents"]["codex"])
      == ["https://chatgpt.com/backend-api/codex/responses"])
_keys.unkeyed = lambda spec: "A_KEY"
check("and one whose key is not here adds none",
      recipes.provider_probe_urls(CFG) == [])
_keys.unkeyed = was_unkeyed
recipes.missing_command = was_missing

# --- the fallback says so on every turn it takes -----------------------------
# `agent_why` is rewritten every turn, so the sentence a student is owed lasts
# exactly as long as the provider cannot take the turn.
from tutorboard import limits as _limits                       # noqa: E402
_limits.LIMIT_RECORD = os.path.join(sandbox, "limited.json")
FB = dict(CFG, provider="deepseek", fallback="claude")
was_load = recipes.load_config
recipes.load_config = lambda: FB
_limits.mark_limited(__import__("time").time() + 900, agent="deepseek")
_, took, _, why = runloop.for_this_turn(FB, "claude", "")
check("a turn the fallback takes says so, naming the provider and why",
      took == "claude" and why and "deepseek" in why and "allowance" in why)
_, took, _, why = runloop.for_this_turn(FB, "claude", "")
check("and says it again on the next turn, not only on the one that moved",
      took == "claude" and why and "deepseek" in why)
_limits.clear_limited()
_, took, _, why = runloop.for_this_turn(FB, "claude", "")
check("and stops saying it when the provider is back",
      took == "deepseek" and why is None)
recipes.load_config = was_load
check("and the swap is on the record the board reads, rather than only in the "
      "log", "agent_why=moved or None," in tutor_src)

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

# --- and the last thing a daemon writes does not land on its successor ------
own_live = os.path.join(sandbox, "live-own")
os.makedirs(own_live, exist_ok=True)
check("a record nobody has claimed is this process's to write",
      daemon.record_is_ours(own_live))
daemon.agent_state(own_live, pid=os.getpid())
check("and so is one naming this process", daemon.record_is_ours(own_live))
daemon.agent_state(own_live, pid=os.getpid() + 1)
check("but a record naming somebody else is not, which is what stops an "
      "exiting daemon stamping `stopped` on the successor that replaced it -- "
      "`supervise.tutor_verdict` reads that as a person saying no and never "
      "revives it", not daemon.record_is_ours(own_live))

# --- the wrap-up runs as whoever can write it -------------------------------
#
# The one turn that must not be skipped was being spent on the one recipe that
# could not take it: the loop's `spec` is rebound only at the top of a turn, and
# a session whose last turn stood its provider down never takes another.
check("the handoff re-asks who writes it instead of inheriting the recipe the "
      "last turn failed on",
      "took, why_took = recipes.resolve(ctx.cfg)" in tutor_src
      and tutor_src.index("the handoff goes to")
      < tutor_src.index("wrap = ctx.spec.get(\"handoff\")"))
check("and it rebinds the recipe, not just the name -- the environment is what "
      "points the binary at its provider",
      "ctx.agent_name, ctx.spec = took, ctx.cfg[\"agents\"].get(took) or {}"
      in tutor_src)
check("and it is skipped rather than spent when nothing here can write one",
      "    if not took:\n" in tutor_src.split("def wrap_up(")[1]
      and "no handoff was attempted" in tutor_src)

# --- what the board is given to say it with ---------------------------------
check("the chooser is told which providers cannot take a turn right now, so a "
      "limited one is not drawn as a live button",
      '"unavailable": unavailable(cfg, n),' in tutor_src)
state_src = open(os.path.join(ROOT, "tutorboard", "lesson", "state.py"),
                 encoding="utf-8").read()
check("and the lesson payload carries the stand-down itself -- the host and "
      "the hour it will be asked again -- because the log and `board agents` "
      "are both places an iPad cannot look",
      "st[\"stood_down\"] = _stood_down(st.get(\"agent\"))" in state_src)
board_js = open(os.path.join(ROOT, "web", "board.js"), encoding="utf-8").read()
check("the climb-down sentence is no longer stamped on by the chip's own text "
      "two lines later, which is why it reached nobody",
      "if (!els.agent.title) els.agent.title = els.agent.textContent;" in board_js)
check("and it lands somewhere a finger can reach, since a title is a hover "
      "tooltip on a device with no hover",
      "if (st && st.agent_why)" in board_js
      and "return failed || aside;" in board_js)
check("and a dark provider is put in words rather than as a hostname the "
      "reader did not choose and cannot act on",
      "its provider does not answer from this machine" in board_js)
who_js = open(os.path.join(ROOT, "web", "who.js"), encoding="utf-8").read()
check("the chooser dims it and says why on the tap",
      "a.unavailable" in who_js and "return a.unavailable || \"\";" in who_js)

# --- and the reason a machine-wide outage gives is the one the board has a
#     word for, rather than the exit code computed over the top of it ---------
check("`no egress` survives to the record instead of being recomputed as "
      "`exit 1`, which is the one case `failWord` has a sentence for",
      "why = \"no egress\" if dark_machine else usage.failure_reason(said, err)" in tutor_src)

# --- a failing turn whose result object is long is still a failing turn ------
long_line = json.dumps({"type": "result", "is_error": True,
                        "duration_ms": 179384, "result": "API Error: " + "x" * 40000})
logfile = os.path.join(sandbox, "agent.log")
with open(logfile, "w", encoding="utf-8") as fh:
    fh.write("chatter\n" * 200 + long_line + "\n")
said = usage.turn_output(logfile, 0)
check("a result object longer than the 20 KB tail is read WHOLE, because "
      "`is_error` is written before `result` and a front cut loses the verdict "
      "before it loses the sentence",
      usage.result_object_error(said) == json.loads(long_line)["result"])
check("and the tail is still a tail -- the whole log is not read back into "
      "memory to find one line", len(said) < len(long_line) + 40000)

shutil.rmtree(sandbox, ignore_errors=True)
print()
print("%d FAILURES" % len(fails) if fails else "a turn can get out, or says why not")
sys.exit(1 if fails else 0)
