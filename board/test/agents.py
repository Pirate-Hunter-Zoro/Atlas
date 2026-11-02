#!/usr/bin/env python3
"""The one assistant: DeepSeek through OpenCode.

`recipes.spec()` is the recipe every turn runs and `recipes.ready()` says why
it cannot run here now (no opencode, no key, a spent allowance). config.json
carries timeouts; it does not choose an assistant, so `provider`, `fallback`,
`vision_agent` and `agents` in it are read by nothing.

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
# A state directory of our own: the readiness section below writes limit
# records, and writing the real one would take this machine out of service.
os.environ.setdefault("BOARD_STATE_DIR", tempfile.mkdtemp(prefix="agents-state-"))
os.environ.setdefault("BOARD_NO_TAILNET", "1")
from tutorboard import keys, limits, paths                    # noqa: E402

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


host = recipes.this_host()

# --- the recipe ---------------------------------------------------------------
D = recipes.DEEPSEEK
check("every turn is a fresh `opencode run` on deepseek-flash",
      D["headless_first"][:4] == ["opencode", "--pure", "run", "--auto"]
      and D["headless_first"][D["headless_first"].index("-m") + 1]
      == "deepseek/deepseek-flash")
check("and it prints JSON events, which is what `usage` reads",
      D["headless_first"][D["headless_first"].index("--format") + 1] == "json")
check("with the prompt last, as the one positional",
      D["headless_first"][-1] == "{prompt}")
check("no resume form: every session's turn runs in the Atlas root, so a "
      "resume would pick up another session's",
      "--continue" not in D["headless_first"] and "headless" not in D)
check("the key rides in the environment, never argv",
      D["env"]["DEEPSEEK_API_KEY"] == "{DEEPSEEK_API_KEY}"
      and not any("DEEPSEEK_API_KEY}" in a for a in D["headless_first"]))
check("the turn recipe carries no permissions list",
      "acceptEdits" not in " ".join(D["headless_first"])
      and "allowedTools" not in " ".join(D["headless_first"]))
check("and it has a price table, so no turn claims to cost nothing",
      D["prices"]["peak"]["out"] > 0 and D["prices"]["off"]["out"] > 0)
check("the prompt is filled in place, and nothing else changes",
      recipes.argv("hello")[-1] == "hello"
      and recipes.argv("hello")[:-1] == D["headless_first"][:-1])

_was_bin = os.environ.pop("TUTORBOARD_OPENCODE", None)
os.environ["TUTORBOARD_OPENCODE"] = "/some/other/opencode"
check("TUTORBOARD_OPENCODE names another binary, and only the binary",
      recipes.spec()["headless_first"][0] == "/some/other/opencode"
      and recipes.spec()["headless_first"][1:] == D["headless_first"][1:]
      and D["headless_first"][0] == "opencode")
check("spec() is a copy, so a caller cannot change the next turn's recipe",
      recipes.spec() is not recipes.spec()
      and recipes.spec()["env"] is not D["env"])

check("the multi-provider machinery is gone",
      not any(hasattr(recipes, n) for n in (
          "provider", "fallbacks", "fallback", "chain", "resolve",
          "unavailable", "listing", "agent_label", "provider_probe_urls",
          "resolve_agent", "choose_agent", "only_agent")))
from tutorboard.course import config as _course_config        # noqa: E402
from tutorboard.net import egress as _egress                  # noqa: E402
check("a workspace's `agent` key and the sitting's are read by nothing",
      not hasattr(_course_config, "workspace_agent")
      and not hasattr(_course_config, "sitting_agent")
      and not hasattr(recipes, "read_course"))
check("and the strike stand-down is gone", not hasattr(_egress, "mark_failing"))

# --- ready(): the three reasons a turn cannot run ----------------------------
_box = tempfile.mkdtemp(prefix="tutor-ready-")
paths.KEYS = os.path.join(_box, "keys.env")
os.environ.pop("DEEPSEEK_API_KEY", None)  # it comes before both files
paths.DEEPSEEK_KEY = os.path.join(_box, "api-keys", "deepseek_key")
keys.forget()
os.environ["TUTORBOARD_OPENCODE"] = "a-command-no-machine-has"
check("no opencode is said by name",
      "a-command-no-machine-has" in (recipes.ready() or ""))
os.environ["TUTORBOARD_OPENCODE"] = "sh"
check("no key is said, with both places it is looked for",
      paths.KEYS in (recipes.ready() or "")
      and paths.DEEPSEEK_KEY in (recipes.ready() or ""))
os.makedirs(os.path.dirname(paths.DEEPSEEK_KEY))
with open(paths.DEEPSEEK_KEY, "w") as fh:
    fh.write("sk-from-the-shared-file\n")
os.chmod(paths.DEEPSEEK_KEY, 0o600)
keys.forget()
check("the shared deepseek_key file is a key when keys.env has none",
      recipes.ready() is None
      and keys.get("DEEPSEEK_API_KEY") == "sk-from-the-shared-file")
with open(paths.KEYS, "w") as fh:
    fh.write("DEEPSEEK_API_KEY=sk-from-keys-env\n")
os.chmod(paths.KEYS, 0o600)
keys.forget()
check("and keys.env wins over it",
      keys.get("DEEPSEEK_API_KEY") == "sk-from-keys-env")
limits.LIMIT_RECORD = os.path.join(os.environ["BOARD_STATE_DIR"], "limited.json")
limits.mark_limited(time.time() + 900)
check("a spent allowance is a reason, with the time it comes back",
      "allowance" in (recipes.ready() or ""))
limits.clear_limited()
check("and when it comes back the turn can run again, because the question "
      "is asked every turn", recipes.ready() is None)
os.environ.pop("TUTORBOARD_OPENCODE", None)
if _was_bin is not None:
    os.environ["TUTORBOARD_OPENCODE"] = _was_bin
shutil.rmtree(_box, ignore_errors=True)

# --- config.json chooses nothing ---------------------------------------------
_cfg_box = tempfile.mkdtemp(prefix="tutor-cfg-")
_was_config = recipes.CONFIG
recipes.CONFIG = os.path.join(_cfg_box, "config.json")
check("a missing config is the defaults, and nothing is written",
      recipes.load_config()["headless_timeout"] == 900
      and not os.path.exists(recipes.CONFIG))
with open(recipes.CONFIG, "w", encoding="utf-8") as fh:
    json.dump({"provider": "codex", "fallback": "claude", "vision_agent": "claude",
               "default_agent": "x", "only_agent": "x",
               "agents": {"claude": {"cmd": ["claude"]}},
               "headless_timeout": 120}, fh)
_loaded = recipes.load_config()
check("provider, fallback, vision_agent, agents and the older keys are "
      "ignored", not any(k in _loaded for k in recipes.IGNORED))
check("and the rest of the file is read", _loaded["headless_timeout"] == 120)
recipes.CONFIG = _was_config
shutil.rmtree(_cfg_box, ignore_errors=True)

# --- where a headless tutor's permissions are NOT written --------------------
# A turn has nobody to approve a tool call. `opencode run --auto` allows
# whatever the recipe's `permission` block does not deny, so the board writes
# no assistant's settings file into any repository it touches.
board_src = open(os.path.join(ROOT, "bin", "board"), encoding="utf-8").read()
check("the board does not write any assistant's settings file",
      "install_permissions" not in board_src)
check("and names no vendor's config directory as something it creates",
      'os.path.join(live.root, ".claude")' not in board_src)
check("and the note says how a turn is allowed what it does",
      "opencode run --auto" in board_src)
check("skills are denied inside a turn, which carries its own brief",
      json.loads(D["env"]["OPENCODE_CONFIG_CONTENT"])["permission"]
      == {"skill": "deny"})

# A TURN IS HANDED NOTHING ON STDIN: a client that reads stdin whenever it is
# not a terminal would otherwise sit there until its cap. `cat` is the
# faithful stand-in: it returns only when stdin is at end of file.
_stdin_log = tempfile.NamedTemporaryFile(prefix="tutor-stdin-", delete=False)
_stdin_log.close()
with open(_stdin_log.name, "w") as _fh:
    _rc, _capped = runturn.run_turn(["cat"], tempfile.gettempdir(), _fh, 10)
check("a turn whose client reads stdin comes straight back rather than "
      "waiting out its whole timeout on a pipe nobody is typing into",
      _rc == 0 and not _capped)
os.unlink(_stdin_log.name)
check("and the old launcher, which printed the table as --agents, is gone",
      not os.path.exists(os.path.join(ROOT, "bin", "tutor")))

# --- AND IT IS ASKED EVERY TURN ----------------------------------------------
src = open(os.path.join(ROOT, "tutorboard", "runner", "loop.py"),
           encoding="utf-8").read()
check("the recipe and readiness are read inside the turn rather than above it",
      "ctx.cfg, ctx.spec = recipes.load_config(), recipes.spec()" in src
      and "why = recipes.ready()" in src)
check("and nothing in a turn chooses another assistant",
      "TUTORBOARD_FALLBACK" not in src and "agent_why" not in src)

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

write_agent(host="some-other-node", pid=1, agent="deepseek", state="listening")
check("a record from another node is not believed", not attached())

write_agent(host=host, pid=999999, agent="deepseek", state="listening")
check("a record for a pid that is gone is not believed", not attached())

write_agent(host=host, pid=os.getpid(), agent="deepseek", state="listening")
check("a record for a live process on this node is believed", attached())

# The runner writes its own pid, and a process either exists or it does not:
# a turn that goes quiet for ten minutes is still working.
write_agent(host=host, pid=os.getpid(), agent="deepseek", state="working",
            last_seen=time.time() - 600)
check("a turn in flight is not declared dead for going quiet", attached())

write_agent(host=host, pid=999999, agent="deepseek", state="working",
            last_seen=time.time())
check("but a record whose process is gone is not believed, heartbeat or not",
      not attached())

# Only a record with no pid at all has nothing better to go on.
write_agent(host=host, agent="deepseek", state="listening", last_seen=time.time() - 600)
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
# A turn fails, no card is written, and the board must not go back to
# `deepseek listening` with `last_error: null` -- the student's working is in
# and the chrome would say everything is fine.

silent = tempfile.mkdtemp(prefix="tutor-silent-")
silent_live = os.path.join(silent, "live")
os.makedirs(silent_live)

# WHAT RETIRES IT IS SOMETHING NEWER, AND A TURN STARTING IS NOT THAT. A turn
# that has begun settles nothing about the failure before it: a daemon killed
# mid-turn would leave `working`, no error and no card -- the empty record, one
# state along.
check("a turn that goes through is what clears it, and the daemon still does that",
      'agent_state(live, state="listening", last_error=None,\n'
      '                           failed_at=0, retrying=False)'
      in tool_src)
check("and the turn that merely STARTS does not, which is what the docstring "
      "above says happens",
      'agent_state(live, state="working", turns=ctx.turns,\n'
      '                       turn_started=time.time(), turn_signal=this_signal)'
      in tool_src)
check("what stops the board painting last time's failure over a turn in flight "
      "is the reader, which does not report one older than the running turn",
      'if st.get("state") == "working":' in
      open(os.path.join(ROOT, "tutorboard", "lesson", "state.py"),
           encoding="utf-8").read())

# AND WHAT THE BOARD IS TOLD IS THE TURN'S OWN SENTENCE rather than the
# number, which is the same for every cause: OpenCode prints a DeepSeek error
# only as a JSON `error` event.
blob = ('{"type":"error","sessionID":"s","error":{"name":"APIError",'
        '"data":{"message":"Insufficient Balance"}}}')
check("an OpenCode error event is the reason the board is told",
      usage.failure_reason("some output\n" + blob, "exit 1")
      == "Insufficient Balance (exit 1)")
check("and with no event the exit code is the reason, never an empty banner",
      usage.failure_reason("", "exit 1") == "exit 1")

# THE WRAP-UP IS A TURN AND IS JUDGED LIKE ONE. TUTOR.md always exists, from
# the turns before, so a wrap-up that died on the wire must not be logged as
# having written it.
check("the wrap-up believes the turn rather than the directory listing: the "
      "exit code and a file newer than the turn",
      "rc, timed_out = turn.run_turn(" in tool_src.split("def wrap_up(")[1]
      and "wrote = not failed and os.path.getmtime(landing) > before" in tool_src)
check("and a wrap-up that failed says TUTOR.md is what the last turn left",
      "the wrap-up turn failed (%s); TUTOR.md is " in tool_src)

# NO STRIKE STAND-DOWN: a turn failing the same way twice is reported in
# DeepSeek's own words and stands nothing down; `ready`'s reasons are a
# missing binary, a missing key and a usage limit.
check("a repeated failure stands nothing down",
      "mark_failing" not in tool_src and "striking" not in tool_src)
shutil.rmtree(silent, ignore_errors=True)


print("%d FAILURES" % len(fails) if fails else "DeepSeek through OpenCode, and nothing chooses another")
sys.exit(1 if fails else 0)
