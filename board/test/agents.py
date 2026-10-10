#!/usr/bin/env python3
"""Which assistant takes a turn: one provider setting.

The machine's config names `provider` (claude by default), one `fallback`
(codex by default) and `vision_agent`. The provider takes every turn; the
fallback takes one the provider cannot (missing binary, missing key, usage
limit); nothing else chooses. An in-fence recipe never takes a turn here.

Also guards the shared-filesystem rule. `live/agent.json` is visible from every
node, so a record left by a node whose allocation has ended will otherwise look
exactly like a live assistant, and the board will sit waiting for a process that
died hours ago.
"""

import importlib.machinery
import importlib.util
import json
import shutil
import time
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

sys.path.insert(0, ROOT)
# A state directory of our own: the fallback section below writes limit records,
# and writing the real one would take this machine out of service.
os.environ.setdefault("BOARD_STATE_DIR", tempfile.mkdtemp(prefix="agents-state-"))
os.environ.setdefault("BOARD_NO_TAILNET", "1")
from tutorboard import limits                                 # noqa: E402

from tutorboard.runner import daemon  # noqa: E402
from tutorboard import gitops  # noqa: E402
from tutorboard.agents import recipes  # noqa: E402
from tutorboard.runner import turn as runturn  # noqa: E402
from tutorboard.agents import usage  # noqa: E402

fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


CFG = {
    "provider": "opencode",
    "agents": {"claude": {"cmd": ["claude"]},
               "opencode": {"cmd": ["opencode"]},
               "codex": {"cmd": ["codex"]}},
}

host = recipes.this_host()

# --- the one provider setting ------------------------------------------------
SH = {"cmd": ["sh"], "headless_first": ["sh", "-c", "{prompt}"]}
limits.LIMIT_RECORD = os.path.join(os.environ["BOARD_STATE_DIR"], "limited.json")
limits.clear_limited()
ONE = {"provider": "one", "fallback": "two", "agents": {
    "one": dict(SH), "two": dict(SH), "three": dict(SH),
    "fenced": dict(SH, private="it reads phi"),
    "ghost": {"cmd": ["a-command-no-machine-has"],
              "headless_first": ["a-command-no-machine-has"]},
    "unkeyed": dict(SH, needs_key="A-KEY-NO-MACHINE-HAS")}}

check("the provider takes the turn when nothing is wrong",
      recipes.resolve(ONE) == ("one", None))
check("an unset provider is claude and an unset fallback is none",
      recipes.provider({}) == "claude" and recipes.fallback({}) is None)
check("the built-in setting names a provider and claude's eyes, and no "
      "fallback, so every other recipe backs it up",
      recipes.DEFAULT_CONFIG["provider"] == "claude"
      and "fallback" not in recipes.DEFAULT_CONFIG
      and recipes.DEFAULT_CONFIG["vision_agent"] == "claude"
      and recipes.fallbacks(recipes.DEFAULT_CONFIG)
      == [n for n in recipes.DEFAULT_CONFIG["agents"] if n != "claude"])
check("nothing else chooses: no default_agent, only_agent, per-session or "
      "per-workspace key is in the table",
      not any(k in recipes.DEFAULT_CONFIG for k in
              ("default_agent", "only_agent", "session_turns", "hosts")))

limits.mark_limited(time.time() + 900, agent="one")
name, why = recipes.resolve(ONE)
check("a limited provider hands the turn to the fallback",
      name == "two")
check("and the sentence names both and why, because the board paints it",
      "'one'" in (why or "") and "'two'" in (why or "")
      and "allowance" in (why or ""))
limits.mark_limited(time.time() + 900, agent="two")
name, why = recipes.resolve(ONE)
check("with the fallback limited too, nobody takes it, and the sentence says "
      "why of both", name is None and "'one'" in why and "'two'" in why)
limits.clear_limited()
check("and when the allowance comes back the provider is home again, because "
      "the question is asked every turn",
      recipes.resolve(ONE) == ("one", None))

