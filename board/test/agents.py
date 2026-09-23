#!/usr/bin/env python3
"""Which assistant tutors which course, on which machine.

Four layers resolve it and the order is the whole feature: a course that names
its own assistant must beat the machine default, and the machine default must
beat the global one, or the same configuration cannot serve a laptop and a
cluster node at once.

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
from tutorboard import limits, processes                      # noqa: E402

loader = importlib.machinery.SourceFileLoader("tutor", os.path.join(ROOT, "bin", "tutor"))
spec = importlib.util.spec_from_loader("tutor", loader)
tutor = importlib.util.module_from_spec(spec)
loader.exec_module(tutor)

fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


CFG = {
    "default_agent": "claude",
    "hosts": {"mac-mini": "opencode", "compute303": "claude"},
    "agents": {"claude": {"cmd": ["claude"]},
               "opencode": {"cmd": ["opencode"]},
               "codex": {"cmd": ["codex"]}},
}

host = tutor.this_host()
CFG["hosts"][host] = "opencode"          # pretend this machine prefers opencode

check("the command line wins over everything",
      tutor.resolve_agent(CFG, {"agent": "claude"}, "codex") == "codex")

check("a course that names its assistant beats the machine default",
      tutor.resolve_agent(CFG, {"agent": "claude"}) == "claude")

check("the machine default beats the global one",
      tutor.resolve_agent(CFG, {}) == "opencode")

no_host = dict(CFG, hosts={})
check("without a machine entry it falls through to default_agent",
      tutor.resolve_agent(no_host, {}) == "claude")

check("an unknown name resolves to nothing rather than to a wrong agent",
      tutor.resolve_agent(CFG, {"agent": "nonesuch"}) is None)

check("a course with no opinion and no machine entry still resolves",
      tutor.resolve_agent(no_host, None) == "claude")

# --- the default, and where its permissions are NOT written ------------------
# Claude Code is the default tutor. Headless there is nobody to approve anything,
# and a refused tool is not an error -- the agent apologises into a log nobody
# opens and exits 0, which reaches the board as a tutor who answered with
# silence. That is already solved, and solved in one place: `board start` writes
# the course its own `.claude/settings.local.json`. The recipe must not repeat
# it. One policy in two files is one policy that drifts the first time either
# moves, and the committed file is the half a course's owner can actually see.
D = tutor.DEFAULT_CONFIG
claude = D["agents"]["claude"]

check("Claude is the tutor unless something more specific says otherwise",
      D["default_agent"] == "claude")

for kind in ("headless_first", "headless"):
    recipe = " ".join(claude[kind])
    check("the %s recipe does not carry a second copy of the permissions" % kind,
          "acceptEdits" not in recipe and "allowedTools" not in recipe)

check("a resumed turn is still a resumed turn",
      "--continue" in claude["headless"] and "--continue" not in claude["headless_first"])

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
      tutor.missing_command(["a-command-no-machine-has"]) == "a-command-no-machine-has")
check("one that is, is not", tutor.missing_command(["sh"]) is None)
check("and a script agent runs under this interpreter, which is always here",
      tutor.missing_command([sys.executable, "anything.py"]) is None)
# CODEX WAS HALF A RECIPE: no first-turn entry, so `turn_plan` fell back to the
# resume one for a first turn and there was no resume path at all; and no
# `usage`, so every Codex turn was free in `cost.jsonl`.
codex = D["agents"]["codex"]
check("codex has a first-turn recipe and a resume recipe, and they differ",
      codex["headless_first"] != codex["headless"])
check("the resume spelling is the installed binary's own",
      codex["headless"][:4] == ["codex", "exec", "resume", "--last"])
check("and it reports what a turn cost", codex["usage"] == "codex-jsonl")
first, _t, fresh = tutor.turn_plan(codex, 0, 1, "")
check("so a first turn uses the first-turn recipe",
      fresh and first == codex["headless_first"])
again, _t, fresh2 = tutor.turn_plan(codex, 1, 0, "")
check("and a second resumes", not fresh2 and again == codex["headless"])

check("there is one tutor and it is the one the config names",
      D["default_agent"] == "claude" and "claude" in D["agents"])
check("and nothing in the table claims to teach for nothing",
      not any("cost" in spec for spec in D["agents"].values()))

# --- WHO TAKES THE TURN WHEN THE ONE WE WANT CANNOT -------------------------
#
# The comment in `cmd_headless` promised this and the code stood still: on a
# limit it wrote the record, logged that turns would go on failing, and did
# nothing. That was the right answer when there was one tutor. There are three,
# and an evening ending because a provider said no more is the thing that still
# sends somebody to a laptop and an account page.
#
# What makes an automatic swap safe is measured rather than hoped: `session_turns`
# is 1, so every ordinary turn is cold and reads the evening back off disk. There
# is no conversation to transfer.
limits.LIMIT_RECORD = os.path.join(
    os.environ["BOARD_STATE_DIR"], "limited.json")
limits.clear_limited()

SH = {"cmd": ["sh"], "headless": ["sh", "-c", "{prompt}"]}
THREE = {"default_agent": "one", "agents": {
    "one": dict(SH), "two": dict(SH), "three": dict(SH),
    "fenced": dict(SH, private="it reads phi"),
    "ghost": {"cmd": ["a-command-no-machine-has"],
              "headless": ["a-command-no-machine-has"]},
    "unkeyed": dict(SH, needs_key="A-KEY-NO-MACHINE-HAS")}}

check("nothing wrong means nothing moves",
      tutor.choose_agent(THREE, "one") == ("one", None))

limits.mark_limited(time.time() + 900, agent="one")
name, why = tutor.choose_agent(THREE, "one")
check("a limited agent hands the turn to the next one that can take it",
      name != "one" and name in ("two", "three"))
check("and the log line says which and why, because the board paints it",
      "one" in (why or "") and name in (why or ""))

limits.mark_limited(time.time() + 900, agent=name)
second, _ = tutor.choose_agent(THREE, "one")
check("a second one hitting its own ceiling falls through to the third",
      second not in ("one", name))

for n in ("one", "two", "three"):
    limits.mark_limited(time.time() + 900, agent=n)
check("all of them limited behaves exactly as one tutor always did: the turn "
      "goes to the one we wanted and fails where that is visible",
      tutor.choose_agent(THREE, "one") == ("one", None))

limits.clear_limited()
limits.mark_limited(time.time() + 900, agent="one")
check("A FENCED RECIPE IS NEVER FALLEN INTO. It is the only assistant allowed "
      "to read phi and its cards must not reach a remote, so it is not a "
      "choice an automatic swap gets to make",
      tutor.choose_agent(dict(THREE, agents={
          "one": THREE["agents"]["one"],
          "fenced": THREE["agents"]["fenced"]}), "one") == ("one", None))
check("nor is one this machine has not got",
      tutor.choose_agent(dict(THREE, agents={
          "one": THREE["agents"]["one"],
          "ghost": THREE["agents"]["ghost"]}), "one") == ("one", None))
check("nor one whose key is not here -- that is a daemon that listens and then "
      "fails every turn into a log",
      tutor.choose_agent(dict(THREE, agents={
          "one": THREE["agents"]["one"],
          "unkeyed": THREE["agents"]["unkeyed"]}), "one") == ("one", None))

ordered = dict(THREE, fallback=["two", "three"])
check("the order is the config's where it has one",
      tutor.choose_agent(ordered, "one")[0] == "two")
check("and where it has none it is what `--agents` reports, in that order -- "
      "a list nobody has set should still do something sensible",
      tutor.choose_agent(THREE, "one")[0] == "three")

limits.clear_limited()
check("and when the allowance comes back we climb home, because the question "
      "is asked again every turn rather than answered once",
      tutor.choose_agent(THREE, "one") == ("one", None))

# --- AND IT IS ASKED EVERY TURN ----------------------------------------------
src = open(os.path.join(ROOT, "bin", "tutor"), encoding="utf-8").read()
check("the recipe is re-bound inside the loop rather than above it",
      "cfg, next_agent, next_spec, moved = for_this_turn(" in src)
check("a carry is immune: it resumes a conversation by id, which is the one "
      "thing a swap would throw away",
      'signal == "carry"' in src and "resumes a conversation by id" in src)
check("and so is a session that is genuinely carrying turns",
      "this agent's own session is carrying" in src)
check("the paragraph saying an assistant cannot be changed mid-way is gone, "
      "because it is no longer true",
      "chosen as a sitting OPENS and not mid-way" not in src)
check("and what IS true is written where the next turn will read it",
      "AN ASSISTANT IS RE-RESOLVED EVERY TURN" in src)

# --- the shared filesystem ---------------------------------------------------
tmp = tempfile.mkdtemp(prefix="tutor-agents-")
live = os.path.join(tmp, "live")
os.makedirs(live)


def write_agent(**kw):
    kw.setdefault("last_seen", time.time())
    with open(os.path.join(live, "agent.json"), "w", encoding="utf-8") as fh:
        json.dump(kw, fh)


check("no record means nothing is listening", tutor.agent_live(tmp) is None)

write_agent(host="some-other-node", pid=1, agent="claude", state="listening")
check("a record from another node is not believed", tutor.agent_live(tmp) is None)

write_agent(host=host, pid=999999, agent="claude", state="listening")
check("a record for a pid that is gone is not believed", tutor.agent_live(tmp) is None)

write_agent(host=host, pid=os.getpid(), agent="claude", state="listening")
st = tutor.agent_live(tmp)
check("a record for a live process on this node is believed",
      bool(st) and st.get("agent") == "claude")

# --- the two kinds of record expire differently ------------------------------
# A headless daemon has a heartbeat, so silence means it died. An interactive
# assistant is idle for exactly as long as the person in front of it is thinking,
# and judging that by a heartbeat is why the board's indicator never once turned
# green in an ordinary `tutor` session: nothing outside headless ever wrote one.

# A daemon records its own pid, and a process either exists or it does not.
# The heartbeat is written at turn boundaries, so a daemon in the middle of a
# long turn goes silent while working perfectly well -- and a teaching turn
# routinely runs past two minutes. That silence used to read as death: the board
# said "assistant not responding" while the tutor was writing the card.
write_agent(host=host, pid=os.getpid(), agent="claude", state="working",
            last_seen=time.time() - 600)
st = tutor.agent_live(tmp)
check("a daemon mid-turn is not declared dead for going quiet",
      bool(st) and st.get("state") == "working")

write_agent(host=host, pid=999999, agent="claude", state="working",
            last_seen=time.time())
check("but a daemon whose process is gone is not believed, heartbeat or not",
      tutor.agent_live(tmp) is None)

# Only a record with no pid at all has nothing better to go on.
write_agent(host=host, agent="claude", state="listening", last_seen=time.time() - 600)
check("a pidless record still expires on its heartbeat",
      tutor.agent_live(tmp) is None)

write_agent(host=host, pid=os.getpid(), agent="claude", state="attached",
            mode="interactive", cmd=sys.executable, last_seen=time.time() - 6000)
st = tutor.agent_live(tmp)
check("an interactive assistant idle for an hour is still attached",
      bool(st) and st.get("state") == "attached")

write_agent(host=host, pid=999999, agent="claude", state="attached",
            mode="interactive", cmd=sys.executable, last_seen=time.time())
check("but one whose process is gone is not",
      tutor.agent_live(tmp) is None)

write_agent(host=host, pid=os.getpid(), agent="claude", state="attached",
            mode="interactive", cmd="a-command-this-process-is-not")
check("and a recycled pid running something else is not either",
      tutor.agent_live(tmp) is None)

# `headless --stop` is for daemons. Someone is sitting in front of an interactive
# session, and killing it is not what anyone typing that meant. This one needs a
# courses_dir of its own, because stopping walks every course it can find.
box = tempfile.mkdtemp(prefix="tutor-courses-")
boxed = os.path.join(box, "fake-course", "live")
os.makedirs(boxed)
with open(os.path.join(boxed, "agent.json"), "w", encoding="utf-8") as fh:
    json.dump({"host": host, "pid": os.getpid(), "agent": "claude",
               "state": "attached", "mode": "interactive", "cmd": sys.executable,
               "last_seen": time.time()}, fh)
tutor.headless_stop({"courses_dir": box, "agents": {}}, [])
check("headless --stop leaves an interactive session alone",
      os.path.exists(os.path.join(boxed, "agent.json")))
shutil.rmtree(box, ignore_errors=True)

write_agent(host=host, pid=os.getpid(), agent="claude", state="listening")

# --- starting ----------------------------------------------------------------
course = {"root": tmp, "dir": "fake-course", "name": "Fake"}
code, msg = tutor.agent_start(CFG, course, "claude")
check("starting is a no-op while one is already listening",
      code == 0 and "already listening" in msg)

os.remove(os.path.join(live, "agent.json"))
code, msg = tutor.agent_start(CFG, course, "claude")
check("an agent with no headless recipe refuses rather than half-starting",
      code == 1 and "headless recipe" in msg)

code, msg = tutor.agent_start(CFG, course, None)
check("an unresolved agent refuses", code == 1 and "no agent resolved" in msg)

ghost = dict(CFG, agents=dict(CFG["agents"],
                              ghost={"cmd": ["a-command-no-machine-has"],
                                     "headless": ["a-command-no-machine-has", "{prompt}"]}))
code, msg = tutor.agent_start(ghost, course, "ghost")
check("an agent whose command this machine lacks refuses rather than "
      "listening and failing every turn",
      code == 1 and "not on the path" in msg)

code, msg = tutor.agent_stop(course)
check("stopping something that is not there is not an error",
      code == 0 and "nothing was listening" in msg)

# --- catching up with another machine ---------------------------------------
# A handoff written on one machine is worth nothing to another that never
# fetched it, so a session starts by pulling. It must never be fatal: someone
# holding an iPad cannot resolve a merge.
import subprocess  # noqa: E402


def git(*args, **kw):
    return subprocess.run(["git"] + list(args), stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL, **kw)


check("a directory that is not a repository is left alone",
      tutor.sync(tempfile.mkdtemp(prefix="tutor-plain-")) is None)

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

check("a repository with no remote is left alone", tutor.sync(here, quiet=True) is None)

git("remote", "add", "origin", up, cwd=here)
git("push", "-qu", "origin", "main", cwd=here)
git("clone", "-q", up, there)
for cfg in (("user.email", "t@t"), ("user.name", "T")):
    git("config", cfg[0], cfg[1], cwd=there)
with open(os.path.join(there, "HANDOFF.md"), "w", encoding="utf-8") as fh:
    fh.write("what the other machine taught\n")
git("commit", "-qam", "handoff from elsewhere", cwd=there)
git("push", "-q", cwd=there)

check("a session pulls what another machine pushed", tutor.sync(here, quiet=True) is True)
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
      tutor.sync(here, quiet=True) is False)
check("and it does not touch the local work",
      open(os.path.join(here, "HANDOFF.md"), encoding="utf-8").read().strip()
      == "locally, at the same time")

shutil.rmtree(sandbox, ignore_errors=True)

# --- restarting every board on this machine ----------------------------------
# A board read serve.py when it started, so a change to the tool reaches a course
# only when its board comes back. The pages are served from disk and look new
# while the endpoints behind them are the old ones -- invisible from outside.
import subprocess as _sp
tool_src = open(os.path.join(ROOT, "bin", "tutor"), encoding="utf-8").read()
check("there is a command to restart every board here",
      "def cmd_restart(" in tool_src)
check("and it refuses to touch a board belonging to another node",
      'info["node"] != host' in tool_src)
check("and only ones that are genuinely answering",
      "board_is_running" in tool_src)

ship = os.path.join(ROOT, "scripts", "ship.sh")
check("there is one command that ships a change", os.path.isfile(ship))
ship_src = open(ship, encoding="utf-8").read() if os.path.isfile(ship) else ""
check("and it restarts the tutors as well as the boards",
      "--tutors" in ship_src)
check("and restarts nothing when the push failed",
      "nothing has been restarted" in ship_src)
check("a tutor mid-turn is not bounced out of the card it is writing",
      "mid-turn" in tool_src)
check("a restart that did not happen is not reported as one",
      "did not come back" in tool_src and 'now["pid"] != was' in tool_src)
# AND THE SAME MISTAKE THE OTHER WAY ROUND. `agent_start` writes `waking` with no
# pid and then forks, so a record read the instant it returns has no pid in it --
# and the check above then called every successful restart one it had left alone.
# Read off a real ship, with both daemons coming back on the new code at the
# time: "left alone: claude starting in Galois-Theory".
restart_src = tool_src[tool_src.index("def cmd_restart("):]
restart_src = restart_src[:restart_src.index("\ndef ", 1)]
check("a restart that DID happen is not reported as one that did not",
      "RESTART_WAIT" in restart_src and "coming back" in restart_src)
# The tutor half only: the boards above have a `left alone` of their own, for a
# board belonging to another node, and it is the right answer there.
tutors_src = restart_src[restart_src.index('"--tutors" not in args'):]
check("and it waits for the daemon's own record rather than reading it once",
      tutors_src.index("agent_start(cfg, c, name)")
      < tutors_src.index("for _ in range(RESTART_WAIT)")
      < tutors_src.index('print("  left alone'))
check("the wait is bounded, because a person is watching a terminal",
      tutor.RESTART_WAIT and tutor.RESTART_WAIT <= 60)
check("a start still on its way is its own answer, not a failure",
      "coming.append" in restart_src and "held.append" in restart_src)
check("and a tutor still writing its handoff is said to be, not claimed restarted",
      "still writing its handoff" in tool_src)
check("and stopping one waits for its handoff to be written",
      "agent_live(c[\"root\"])" in tool_src)

# A restart is when a changed default actually reaches a course. It used to
# bring back whatever the record named, so a config that said `claude` sat beside
# a board running `free` indefinitely -- and the only way out was to stop the
# tutor by hand. The stop is the safe moment: SIGTERM makes the outgoing tutor
# write HANDOFF.md, which is exactly what the incoming one reads.
check("a restart asks configuration which tutor to bring back",
      "resolve_agent(cfg, c) or was_name" in tool_src)
check("and falls back to the one that was running if nothing resolves",
      "or was_name" in tool_src)
check("and says so when the restart changed the tutor",
      '"%s (%s -> %s)" % (c["dir"], was_name, name)' in tool_src)

push_src = open(os.path.join(ROOT, "scripts", "save-and-push.sh"), encoding="utf-8").read()
check("pushing the tool restarts the boards it drives", "tutor restart" in push_src)
# Asserted on the TEST the script makes, not on a sentence near it: a commit in
# a repository the tool does not live in cannot have changed the tool, whatever
# it touched, and `ROOT` is the repository the caller was standing in.
check("but a course pushing its own work does not",
      '[ "$TOOL_ROOT" = "$ROOT" ]' in push_src
      and 'ROOT="$(git rev-parse --show-toplevel' in push_src)
check("and a failure to restart does not fail the push",
      "|| echo" in push_src)

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

check("a restart says on disk that it is a restart",
      'agent_state(c["root"] + "/live", restarting=True' in tool_src)
check("and a clean stop keeps the record rather than deleting it, so the board "
      "can tell 'stopped' from 'never had one'",
      'agent_state(live, state="stopped"' in tool_src
      and "os.remove(os.path.join(live, \"agent.json\"))" not in tool_src)
# AND THE EXIT DOES NOT SAY WHY, BECAUSE IT DOES NOT KNOW WHY. `restarting` is
# written by the asker, before the signal; a daemon receiving a SIGTERM cannot
# tell a bounce from a person leaving. Writing `restarting: False` on the way out
# made every restart nobody finished identical to `tutor agent stop`, which the
# watch loop obeys for ever -- measured as fifteen hours of a Galois Theory board
# serving perfectly with nothing reading it. `test/waking.py` holds the other end
# of that contract.
check("and it does not overwrite the flag that says a restart asked for it",
      'restarting' not in
      [l for l in tool_src.splitlines()
       if 'agent_state(live, state="stopped"' in l][0])
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
# A BOARD AND ITS TUTOR ARE TWO PROCESSES AND THEY DIE SEPARATELY.
#
# The daemon's node lost its allocation; the board came back on the next node
# logged in to, and no tutor came with it. Nothing was ever going to notice from
# the machine the person actually works on: `tutor resume` saw a board on a node
# that is still theirs, said it was leaving it there, and returned BEFORE
# `ensure_agent` -- and `tutor restart --tutors` only bounces tutors that are
# already attached, so it reported "no tutors were attached" and moved on. The
# lesson sat on the iPad with nothing listening to it.

import contextlib                                            # noqa: E402
import io as _io                                             # noqa: E402

away = tempfile.mkdtemp(prefix="tutor-away-")
away_root = os.path.join(away, "Fake-Course")
away_live = os.path.join(away_root, "live")
os.makedirs(away_live)
open(os.path.join(away_root, "AI_INSTRUCTIONS.md"), "w").close()
with open(os.path.join(away_live, ".board.json"), "w", encoding="utf-8") as fh:
    json.dump({"pid": 1, "port": 9098, "node": "othernode", "root": away_root,
               "started": time.time()}, fh)

AWAY_CFG = {"courses_dir": away, "default_agent": "claude",
            "agents": {"claude": {"cmd": ["claude"],
                                  "headless": [sys.executable, "-c", "pass"]}}}

was_env = os.environ.pop("TUTORBOARD_COURSES", None)
started, sshed = [], []
real = {k: getattr(tutor, k) for k in
        ("board", "link", "sync", "pull_vendor", "prune_dead_records",
         "ssh_tool", "agent_start")}
real_nodes = tutor.machine.slurm_nodes
tutor.board = lambda root, *a: (0, "")
tutor.link = lambda root: None
tutor.sync = lambda root, quiet=False: None
tutor.pull_vendor = lambda quiet=False: None
tutor.prune_dead_records = lambda cfg, host: []
tutor.agent_start = lambda cfg, c, name, session=None: (started.append(c["dir"]) or (0, "started"))
tutor.ssh_tool = lambda target, tail, timeout=300: (
    sshed.append((target, list(tail))) or (0, "claude starting in Fake-Course\n"))
tutor.machine.slurm_nodes = lambda: {host, "othernode"}
# Nothing is serving in this world. A running chain makes its node home and a
# login elsewhere leaves the boards alone, which is a question about the real
# queue -- and what is in the real queue is not allowed to decide what a suite
# asserts. `test/perpetual.py` owns that rule.
tutor.supervise.serving_node = lambda rows=None: None


def away_agent(**kw):
    path = os.path.join(away_live, "agent.json")
    if not kw:
        if os.path.exists(path):
            os.remove(path)
        return
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(kw, fh)


try:
    check("the fixture's board is the one a resume would bring back",
          (tutor.last_board(AWAY_CFG) or {}).get("dir") == "Fake-Course")

    away_agent()
    del sshed[:]
    tutor.cmd_resume(AWAY_CFG, ["--quiet"])
    check("a board left on another of your nodes is still asked whether a "
          "tutor is listening to it",
          sshed == [("othernode", ["agent", "ensure", "Fake-Course"])])
    check("and the board itself is not moved to do it", not started)

    away_agent(host="othernode", agent="claude", state="listening",
               pid=4021421, last_seen=time.time())
    del sshed[:]
    tutor.cmd_resume(AWAY_CFG, ["--quiet"])
    check("a tutor that is beating over there costs the login nothing",
          sshed == [])

    away_agent(host="othernode", agent="claude", state="listening",
               pid=4021421, last_seen=time.time() - 3600)
    del sshed[:]
    tutor.cmd_resume(AWAY_CFG, ["--quiet"])
    check("but one that has been silent for an hour is asked about",
          sshed == [("othernode", ["agent", "ensure", "Fake-Course"])])

    del sshed[:]
    tutor.cmd_resume(AWAY_CFG, ["--quiet", "--no-agent"])
    check("--no-agent still means no tutor, here or anywhere else", sshed == [])

    # `ensure` is `start` that says nothing when there was nothing to do: it is
    # asked on every login from another machine, and a line per shell for a
    # tutor that is fine is noise in the one log a real failure has to be
    # findable in.
    away_agent(host=host, agent="claude", state="listening", pid=os.getpid())
    del started[:]
    check("ensure starts nothing when a tutor is already attached",
          tutor.cmd_agent(AWAY_CFG, ["ensure", "Fake-Course"]) == 0 and not started)

    away_agent(host=host, agent="claude", state="listening", pid=999999)
    del started[:]
    check("and starts one when the record names a process that is gone",
          tutor.cmd_agent(AWAY_CFG, ["ensure", "Fake-Course"]) == 0
          and started == ["Fake-Course"])

    # WHICH ASSISTANT THIS WORKSPACE RUNS WHEN NOBODY NAMES ONE, asked rather
    # than worked out a second time. A mission that STARTS an assistant gives
    # it back when it ends and an assistant a person chose stays, so the board
    # has to know which name the configuration would have produced -- and
    # `resolve_agent` is the one place those five layers live.
    out = _io.StringIO()
    with contextlib.redirect_stdout(out):
        code = tutor.cmd_agent(AWAY_CFG, ["which", "Fake-Course"])
    check("the launcher will say which assistant a workspace runs, and say "
          "nothing else, because the board reads this rather than a person",
          code == 0 and out.getvalue() == "claude\n")

    out = _io.StringIO()
    with contextlib.redirect_stdout(out):
        code = tutor.cmd_agent(dict(AWAY_CFG, default_agent="nonesuch"),
                               ["which", "Fake-Course"])
    check("and an empty line where the configuration resolves to nothing, "
          "rather than a name nothing can run",
          code == 0 and out.getvalue() == "\n")
finally:
    for k, v in real.items():
        setattr(tutor, k, v)
    tutor.machine.slurm_nodes = real_nodes
    if was_env is not None:
        os.environ["TUTORBOARD_COURSES"] = was_env
    shutil.rmtree(away, ignore_errors=True)

# And `tutor where` is where a person asks. It read the pid against THIS
# machine's process table, so a daemon listening perfectly well on the node the
# board is on came back as `stale` -- on the machine they type the question on.

seen = tempfile.mkdtemp(prefix="tutor-where-")
seen_live = os.path.join(seen, "Away-Course", "live")
os.makedirs(seen_live)
open(os.path.join(seen, "Away-Course", "AI_INSTRUCTIONS.md"), "w").close()
with open(os.path.join(seen_live, "agent.json"), "w", encoding="utf-8") as fh:
    json.dump({"host": "othernode", "agent": "claude", "state": "listening",
               "pid": 4021421, "last_seen": time.time()}, fh)
was_env = os.environ.pop("TUTORBOARD_COURSES", None)
try:
    out = _io.StringIO()
    with contextlib.redirect_stdout(out):
        tutor.cmd_where({"courses_dir": seen, "agents": {}}, [])
    said = out.getvalue()
    check("a tutor listening on another node is not reported as a stale record",
          "claude listening on othernode" in said and "stale" not in said)

    with open(os.path.join(seen_live, "agent.json"), "w", encoding="utf-8") as fh:
        json.dump({"host": "othernode", "agent": "claude", "state": "listening",
                   "pid": 4021421,
                   "last_seen": time.time() - processes.AWAY_SILENCE - 1}, fh)
    out = _io.StringIO()
    with contextlib.redirect_stdout(out):
        tutor.cmd_where({"courses_dir": seen, "agents": {}}, [])
    check("and one that stopped beating there is still called stale",
          "stale" in out.getvalue())
finally:
    if was_env is not None:
        os.environ["TUTORBOARD_COURSES"] = was_env
    shutil.rmtree(seen, ignore_errors=True)

# The record is the only evidence there is from another machine: the pid in it
# belongs to a process table this one cannot read, and reading the local one
# instead is how a stranger's process gets mistaken for a tutor.
now = time.time()
check("a record from the node in question, beating, reads as attached",
      processes.agent_attached_away(
          {"host": "othernode", "last_seen": now, "state": "listening"}, "othernode"))
check("the same record does not vouch for a different node",
      not processes.agent_attached_away(
          {"host": "othernode", "last_seen": now}, "thirdnode"))
check("silence past three of the daemon's own wake-ups is death",
      not processes.agent_attached_away(
          {"host": "othernode", "last_seen": now - processes.AWAY_SILENCE - 1},
          "othernode"))
check("a start in flight over there is not a death either",
      processes.agent_attached_away(
          {"host": "othernode", "state": "waking", "waking_at": now}, "othernode"))
check("and one that never finished does not claim to be starting for ever",
      not processes.agent_attached_away(
          {"host": "othernode", "state": "waking",
           "waking_at": now - processes.WAKING_GRACE - 1}, "othernode"))


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
with open(os.path.join(silent_live, "agent.json"), "w", encoding="utf-8") as fh:
    json.dump({"agent": "deepseek", "state": "listening", "pid": 4321,
               "last_error": "API Error: Connection dropped (ECONNRESET) (exit 1)",
               "failed_at": time.time(), "handover": "2026-09-20 10:00:00"}, fh)
woke = tutor.mark_waking(silent_live, "claude", pid=os.getpid())
check("a start does not erase the last turn's failure -- a daemon is most often "
      "restarted BECAUSE the turn fell over, and clearing the reason there "
      "empties the record at the one moment somebody is reading it",
      woke.get("last_error", "").startswith("API Error") and woke.get("failed_at"))
check("and it still answers the flags a start is the answer to",
      not woke.get("handover") and woke.get("state") == "waking")

# WHAT RETIRES IT IS SOMETHING NEWER, which is the next turn that goes through.
check("a turn that goes through is what clears it, and the daemon still does that",
      'agent_state(live, state="listening", last_error=None,\n'
      '                        failed_at=0, retrying=False)' in tool_src)

# AND THE EXIT CODE IS NOT THE LAST WORD ON WHETHER A TURN WORKED. It is the
# agent summarising itself; the result object is the agent saying what happened.
blob = ('{"type":"result","subtype":"success","is_error":true,'
        '"result":"API Error: Connection dropped (ECONNRESET)",'
        '"duration_api_ms":0,"total_cost_usd":0}')
check("an agent that reports its own failure is read as one, whatever it exited",
      tutor.result_object_error("some output\n" + blob)
      == "API Error: Connection dropped (ECONNRESET)")
check("and a turn that went through is not made into a failure by the same read",
      tutor.result_object_error('{"type":"result","is_error":false,"result":"ok"}')
      is None)
check("so the daemon reads what the turn said BEFORE it believes the number, "
      "and a turn that reported a failure and exited 0 is still a failed turn",
      "said = turn_output(logpath, mark)\n"
      "        if not err and result_object_error(said):" in tool_src)
check("and what the board is told is the turn's own sentence rather than the "
      "number, which is the same for every cause",
      tutor.failure_reason(blob, "exit 1")
      == "API Error: Connection dropped (ECONNRESET) (exit 1)")
shutil.rmtree(silent, ignore_errors=True)


print("%d FAILURES" % len(fails) if fails else "the assistant follows the course")
sys.exit(1 if fails else 0)
