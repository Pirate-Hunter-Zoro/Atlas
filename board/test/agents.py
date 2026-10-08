#!/usr/bin/env python3
"""Which assistant tutors which course, on which machine.

Four layers resolve it and the order is the whole feature: the command line,
the sitting, the course's own choice, then the global default.

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
from tutorboard.runner import daemon  # noqa: E402
from tutorboard import gitsync  # noqa: E402
from tutorboard.agents import recipes  # noqa: E402
from tutorboard.runner import turn as runturn  # noqa: E402
from tutorboard.runner import watch as runwatch  # noqa: E402
from tutorboard.agents import usage  # noqa: E402

fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


CFG = {
    "default_agent": "opencode",
    "agents": {"claude": {"cmd": ["claude"]},
               "opencode": {"cmd": ["opencode"]},
               "codex": {"cmd": ["codex"]}},
}

host = recipes.this_host()

check("the command line wins over everything",
      recipes.resolve_agent(CFG, {"agent": "claude"}, "codex") == "codex")

check("a course that names its assistant beats the global default",
      recipes.resolve_agent(CFG, {"agent": "claude"}) == "claude")

check("a course with no opinion falls through to default_agent",
      recipes.resolve_agent(CFG, {}) == "opencode")

check("there is no per-machine layer: a `hosts` map is ignored",
      recipes.resolve_agent(dict(CFG, hosts={host: "codex"}), {}) == "opencode"
      and "hosts" not in recipes.DEFAULT_CONFIG)

check("an unknown name resolves to nothing rather than to a wrong agent",
      recipes.resolve_agent(CFG, {"agent": "nonesuch"}) is None)

check("a course with no opinion at all still resolves",
      recipes.resolve_agent(CFG, None) == "opencode")

# --- a provider per KIND of sitting -----------------------------------------
# `agent` in `tutorboard.json` may be an object keyed by kind: a course's learn
# sittings on DeepSeek, a project's build sittings on Claude. The open sitting's
# own kind picks the entry; a kind it does not name falls through to the default.
kinded = tempfile.mkdtemp(prefix="agents-kind-")
os.makedirs(os.path.join(kinded, "live"))


def sit(kind):
    with open(os.path.join(kinded, "live", "state.json"), "w", encoding="utf-8") as fh:
        json.dump({"thread": "t", "kind": kind} if kind else {}, fh)


by_kind = {"root": kinded, "agent": {"learn": "codex", "build": "claude"}}
sit("learn")
check("a learn sitting takes the workspace's learn provider",
      recipes.resolve_agent(CFG, by_kind) == "codex")
sit("build")
check("a build sitting takes its build provider",
      recipes.resolve_agent(CFG, by_kind) == "claude")
sit("coach")
check("a kind the workspace does not name falls through to the default",
      recipes.resolve_agent(CFG, by_kind) == "opencode")
sit(None)
check("and so does a sitting of no kind",
      recipes.resolve_agent(CFG, by_kind) == "opencode")
sit("learn")
check("the sitting's own choice still beats the workspace's kind",
      recipes.resolve_agent(CFG, by_kind, "opencode") == "opencode")
check("a misspelt provider for a kind is refused, not quietly replaced",
      recipes.resolve_agent(CFG, dict(by_kind, agent={"learn": "nonesuch"})) is None)
check("a plain name still holds for every kind",
      recipes.resolve_agent(CFG, {"root": kinded, "agent": "codex"}) == "codex")
shutil.rmtree(kinded, ignore_errors=True)

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
      recipes.missing_command(["a-command-no-machine-has"]) == "a-command-no-machine-has")
check("one that is, is not", recipes.missing_command(["sh"]) is None)
check("and a script agent runs under this interpreter, which is always here",
      recipes.missing_command([sys.executable, "anything.py"]) is None)
# CODEX WAS HALF A RECIPE: no first-turn entry, so `turn_plan` fell back to the
# resume one for a first turn and there was no resume path at all; and no
# `usage`, so every Codex turn was free in `cost.jsonl`.
codex = D["agents"]["codex"]
check("codex has a first-turn recipe and a resume recipe, and they differ",
      codex["headless_first"] != codex["headless"])
check("the resume spelling is the installed binary's own",
      codex["headless"][:4] == ["codex", "exec", "resume", "--last"])
check("and it reports what a turn cost", codex["usage"] == "codex-jsonl")
# THE SANDBOX, WHICH IS THE WHOLE OF WHETHER IT CAN TUTOR AT ALL. `codex exec`
# defaults to read-only and answers the first write with `writing is blocked by
# read-only sandbox`, so the turn reads the brief, thinks, writes no card and
# exits 0. Asserted on BOTH recipes: a resumed turn that cannot write is the
# same silent failure one turn later.
check("a codex turn may write, or it is a tutor that produces nothing and "
      "says it succeeded",
      all("--dangerously-bypass-approvals-and-sandbox" in r
          for r in (codex["headless_first"], codex["headless"])))
first, _t, fresh = runturn.turn_plan(codex, 0, 1, "")
check("so a first turn uses the first-turn recipe",
      fresh and first == codex["headless_first"])
again, _t, fresh2 = runturn.turn_plan(codex, 1, 0, "")
check("and a second resumes", not fresh2 and again == codex["headless"])

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

# A RECIPE THIS MACHINE'S CONFIG IS HOLDING DOWN, which until now nothing could
# see. `agents` merges one level deep, so a field named in `config.json` beats
# the built-in for ever: this machine's config carried a verbatim copy of the
# whole table from an older version, and its codex entry had neither the resume
# path nor the sandbox flag -- so every resumed codex turn failed silently while
# the recipe in the repository read correctly. The symptom is the tool's own
# behaviour looking wrong, which is the worst place to start looking.
_shadow_box = tempfile.mkdtemp(prefix="tutor-shadow-")
_was_config = recipes.CONFIG
recipes.CONFIG = os.path.join(_shadow_box, "config.json")
with open(recipes.CONFIG, "w", encoding="utf-8") as fh:
    json.dump({"default_agent": "claude", "agents": {
        # A field that differs: the stale copy, and the one that bit.
        "codex": {"cmd": ["codex"], "headless": ["codex", "exec", "{prompt}"]},
        # A field that agrees with the built-in: stale in the same way and
        # changes nothing today, so naming it would be noise on every run.
        "claude": {"cmd": ["claude"]},
        # An agent this machine invented: there is no built-in behind it.
        "mine": {"cmd": ["mine"], "prompt": "argv"},
    }}, fh)
_held = recipes.config_shadows()
check("a config field that overrides a built-in recipe is named, with the "
      "field, because that field is frozen at the day somebody wrote it",
      _held == {"codex": ["headless"]})
with open(recipes.CONFIG, "w", encoding="utf-8") as fh:
    json.dump({"agents": {"codex": {"replace": True, "cmd": ["codex"]}}}, fh)
check("and a recipe replaced outright is named whatever its fields say, "
      "because replacing turns the rest of it off",
      "replace" in (recipes.config_shadows().get("codex") or [""])[0])
with open(recipes.CONFIG, "w", encoding="utf-8") as fh:
    fh.write("not json at all")
check("an unreadable config shadows nothing rather than raising, because this "
      "is read on the way to reporting health", recipes.config_shadows() == {})
recipes.CONFIG = _was_config
shutil.rmtree(_shadow_box, ignore_errors=True)
check("and `board doctor` reports it off the registry rather than working it "
      "out a second time",
      'a.get("shadowed")' in open(os.path.join(ROOT, "bin", "board"),
                                  encoding="utf-8").read())

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
      recipes.choose_agent(THREE, "one") == ("one", None))

limits.mark_limited(time.time() + 900, agent="one")
name, why = recipes.choose_agent(THREE, "one")
check("a limited agent hands the turn to the next one that can take it",
      name != "one" and name in ("two", "three"))
check("and the log line says which and why, because the board paints it",
      "one" in (why or "") and name in (why or ""))

limits.mark_limited(time.time() + 900, agent=name)
second, _ = recipes.choose_agent(THREE, "one")
check("a second one hitting its own ceiling falls through to the third",
      second not in ("one", name))

for n in ("one", "two", "three"):
    limits.mark_limited(time.time() + 900, agent=n)
check("all of them limited behaves exactly as one tutor always did: the turn "
      "goes to the one we wanted and fails where that is visible",
      recipes.choose_agent(THREE, "one") == ("one", None))

limits.clear_limited()
limits.mark_limited(time.time() + 900, agent="one")
check("A FENCED RECIPE IS NEVER FALLEN INTO. It is the only assistant allowed "
      "to read phi and its cards must not reach a remote, so it is not a "
      "choice an automatic swap gets to make",
      recipes.choose_agent(dict(THREE, agents={
          "one": THREE["agents"]["one"],
          "fenced": THREE["agents"]["fenced"]}), "one") == ("one", None))
check("nor is one this machine has not got",
      recipes.choose_agent(dict(THREE, agents={
          "one": THREE["agents"]["one"],
          "ghost": THREE["agents"]["ghost"]}), "one") == ("one", None))
check("nor one whose key is not here -- that is a daemon that listens and then "
      "fails every turn into a log",
      recipes.choose_agent(dict(THREE, agents={
          "one": THREE["agents"]["one"],
          "unkeyed": THREE["agents"]["unkeyed"]}), "one") == ("one", None))

ordered = dict(THREE, fallback=["two", "three"])
check("the order is the config's where it has one",
      recipes.choose_agent(ordered, "one")[0] == "two")
check("and where it has none it is what `--agents` reports, in that order -- "
      "a list nobody has set should still do something sensible",
      recipes.choose_agent(THREE, "one")[0] == "three")

limits.clear_limited()
check("and when the allowance comes back we climb home, because the question "
      "is asked again every turn rather than answered once",
      recipes.choose_agent(THREE, "one") == ("one", None))

# --- THE ONLY-AGENT SWITCH ---------------------------------------------------
# One key, `only_agent`, and every other hosted recipe is unavailable here in
# one sentence, whatever a sitting, a workspace or `default_agent`
# asks for. The fenced reader is not a hosted provider and is not barred.
ONLY = {"default_agent": "claude", "only_agent": "deepseek",
        "agents": {"claude": dict(SH, label="Claude"),
                   "deepseek": dict(SH, label="DeepSeek"),
                   "codex": {"cmd": ["a-command-no-machine-has"],
                             "headless": ["a-command-no-machine-has"]},
                   "colibri": dict(SH, private="it reads phi")}}
POLICY = "this machine is running DeepSeek only"
_said, _why = [], []
check("a workspace naming claude lands on deepseek under the switch",
      recipes.resolve_agent(ONLY, {"agent": "claude"}, say=_said.append,
                          why=_why) == "deepseek")
check("with the policy line, naming the layer it overruled and the config line "
      "that did it",
      len(_why) == 1 and _why == _said
      and "this workspace's tutorboard.json asks for 'claude'" in _why[0]
      and POLICY in _why[0] and '"only_agent": "deepseek"' in _why[0])
check("--agent naming another is refused the same way",
      recipes.resolve_agent(ONLY, {}, "claude", say=lambda m: None) == "deepseek")
check("so is `default_agent`, which is the layer that named claude here",
      recipes.resolve_agent(ONLY, {}, say=lambda m: None) == "deepseek")
check("the fenced reader still resolves where a workspace asks for it by name",
      recipes.resolve_agent(ONLY, {"agent": "colibri"}, say=lambda m: None)
      == "colibri")
check("and the switch naming a recipe that is not here resolves to nothing",
      recipes.resolve_agent(dict(ONLY, only_agent="nonesuch"), {},
                          say=lambda m: None) is None)
check("with the switch off, claude is claude again",
      recipes.resolve_agent(dict(ONLY, only_agent=None), {"agent": "claude"})
      == "claude")

check("agent_unavailable says the switch for every other hosted recipe",
      recipes.agent_unavailable(ONLY, "claude") == POLICY)
check("before any binary or key check: a recipe that is not installed says the "
      "switch, not the missing binary",
      recipes.agent_unavailable(ONLY, "codex") == POLICY)
check("and nothing about the switch's own recipe or the fenced reader",
      recipes.agent_unavailable(ONLY, "deepseek") is None
      and recipes.agent_unavailable(ONLY, "colibri") is None)

limits.clear_limited()
_name, _why = recipes.choose_agent(ONLY, "claude")
check("choose_agent hands a barred recipe's turn to the switch, and says so",
      _name == "deepseek" and POLICY in (_why or ""))
limits.mark_limited(time.time() + 900, agent="deepseek")
check("and never crosses: the switch's recipe out of allowance keeps the turn "
      "and fails where that is visible",
      recipes.choose_agent(ONLY, "deepseek") == ("deepseek", None))
check("even when the turn was wanted by a barred recipe",
      recipes.choose_agent(ONLY, "claude")[0] == "deepseek")
limits.clear_limited()

# `tutor agent only <name>|--off` writes one key and leaves the rest alone.
_only_box = tempfile.mkdtemp(prefix="tutor-only-")
_was_config = recipes.CONFIG
recipes.CONFIG = os.path.join(_only_box, "config.json")
with open(recipes.CONFIG, "w", encoding="utf-8") as fh:
    json.dump({"default_agent": "claude", "vision_agent": "deepseek"}, fh)
_free = dict(ONLY, only_agent=None)
_rc = tutor.agent_only(_free, ["deepseek"])
with open(recipes.CONFIG, encoding="utf-8") as fh:
    _on = json.load(fh)
check("`tutor agent only deepseek` sets the key and keeps every other",
      _rc == 0 and _on == {"default_agent": "claude", "vision_agent": "deepseek",
                           "only_agent": "deepseek"})
_rc = tutor.agent_only(_free, ["--off"])
with open(recipes.CONFIG, encoding="utf-8") as fh:
    _off = json.load(fh)
check("and `--off` removes it", _rc == 0 and "only_agent" not in _off)
check("the fenced reader, an unknown name and an uninstalled recipe are refused "
      "before anything is written",
      tutor.agent_only(_free, ["colibri"]) == 1
      and tutor.agent_only(_free, ["nonesuch"]) == 1
      and tutor.agent_only(_free, ["codex"]) == 1
      and "only_agent" not in json.load(open(recipes.CONFIG, encoding="utf-8")))
check("and neither a name with --off nor nothing at all is a command",
      tutor.agent_only(_free, []) == 2
      and tutor.agent_only(_free, ["deepseek", "--off"]) == 2)
recipes.CONFIG = _was_config
shutil.rmtree(_only_box, ignore_errors=True)

# `tutor --agents --json` carries the switch, so the strip can grey the rest.
import subprocess                                             # noqa: E402
_xdg = tempfile.mkdtemp(prefix="tutor-only-xdg-")
os.makedirs(os.path.join(_xdg, "tutor-board"))
with open(os.path.join(_xdg, "tutor-board", "config.json"), "w",
          encoding="utf-8") as fh:
    json.dump({"only_agent": "deepseek"}, fh)
_p = subprocess.run([sys.executable, os.path.join(ROOT, "bin", "tutor"),
                     "--agents", "--json"],
                    env=dict(os.environ, XDG_CONFIG_HOME=_xdg),
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
try:
    _table = json.loads(_p.stdout.decode().strip().splitlines()[-1])
except (ValueError, IndexError):
    _table = {}
_rows = {a["name"]: a for a in _table.get("agents") or []}
check("--agents --json names the switch",
      (_table.get("only") or {}).get("agent") == "deepseek"
      and (_table.get("only") or {}).get("why") == POLICY)
check("and every barred recipe carries the sentence, the switch's own and the "
      "fenced reader none",
      (_rows.get("claude") or {}).get("barred") == POLICY
      and (_rows.get("claude") or {}).get("unavailable") == POLICY
      and not (_rows.get("deepseek") or {}).get("barred")
      and not (_rows.get("colibri") or {}).get("barred"))
check("and the machine's own answer is the switch's recipe",
      _table.get("machine") == "deepseek")
shutil.rmtree(_xdg, ignore_errors=True)

# A barred recipe is no vision route either: an image is a call.
from tutorboard import seeing                                 # noqa: E402
_got, _no = seeing.route("claude", {"vision_agent": "claude", "agents": [
    {"name": "claude", "barred": POLICY,
     "vision": {"cmd": ["claude"], "sighted": True}}]})
check("a barred recipe's vision route is refused, with the switch's sentence",
      _got is None and POLICY in (_no or ""))
_got, _no = seeing.route(None, {
    "vision_agent": "claude", "default": "claude",
    "only": {"agent": "deepseek", "why": POLICY},
    "agents": [{"name": "claude", "barred": POLICY,
                "vision": {"cmd": ["claude"], "sighted": True}},
               {"name": "deepseek",
                "vision": {"endpoint": "https://api.deepseek.test/v1",
                           "model": "m"}}]})
check("and the switch's own recipe is asked, so a vision_agent and default "
      "still naming claude leave an image a route",
      (_got or {}).get("agent") == "deepseek")

# --- AND IT IS ASKED EVERY TURN ----------------------------------------------
src = "".join(open(os.path.join(ROOT, "tutorboard", d, f), encoding="utf-8").read()
              for d, f in (("runner", "loop.py"), ("agents", "recipes.py")))
check("the recipe is re-bound inside the loop rather than above it",
      "cfg, next_agent, next_spec, moved = for_this_turn(" in src)
check("an unfinished report is immune: it belongs to the session that did "
      "the work",
      'signal == "unfinished"' in src
      and "belongs to the session that did the work" in src)
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


check("no record means nothing is listening", daemon.agent_live(tmp) is None)

write_agent(host="some-other-node", pid=1, agent="claude", state="listening")
check("a record from another node is not believed", daemon.agent_live(tmp) is None)

write_agent(host=host, pid=999999, agent="claude", state="listening")
check("a record for a pid that is gone is not believed", daemon.agent_live(tmp) is None)

write_agent(host=host, pid=os.getpid(), agent="claude", state="listening")
st = daemon.agent_live(tmp)
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
st = daemon.agent_live(tmp)
check("a daemon mid-turn is not declared dead for going quiet",
      bool(st) and st.get("state") == "working")

write_agent(host=host, pid=999999, agent="claude", state="working",
            last_seen=time.time())
check("but a daemon whose process is gone is not believed, heartbeat or not",
      daemon.agent_live(tmp) is None)

# Only a record with no pid at all has nothing better to go on.
write_agent(host=host, agent="claude", state="listening", last_seen=time.time() - 600)
check("a pidless record still expires on its heartbeat",
      daemon.agent_live(tmp) is None)

write_agent(host=host, pid=os.getpid(), agent="claude", state="attached",
            mode="interactive", cmd=sys.executable, last_seen=time.time() - 6000)
st = daemon.agent_live(tmp)
check("an interactive assistant idle for an hour is still attached",
      bool(st) and st.get("state") == "attached")

write_agent(host=host, pid=999999, agent="claude", state="attached",
            mode="interactive", cmd=sys.executable, last_seen=time.time())
check("but one whose process is gone is not",
      daemon.agent_live(tmp) is None)

write_agent(host=host, pid=os.getpid(), agent="claude", state="attached",
            mode="interactive", cmd="a-command-this-process-is-not")
check("and a recycled pid running something else is not either",
      daemon.agent_live(tmp) is None)

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
daemon.headless_stop({"courses_dir": box, "agents": {}}, [])
check("headless --stop leaves an interactive session alone",
      os.path.exists(os.path.join(boxed, "agent.json")))
shutil.rmtree(box, ignore_errors=True)

write_agent(host=host, pid=os.getpid(), agent="claude", state="listening")

# --- starting ----------------------------------------------------------------
course = {"root": tmp, "dir": "fake-course", "name": "Fake"}
code, msg = daemon.agent_start(CFG, course, "claude")
check("starting is a no-op while one is already listening",
      code == 0 and "already listening" in msg)

os.remove(os.path.join(live, "agent.json"))
code, msg = daemon.agent_start(CFG, course, "claude")
check("an agent with no headless recipe refuses rather than half-starting",
      code == 1 and "headless recipe" in msg)

code, msg = daemon.agent_start(CFG, course, None)
check("an unresolved agent refuses", code == 1 and "no agent resolved" in msg)

ghost = dict(CFG, agents=dict(CFG["agents"],
                              ghost={"cmd": ["a-command-no-machine-has"],
                                     "headless": ["a-command-no-machine-has", "{prompt}"]}))
code, msg = daemon.agent_start(ghost, course, "ghost")
check("an agent whose command this machine lacks refuses rather than "
      "listening and failing every turn",
      code == 1 and "not on the path" in msg)

code, msg = daemon.agent_stop(course)
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
      gitsync.sync(tempfile.mkdtemp(prefix="tutor-plain-")) is None)

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

check("a repository with no remote is left alone", gitsync.sync(here, quiet=True) is None)

git("remote", "add", "origin", up, cwd=here)
git("push", "-qu", "origin", "main", cwd=here)
git("clone", "-q", up, there)
for cfg in (("user.email", "t@t"), ("user.name", "T")):
    git("config", cfg[0], cfg[1], cwd=there)
with open(os.path.join(there, "HANDOFF.md"), "w", encoding="utf-8") as fh:
    fh.write("what the other machine taught\n")
git("commit", "-qam", "handoff from elsewhere", cwd=there)
git("push", "-q", cwd=there)

check("a session pulls what another machine pushed", gitsync.sync(here, quiet=True) is True)
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
      gitsync.sync(here, quiet=True) is False)
check("and it does not touch the local work",
      open(os.path.join(here, "HANDOFF.md"), encoding="utf-8").read().strip()
      == "locally, at the same time")

shutil.rmtree(sandbox, ignore_errors=True)

# --- restarting every board on this machine ----------------------------------
# A board read serve.py when it started, so a change to the tool reaches a course
# only when its board comes back. The pages are served from disk and look new
# while the endpoints behind them are the old ones -- invisible from outside.
import subprocess as _sp
tool_src = "".join(open(os.path.join(ROOT, "tutorboard", "runner", f),
                         encoding="utf-8").read() for f in ("watch.py", "loop.py"))
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
      runwatch.RESTART_WAIT and runwatch.RESTART_WAIT <= 60)
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
# `tutor agent ensure` is `start` that says nothing when there was nothing to
# do, and `tutor agent which` names the assistant a workspace runs.

import contextlib                                            # noqa: E402
import io as _io                                             # noqa: E402

away = tempfile.mkdtemp(prefix="tutor-away-")
away_root = os.path.join(away, "Fake-Course")
away_live = os.path.join(away_root, "live")
os.makedirs(away_live)
open(os.path.join(away_root, "AI_INSTRUCTIONS.md"), "w").close()

AWAY_CFG = {"courses_dir": away, "default_agent": "claude",
            "agents": {"claude": {"cmd": ["claude"],
                                  "headless": [sys.executable, "-c", "pass"]}}}

was_env = os.environ.pop("TUTORBOARD_COURSES", None)
started = []
real = {k: getattr(daemon, k) for k in ("agent_start",)}
daemon.agent_start = lambda cfg, c, name, session=None: (started.append(c["dir"]) or (0, "started"))


def away_agent(**kw):
    path = os.path.join(away_live, "agent.json")
    if not kw:
        if os.path.exists(path):
            os.remove(path)
        return
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(kw, fh)


try:
    away_agent(host=host, agent="claude", state="listening", pid=os.getpid())
    del started[:]
    check("ensure starts nothing when a tutor is already attached",
          tutor.cmd_agent(AWAY_CFG, ["ensure", "Fake-Course"]) == 0 and not started)

    away_agent(host=host, agent="claude", state="listening", pid=999999)
    del started[:]
    check("and starts one when the record names a process that is gone",
          tutor.cmd_agent(AWAY_CFG, ["ensure", "Fake-Course"]) == 0
          and started == ["Fake-Course"])

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
        setattr(daemon, k, v)
    if was_env is not None:
        os.environ["TUTORBOARD_COURSES"] = was_env
    shutil.rmtree(away, ignore_errors=True)

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
def wrote_failure(agent):
    with open(os.path.join(silent_live, "agent.json"), "w", encoding="utf-8") as fh:
        json.dump({"agent": agent, "state": "listening", "pid": 4321,
                   "failed_agent": agent,
                   "last_error": "API Error: Connection dropped (ECONNRESET) (exit 1)",
                   "failed_at": time.time(),
                   "handover": "2026-09-20 10:00:00"}, fh)


wrote_failure("deepseek")
woke = daemon.mark_waking(silent_live, "deepseek", pid=os.getpid())
check("a start does not erase the last turn's failure -- a daemon is most often "
      "restarted BECAUSE the turn fell over, and clearing the reason there "
      "empties the record at the one moment somebody is reading it",
      (woke.get("last_error") or "").startswith("API Error")
      and woke.get("failed_at"))
check("and it still answers the flags a start is the answer to",
      not woke.get("handover") and woke.get("state") == "waking")

# AND THE FAILURE BELONGS TO THE PROVIDER IT HAPPENED TO. The board reads the
# agent and the error out of one record and puts them in one sentence, so a
# failure kept across a swap would read as "claude's last turn failed -- cannot
# reach api.deepseek.com", about a host claude never opens.
wrote_failure("deepseek")
woke = daemon.mark_waking(silent_live, "claude", pid=os.getpid())
check("a failure does not follow the record onto the next provider: coming up "
      "as somebody else drops an error that was not theirs",
      not woke.get("last_error") and not woke.get("failed_at")
      and not woke.get("failed_agent"))
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

# THE WRAP-UP IS A TURN AND IS JUDGED LIKE ONE. The handoff used to be called
# written whenever HANDOFF.md existed -- and one always does, from the session
# before -- so a wrap-up that died on the wire logged `handoff written` and then
# re-stamped LAST session's note with the chapter this one taught.
check("the handoff believes the turn rather than the directory listing: the "
      "exit code, the result object and a file newer than the turn",
      "done = subprocess.run(cmd, cwd=root, stdout=log," in tool_src
      and "wrote = not failed and os.path.getmtime(landing) > before" in tool_src)
check("and a wrap-up that failed does not stamp a stale note with this "
      "session's chapter",
      "the handoff turn failed (%s); HANDOFF.md is " in tool_src)

# A PROVIDER THAT FAILS THE SAME WAY EVERY TURN IS NOT A LOUD FAILURE, IT IS A
# PERMANENT ONE. An allowance and a dark host both climb down; a renamed model
# reaches the board in the provider's own words and then costs a turn per
# message, for ever.
check("the same failure twice stands the recipe down and hands the lesson on",
      "egress.mark_failing(ctx.agent_name, why)" in tool_src
      and "has failed the same way twice" in tool_src)
check("and a turn that goes through takes the stand-down off again, whichever "
      "kind it was",
      "if egress.stood_down(ctx.agent_name):" in tool_src
      and "egress.clear_unreachable(ctx.agent_name)" in tool_src)
shutil.rmtree(silent, ignore_errors=True)


print("%d FAILURES" % len(fails) if fails else "the assistant follows the course")
sys.exit(1 if fails else 0)