check("a provider whose binary is missing falls back",
      recipes.resolve(dict(ONE, provider="ghost"))[0] == "two"
      and "not on the path" in recipes.resolve(dict(ONE, provider="ghost"))[1])
check("so does one whose key is missing",
      recipes.resolve(dict(ONE, provider="unkeyed"))[0] == "two"
      and "A-KEY-NO-MACHINE-HAS" in recipes.resolve(dict(ONE, provider="unkeyed"))[1])
check("an unknown provider falls back rather than resolving to a wrong one",
      recipes.resolve(dict(ONE, provider="nonesuch"))[0] == "two")
check("a named fallback is the only one, and null names none",
      recipes.resolve(dict(ONE, provider="ghost", fallback="unkeyed"))[0] is None
      and recipes.resolve(dict(ONE, provider="ghost", fallback=None))[0] is None)
check("a list of fallbacks is walked in order, past the ones that cannot",
      recipes.resolve(dict(ONE, provider="ghost",
                           fallback=["unkeyed", "three", "two"]))[0] == "three")
_all = dict((k, v) for k, v in ONE.items() if k != "fallback")
check("with no fallback set, every other recipe is walked in the table's "
      "order, so any one provider can die",
      recipes.chain(_all) == ["one", "two", "three", "fenced", "ghost",
                              "unkeyed"]
      and recipes.resolve(dict(_all, provider="ghost"))[0] == "one")
limits.mark_limited(time.time() + 900, agent="one")
limits.mark_limited(time.time() + 900, agent="two")
check("and past every one that is out, to the next that can answer",
      recipes.resolve(_all)[0] == "three"
      and "'one'" in recipes.resolve(_all)[1])
limits.clear_limited()
check("a fallback that is the provider is no fallback",
      recipes.resolve(dict(ONE, provider="ghost", fallback="ghost"))[0] is None)

# ONLY AN IN-FENCE MODEL READS PHI, and it never takes a turn here: an explicit
# refusal, whichever slot the config puts it in.
check("an in-fence provider is refused, in words, and the fallback takes it",
      "in-fence" in (recipes.in_fence(ONE, "fenced") or "")
      and recipes.resolve(dict(ONE, provider="fenced"))[0] == "two"
      and "phi" in recipes.resolve(dict(ONE, provider="fenced"))[1])
check("and an in-fence fallback is never fallen into",
      recipes.resolve(dict(ONE, provider="ghost", fallback="fenced"))[0] is None
      and recipes.resolve(dict(_all, provider="ghost",
                               fallback=["fenced", "two"]))[0] == "two")
check("a hosted recipe is not in the fence", recipes.in_fence(ONE, "one") is None)

import inspect                                                 # noqa: E402
_resolver = sum(len(inspect.getsourcelines(f)[0]) for f in (
    recipes.provider, recipes.fallbacks, recipes.fallback, recipes.chain,
    recipes.in_fence, recipes.unavailable, recipes.resolve))
check("the resolver is under 80 lines (%d)" % _resolver, _resolver < 80)
check("and the old choosers are gone",
      not any(hasattr(recipes, n) for n in (
          "resolve_agent", "choose_agent", "agent_unavailable", "only_agent",
          "only_bars", "config_shadows", "probe_before_turn")))
from tutorboard.course import config as _course_config        # noqa: E402
from tutorboard.net import egress as _egress                  # noqa: E402
check("a workspace's `agent` key and the sitting's are read by nothing",
      not hasattr(_course_config, "workspace_agent")
      and not hasattr(_course_config, "sitting_agent")
      and not hasattr(recipes, "read_course"))
check("and the strike stand-down is gone", not hasattr(_egress, "mark_failing"))

# The machine's own file: `provider` alone chooses, a `default_agent` is read
# by nothing, and nothing is written when the file is missing.
_cfg_box = tempfile.mkdtemp(prefix="tutor-cfg-")
_was_config = recipes.CONFIG
recipes.CONFIG = os.path.join(_cfg_box, "config.json")
check("a missing config is the defaults, and nothing is written",
      recipes.load_config()["provider"] == "claude"
      and not os.path.exists(recipes.CONFIG))
with open(recipes.CONFIG, "w", encoding="utf-8") as fh:
    json.dump({"default_agent": "deepseek", "only_agent": "deepseek"}, fh)
_loaded = recipes.load_config()
check("a default_agent or only_agent chooses nothing: the provider is the "
      "default's", _loaded["provider"] == "claude"
      and "only_agent" not in _loaded and "default_agent" not in _loaded)
with open(recipes.CONFIG, "w", encoding="utf-8") as fh:
    json.dump({"provider": "codex", "default_agent": "deepseek",
               "agents": {"claude": {"label": "Mine"}}}, fh)
_loaded = recipes.load_config()
check("`provider` is read beside a leftover default_agent",
      _loaded["provider"] == "codex")
check("and a recipe field merges into the built-in one rather than replacing it",
      _loaded["agents"]["claude"]["label"] == "Mine"
      and _loaded["agents"]["claude"]["headless_first"][0] == "claude")
recipes.CONFIG = _was_config
shutil.rmtree(_cfg_box, ignore_errors=True)

# --- the default, and where its permissions are NOT written ------------------
# Claude Code is the default tutor. Headless there is nobody to approve anything,
# and a refused tool is not an error -- the agent apologises into a log nobody
# opens and exits 0, which reaches the board as a tutor who answered with
# silence. That is already solved, and solved in one place: `board start` writes
# the course its own `.claude/settings.local.json`. The recipe must not repeat
# it. One policy in two files is one policy that drifts the first time either
# moves, and the committed file is the half a course's owner can actually see.
D = recipes.DEFAULT_CONFIG
claude = D["agents"]["claude"]

recipe = " ".join(claude["headless_first"])
check("the turn recipe does not carry a second copy of the permissions",
      "acceptEdits" not in recipe and "allowedTools" not in recipe)
check("no built-in recipe carries a resume form: every turn is fresh",
      not any("headless" in spec for spec in D["agents"].values()))

# WHERE A HEADLESS TUTOR'S PERMISSIONS LIVE, and the assertion is that this
# tool does not write them.
#
# The board used to write each course its own `.claude/settings.local.json`,
# because a daemon has nobody to approve a tool call and a refused write is
# silent. The grants were right; their home was wrong -- this tool was putting
# one vendor's config file into every repository it touched. They are
# `ai-config/workspaces/tutors.allow` now, folded into that assistant's own
# settings by its installer.
#
# So what is checked here is the absence, and the grants themselves are
# `ai-config`'s to test. An absence needs a test more than a presence does:
# nothing fails loudly when a writer creeps back in, it just starts leaving
# directories behind again.
board_src = open(os.path.join(ROOT, "bin", "board"), encoding="utf-8").read()
check("the board does not write any assistant's settings file",
      "install_permissions" not in board_src.replace(
          "# `install_permissions` wrote each course its own", ""))
check("and names no vendor's config directory as something it creates",
      'os.path.join(live.root, ".claude")' not in board_src)
check("and the note says where the grants went, so the next person adding one "
      "does not re-add the writer",
      "ai-config/workspaces/tutors.allow" in board_src)

# Every agent is a command, and no two machines have the same commands. A
# missing one used to start a daemon that showed as listening and then failed
# every turn into a log nobody opens.
check("a command that is not on the path is reported",
      recipes.missing_command(["a-command-no-machine-has"]) == "a-command-no-machine-has")
check("one that is, is not", recipes.missing_command(["sh"]) is None)
check("and a script agent runs under this interpreter, which is always here",
      recipes.missing_command([sys.executable, "anything.py"]) is None)
# CODEX WAS HALF A RECIPE: no first-turn entry, so `turn_plan` fell back to the
# resume one for a first turn and there was no resume path at all; and no
# `usage`, so every Codex turn was free in `cost.jsonl`.
codex = D["agents"]["codex"]
check("codex has a turn recipe", codex["headless_first"][:2] == ["codex", "exec"])
check("and it reports what a turn cost", codex["usage"] == "codex-jsonl")
# THE SANDBOX, WHICH IS THE WHOLE OF WHETHER IT CAN TUTOR AT ALL. `codex exec`
# defaults to read-only and answers the first write with `writing is blocked by
# read-only sandbox`, so the turn reads the brief, thinks, writes no card and
# exits 0. Asserted on BOTH recipes: a resumed turn that cannot write is the
# same silent failure one turn later.
check("a codex turn may write, or it is a tutor that produces nothing and "
      "says it succeeded",
      "--dangerously-bypass-approvals-and-sandbox" in codex["headless_first"])
first, _t = runturn.turn_plan(codex, "")
check("so a turn uses the first-turn recipe",
      first == codex["headless_first"])
# EVERY TURN IS FRESH. Every session's turn runs in the Atlas root, so a
# resume (`--continue`, `resume --last`) would pick up another session's.
for sig in ("", "unfinished", "revise", "writeup", "repair"):
    again, _t = runturn.turn_plan(claude, sig)
    check("a %s turn never resumes" % (sig or "lesson"),
          again == claude["headless_first"] and "--continue" not in again)

# A TURN IS HANDED NOTHING ON STDIN, and the client that made this matter is
# this one: `codex exec` reads stdin whenever it is not a terminal, appends it
# to the prompt, and waits for the far end to close. Started from a terminal
# that is never, so the turn sits there until its cap and says nothing -- which
# on the board is indistinguishable from a model thinking. `cat` is the
# faithful stand-in: it returns only when stdin is at end of file.
_stdin_log = tempfile.NamedTemporaryFile(prefix="tutor-stdin-", delete=False)
_stdin_log.close()
with open(_stdin_log.name, "w") as _fh:
    _rc, _capped = runturn.run_turn(["cat"], tempfile.gettempdir(), _fh, 10)
check("a turn whose client reads stdin comes straight back rather than "
      "waiting out its whole timeout on a pipe nobody is typing into",
      _rc == 0 and not _capped)
os.unlink(_stdin_log.name)

check("nothing in the table claims to teach for nothing",
      not any("cost" in spec for spec in D["agents"].values()))

# --- the provider table the board reads, built in-process -------------------
_table = recipes.listing({"provider": "deepseek", "fallback": "codex",
                          "agents": recipes.load_config().get("agents")})
check("the table names the provider and its fallback",
      _table.get("default") == "deepseek" and _table.get("fallback") == "codex")
check("and carries no switch", "only" not in _table
      and not any("barred" in a for a in _table.get("agents") or []))
check("and the old launcher, which printed it as --agents, is gone",
      not os.path.exists(os.path.join(ROOT, "bin", "tutor")))

# An in-fence recipe is no vision route either: an image is a hosted call.
from tutorboard import seeing                                 # noqa: E402
_got, _no = seeing.route("colibri", {"vision_agent": "colibri", "agents": [
    {"name": "colibri", "private": "it reads phi",
     "vision": {"cmd": ["coli"], "sighted": True}}]})
check("an in-fence recipe's vision route is refused, in words",
      _got is None and "in-fence" in (_no or ""))

# --- AND IT IS ASKED EVERY TURN ----------------------------------------------
src = open(os.path.join(ROOT, "tutorboard", "runner", "loop.py"),
           encoding="utf-8").read()
check("the recipe is re-bound inside the turn rather than above it",
      "ctx.cfg, name, spec, moved = for_this_turn(" in src
      and "cfg = recipes.load_config()" in src)
check("an unfinished report stays with the recipe that did the work",
      'signal == "unfinished"' in src)

# --- the shared filesystem ---------------------------------------------------
tmp = tempfile.mkdtemp(prefix="tutor-agents-")
live = os.path.join(tmp, "live")
os.makedirs(live)


def write_agent(**kw):
    kw.setdefault("last_seen", time.time())
    with open(os.path.join(live, "agent.json"), "w", encoding="utf-8") as fh:
        json.dump(kw, fh)


def attached():
    return daemon.attached(daemon.agent_record_at(live), host)


check("no record means nothing is listening", not attached())

write_agent(host="some-other-node", pid=1, agent="claude", state="listening")
check("a record from another node is not believed", not attached())

write_agent(host=host, pid=999999, agent="claude", state="listening")
check("a record for a pid that is gone is not believed", not attached())

write_agent(host=host, pid=os.getpid(), agent="claude", state="listening")
check("a record for a live process on this node is believed", attached())

# The runner writes its own pid, and a process either exists or it does not:
# a turn that goes quiet for ten minutes is still working.
write_agent(host=host, pid=os.getpid(), agent="claude", state="working",
            last_seen=time.time() - 600)
check("a turn in flight is not declared dead for going quiet", attached())

write_agent(host=host, pid=999999, agent="claude", state="working",
            last_seen=time.time())
check("but a record whose process is gone is not believed, heartbeat or not",
      not attached())

# Only a record with no pid at all has nothing better to go on.
write_agent(host=host, agent="claude", state="listening", last_seen=time.time() - 600)
check("a pidless record still expires on its heartbeat", not attached())
check("a recycled pid running something else is not this process",
      not daemon.pid_alive(os.getpid(), "a-command-this-process-is-not"))

# --- starting ----------------------------------------------------------------
# NOTHING STARTS A DAEMON: the board server's runner takes every turn.
check("there is no daemon to start, stop or hand over",
      not any(hasattr(daemon, n) for n in ("agent_start", "agent_stop",
                                           "agent_live", "handed_off",
                                           "mark_waking", "courses")))

# --- catching up with another machine ---------------------------------------
# A handoff written on one machine is worth nothing to another that never
# fetched it, so a session starts by pulling. It must never be fatal: someone
# holding an iPad cannot resolve a merge.
import subprocess  # noqa: E402


def git(*args, **kw):
    return subprocess.run(["git"] + list(args), stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL, **kw)


check("a directory that is not a repository is left alone",
      gitops.pull(tempfile.mkdtemp(prefix="tutor-plain-")) is None)

sandbox = tempfile.mkdtemp(prefix="tutor-sync-")
up = os.path.join(sandbox, "up")
here = os.path.join(sandbox, "here")
there = os.path.join(sandbox, "there")

git("init", "-q", "--bare", up)
git("symbolic-ref", "HEAD", "refs/heads/main", cwd=up)
git("init", "-q", "-b", "main", here)
for cfg in (("user.email", "t@t"), ("user.name", "T")):
    git("config", cfg[0], cfg[1], cwd=here)
with open(os.path.join(here, "HANDOFF.md"), "w", encoding="utf-8") as fh:
    fh.write("first\n")
git("add", "-A", cwd=here)
git("commit", "-qm", "first", cwd=here)

check("a repository with no remote is left alone", gitops.pull(here, quiet=True) is None)

git("remote", "add", "origin", up, cwd=here)
git("push", "-qu", "origin", "main", cwd=here)
git("clone", "-q", up, there)
for cfg in (("user.email", "t@t"), ("user.name", "T")):
    git("config", cfg[0], cfg[1], cwd=there)
with open(os.path.join(there, "HANDOFF.md"), "w", encoding="utf-8") as fh:
    fh.write("what the other machine taught\n")
git("commit", "-qam", "handoff from elsewhere", cwd=there)
git("push", "-q", cwd=there)

check("a session pulls what another machine pushed", gitops.pull(here, quiet=True) is True)
with open(os.path.join(here, "HANDOFF.md"), encoding="utf-8") as fh:
    check("and the handoff it wrote is the one now on disk",
          fh.read().strip() == "what the other machine taught")

# Diverged: the remote moved and so did this side. A pull cannot fast-forward,
# and the session still has to start.
with open(os.path.join(there, "HANDOFF.md"), "w", encoding="utf-8") as fh:
    fh.write("elsewhere again\n")
git("commit", "-qam", "elsewhere again", cwd=there)
git("push", "-q", cwd=there)
with open(os.path.join(here, "HANDOFF.md"), "w", encoding="utf-8") as fh:
    fh.write("locally, at the same time\n")
git("commit", "-qam", "local work", cwd=here)

check("a diverged branch reports rather than throwing",
      gitops.pull(here, quiet=True) is False)
check("and it does not touch the local work",
      open(os.path.join(here, "HANDOFF.md"), encoding="utf-8").read().strip()
      == "locally, at the same time")

shutil.rmtree(sandbox, ignore_errors=True)

# --- shipping ---------------------------------------------------------------
tool_src = open(os.path.join(ROOT, "tutorboard", "runner", "loop.py"),
                encoding="utf-8").read()
ship = os.path.join(ROOT, "scripts", "ship.sh")
check("there is one command that ships a change", os.path.isfile(ship))
ship_src = open(ship, encoding="utf-8").read() if os.path.isfile(ship) else ""
check("and it restarts the one board server, which runs every turn",
      'launchctl kickstart -k "$TARGET"' in ship_src)
check("and restarts nothing when the push failed",
      "nothing has been restarted" in ship_src)


print()
# A daemon being BOUNCED is not a daemon that died.
#
# Reported mid-lesson, right after a ship: "No tutor attached. NOW the tutor just
# got attached, but this is spotty and I don't like it." Both statements were
# true -- `tutor restart --tutors` stops each daemon and starts it again, and the
# gap between the two showed on the iPad as the dead-end chip a course that never
# had a tutor shows, plus the empty-board banner. The record is now marked on the
# way out, and the board says what is actually happening.

import time as _time                                         # noqa: E402
from tutorboard.lesson import state as _state                # noqa: E402

check("a record left by a restart in flight reads as reattaching",
      _state._reattaching({"restarting": True, "stopped_at": _time.time()}))
check("and one left by a restart that never finished does not, for ever",
      not _state._reattaching({"restarting": True,
                               "stopped_at": _time.time() - 10000}))
check("a daemon that simply died is not dressed up as a restart",
      not _state._reattaching({"stopped_at": _time.time()}))
check("and the board has a word for it that is not 'nothing is reading'",
      'agent.state === "reattaching"' in
      open(os.path.join(ROOT, "web", "board.js"), encoding="utf-8").read())

print()
# ------------------------------------------- a turn that wrote nothing says so
#
# THE HALF THAT MAKES A BROKEN PROVIDER SPECTACULAR RATHER THAN MERELY BROKEN.
# A turn fails, no card is written, and the board goes back to `claude
# listening` with `last_error: null` -- so the student's working is in and the
# chrome says everything is fine. Two ways that record gets emptied, and both
# are here.

silent = tempfile.mkdtemp(prefix="tutor-silent-")
silent_live = os.path.join(silent, "live")
os.makedirs(silent_live)
def wrote_failure(agent):
    with open(os.path.join(silent_live, "agent.json"), "w", encoding="utf-8") as fh:
        json.dump({"agent": agent, "state": "listening", "pid": 4321,
                   "failed_agent": agent,
                   "last_error": "API Error: Connection dropped (ECONNRESET) (exit 1)",
                   "failed_at": time.time(),
                   "handover": "2026-09-20 10:00:00"}, fh)


wrote_failure("deepseek")
check("and the same is true of a climb-down between turns, which writes the "
      "new agent onto the record the same way",
      daemon.not_this_agents_failure(silent_live, "claude")
      == {"last_error": None, "failed_at": 0, "failed_agent": None}
      and daemon.not_this_agents_failure(silent_live, "deepseek") == {})

# WHAT RETIRES IT IS SOMETHING NEWER, AND A TURN STARTING IS NOT THAT. A turn
# that has begun settles nothing about the failure before it: a daemon killed
# mid-turn would leave `working`, no error and no card -- the empty record, one
# state along.
check("a turn that goes through is what clears it, and the daemon still does that",
      'agent_state(live, state="listening", last_error=None,\n'
      '                           failed_at=0, failed_agent=None, retrying=False)'
      in tool_src)
check("and the turn that merely STARTS does not, which is what the docstring "
      "above says happens",
      'agent_state(live, state="working", turns=ctx.turns,\n'
      '                       turn_started=time.time(), turn_signal=this_signal,\n'
      '                       turn_repairs=turn_repairs)'
      in tool_src)
check("what stops the board painting last time's failure over a turn in flight "
      "is the reader, which does not report one older than the running turn",
      'if st.get("state") == "working":' in
      open(os.path.join(ROOT, "tutorboard", "lesson", "state.py"),
           encoding="utf-8").read())

# AND THE EXIT CODE IS NOT THE LAST WORD ON WHETHER A TURN WORKED. It is the
# agent summarising itself; the result object is the agent saying what happened.
blob = ('{"type":"result","subtype":"success","is_error":true,'
        '"result":"API Error: Connection dropped (ECONNRESET)",'
        '"duration_api_ms":0,"total_cost_usd":0}')
check("an agent that reports its own failure is read as one, whatever it exited",
      usage.result_object_error("some output\n" + blob)
      == "API Error: Connection dropped (ECONNRESET)")
check("and a turn that went through is not made into a failure by the same read",
      usage.result_object_error('{"type":"result","is_error":false,"result":"ok"}')
      is None)
check("so the daemon reads what the turn said BEFORE it believes the number, "
      "and a turn that reported a failure and exited 0 is still a failed turn",
      "said = usage.turn_output(logpath, mark)\n"
      "    if not err and usage.result_object_error(said):" in tool_src)
check("and what the board is told is the turn's own sentence rather than the "
      "number, which is the same for every cause",
      usage.failure_reason(blob, "exit 1")
      == "API Error: Connection dropped (ECONNRESET) (exit 1)")

# AND A RESULT OBJECT TOO LONG TO HAVE SURVIVED WHOLE still says what happened.
# `turn_output` reads back the last 20 KB, so a turn with many round trips has
# its final line cut at the front -- and the exit code is then the only thing
# left, which is the dead end all of this exists to end. Cut the way a byte
# offset cuts: no opening brace, because that is the test the fragment must not
# have to pass.
cut = ('rations":[' + "x" * 40 + '}],"is_error":true,'
       '"result":"API Error: 404 model not found","type":"result",'
       '"duration_ms":171868}')
check("a result object cut off at the front is still read for the reason, "
      "rather than falling back to the number",
      usage.result_object_error(cut) == "API Error: 404 model not found")
check("and a fragment is only answered for where it is a result object, so an "
      "ordinary log line carrying the word is not mistaken for a verdict",
      usage.result_object_error('  ... "result" of the sweep: 3 files\n') is None)
check("a truncated result object that reports no failure is still the newest "
      "verdict, and ends the scan rather than letting an older one through",
      usage.result_object_error(
          '{"type":"result","is_error":true,"result":"an older failure"}\n'
          'ons":1}],"is_error":false,"result":"done","type":"result"}') is None)

# THE WRAP-UP IS A TURN AND IS JUDGED LIKE ONE. TUTOR.md always exists, from
# the turns before, so a wrap-up that died on the wire must not be logged as
# having written it.
check("the wrap-up believes the turn rather than the directory listing: the "
      "exit code, the result object and a file newer than the turn",
      "rc, timed_out = turn.run_turn(" in tool_src.split("def wrap_up(")[1]
      and "wrote = not failed and os.path.getmtime(landing) > before" in tool_src)
check("and a wrap-up that failed says TUTOR.md is what the last turn left",
      "the wrap-up turn failed (%s); TUTOR.md is " in tool_src)

# NO STRIKE STAND-DOWN: a recipe failing the same way twice is reported in the
# provider's own words and is not stood down; the resolver's reasons are a
# missing binary, a missing key and a usage limit.
check("a repeated failure stands nothing down",
      "mark_failing" not in tool_src and "striking" not in tool_src)
shutil.rmtree(silent, ignore_errors=True)


print("%d FAILURES" % len(fails) if fails else "a provider, every other one behind it, and nothing else chooses")
sys.exit(1 if fails else 0)
