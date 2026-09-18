#!/usr/bin/env python3
"""The local model, reached from the iPad.

`coli-code` serves GLM-5.2 int4 to a coding client in any directory, and it was
reachable from a terminal and from nowhere else. Five things stood between it and
a thumb, and this is the suite for them.

1. THERE WAS NO `colibri` AGENT. It is a command recipe like the other five --
   nothing in `bin/tutor` knows what a model is -- and the resumed turn must
   carry `--continue`, because a fresh session on this model re-pays a
   15,900-token preamble at a few tokens a second: hours, not pennies.

2. EVERY TURN WOULD HAVE BEEN KILLED AT ONE HOUR, in the middle of its first
   prefill, and the board would have painted it as a turn that FAILED rather
   than one that was interrupted. The timeout is now a property of the agent as
   well as of the sitting.

3. NOTHING STARTED THE SERVER. Four states off `squeue`, and a control that
   returns at once because an allocation, a 429 GB load and a warm-up
   generation is seven or eight minutes on a good day.

4. A SITTING COULD NOT CHOOSE ITS ASSISTANT. Four layers resolved it and none of
   them was the sitting, so choosing the local model for one evening meant
   editing a file that is a statement about the workspace for ever -- and the
   iPad could reach none of the four.

5. AND TWO REFUSALS. The server runs one KV slot, so a second sitting anywhere
   on this machine evicts the first one's prefix and costs it its whole preamble
   again; and this is the only assistant allowed to read `phi`, so a card of its
   own must not reach a remote.
"""

import importlib.machinery
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from tutorboard import atlas, colibri                        # noqa: E402
from tutorboard.course import config                         # noqa: E402

loader = importlib.machinery.SourceFileLoader("tutor", os.path.join(ROOT, "bin", "tutor"))
tutor = importlib.util.module_from_spec(
    importlib.util.spec_from_loader("tutor", loader))
loader.exec_module(tutor)

fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


# ---------------------------------------------------------------------------
# 1. a sixth row in a table that already had five
# ---------------------------------------------------------------------------
AGENTS = tutor.DEFAULT_CONFIG["agents"]
spec = AGENTS.get("colibri") or {}

check("there is a colibri agent at all", bool(spec))
check("and it is `coli-code`, which is the whole of what the board knows about it",
      spec.get("cmd") == ["coli-code"])
check("a first turn opens a session", "coli-code" in (spec.get("headless_first") or []))
check("and a later one CONTINUES it, which is the whole cost argument here",
      "--continue" in (spec.get("headless") or [])
      and "--continue" not in (spec.get("headless_first") or []))
check("a headless turn does not stop to ask about each tool call",
      "--yes" in (spec.get("headless") or []))
check("and the prompt still reaches it",
      any("{prompt}" in a for a in spec.get("headless", [])))

# The flag the recipe depends on has to exist in the thing it drives. It did
# not: `coli-code` had no way to continue a session, and the board's whole cost
# argument rests on `headless` resuming what `headless_first` opened.
CODE = os.path.join(os.path.dirname(ROOT), "projects", "libr-local-llm",
                    "bin", "coli-code")
if not os.path.isfile(CODE):
    print("note libr-local-llm is not checked out here; skipping the client half")
else:
    src = open(CODE, encoding="utf-8").read()
    check("`coli-code` takes -c/--continue at all", "-c|--continue" in src)
    check("and passes --continue to Claude Code",
          'CLI+=(--continue)' in src)
    check("and -c to opencode, on `run`, where continuing means anything",
          'CLI+=(-c)' in src)
    check("the reason is written beside it, because it is hours and not pennies",
          "15,900" in src and "prefill" in src)
    check("and the client is syntactically sound",
          subprocess.run(["bash", "-n", CODE]).returncode == 0)

# ---------------------------------------------------------------------------
# 2. the clock
# ---------------------------------------------------------------------------
CFG = {"headless_timeout": 900, "doing_timeout": 3600,
       "default_agent": "claude", "hosts": {},
       "agents": {"claude": {"cmd": ["claude"]}, "colibri": spec}}

teach = tempfile.mkdtemp(prefix="tutor-coli-teach-")
doing = tempfile.mkdtemp(prefix="tutor-coli-doing-")
for where, st in ((teach, {"session": "lecture", "aim": "teach"}),
                  (doing, {"session": "lecture", "aim": "build"})):
    os.makedirs(os.path.join(where, "live"), exist_ok=True)
    with open(os.path.join(where, "live", "state.json"), "w", encoding="utf-8") as fh:
        json.dump(st, fh)

check("a teaching turn's clock is unchanged for a hosted agent",
      tutor.turn_timeout(CFG, teach, CFG["agents"]["claude"]) == 900)
check("and so is a doing turn's",
      tutor.turn_timeout(CFG, doing, CFG["agents"]["claude"]) == 3600)
check("a turn with no agent named at all is unchanged too",
      tutor.turn_timeout(CFG, teach) == 900)
check("a colibri teaching turn gets the recipe's number, which is hours",
      tutor.turn_timeout(CFG, teach, spec) == spec["timeout"] > 3600)
check("and the recipe is a FLOOR, so a longer sitting still wins",
      tutor.turn_timeout(dict(CFG, doing_timeout=99999), doing, spec) == 99999)
check("a recipe with nonsense in the field does not break the clock",
      tutor.turn_timeout(CFG, teach, {"timeout": "soon"}) == 900)
shutil.rmtree(teach, ignore_errors=True)
shutil.rmtree(doing, ignore_errors=True)

# ---------------------------------------------------------------------------
# 3. the four states, off squeue, with no cluster in the room
# ---------------------------------------------------------------------------
# `_run` is the one place a command is asked, so this is where a fake Slurm
# goes. The logs are real files, because the difference between `loading` and
# `warm` cannot be got from Slurm and is read out of the job's own two lines.
logs = tempfile.mkdtemp(prefix="tutor-coli-logs-")
OUT = os.path.join(logs, "colibri_serve_out.txt")
ERR = os.path.join(logs, "colibri_serve_err.txt")
open(OUT, "w").close()
open(ERR, "w").close()
os.environ["COLI_LOG_DIR"] = logs

QUEUE = {"lines": ""}
asked = []


def fake_run(args, timeout=10):
    asked.append(list(args))
    return QUEUE["lines"]


colibri._run = fake_run


def state(**kw):
    colibri.forget()
    colibri._ASKED["at"] = 0.0
    return colibri.status(**kw)


QUEUE["lines"] = ""
now = state()
check("with no job in the queue, nothing is running",
      now["state"] == "off" and "no server" in now["detail"])
check("and it is squeue that was asked, by job name, not a state file",
      any("squeue" in a[0] and colibri.JOB_NAME in a for a in asked))

QUEUE["lines"] = "4231|PENDING||Resources"
now = state()
check("a job Slurm has not run yet reads as queued", now["state"] == "queued")
check("and Slurm's own reason is what is shown, because a 950 GB ask can pend "
      "indefinitely and nothing else says why",
      now["detail"] == "Resources")
check("the job number comes back, so a person can go and look at it",
      now["job"] == "4231")

QUEUE["lines"] = "4231|RUNNING|compute304|None"
now = state()
check("running with neither sentinel yet is loading, not ready",
      now["state"] == "loading" and "429 GB" in now["detail"])
check("and it says which node, which is where the endpoint is",
      now["node"] == "compute304")

with open(ERR, "w", encoding="utf-8") as fh:
    fh.write("... API listening on 127.0.0.1:8000\n")
now = state()
check("listening is still not warm, and the difference is a factor of four",
      now["state"] == "loading" and "fifth of the steady rate" in now["detail"])

with open(OUT, "w", encoding="utf-8") as fh:
    fh.write("COLIBRI-SERVE READY 3.2 tok/s\n")
now = state()
check("and it is warm only once it has actually answered a request",
      now["state"] == "warm" and "compute304" in now["detail"])

# The engine failing to load is not a server that is coming up.
with open(OUT, "w", encoding="utf-8") as fh:
    fh.write("COLIBRI-SERVE FAILED could not open the checkpoint\n")
with open(ERR, "w", encoding="utf-8") as fh:
    fh.write("nothing\n")
now = state()
check("a job whose engine fell over is not reported as loading for ever",
      now["state"] == "off" and "failed to load" in now["detail"])

# The cache, because the board polls four times a second.
QUEUE["lines"] = ""
del asked[:]
colibri.forget()
colibri.status()
first = len(asked)
for _ in range(20):
    colibri.status()
check("twenty polls ask Slurm once", len(asked) == first)
check("and the window is the one the rest of the board uses", colibri.TTL == 15.0)

# A start that has been asked for but is not yet in the queue still says so:
# sbatch takes about a second, and "nothing is running" reported back to
# somebody who has just tapped start is how a second tap happens.
colibri.submitted()
check("a submit in flight reads as queued rather than as nothing",
      colibri.status()["state"] == "queued")
colibri._ASKED["at"] = time.time() - colibri.SUBMIT_GRACE - 1
colibri.forget()
check("and a submit that never appeared does not claim to be queued for ever",
      colibri.status()["state"] == "off")

# And the control refuses rather than submitting a second job.
from tutorboard.server import spawn                          # noqa: E402

QUEUE["lines"] = "4231|PENDING||Priority"
colibri.forget()
colibri._ASKED["at"] = 0.0
started, said = spawn.wake_colibri()
check("with a job already queued, the control does not submit a second",
      started is False and "Priority" in said)
QUEUE["lines"] = "4231|RUNNING|compute304|None"
with open(OUT, "w", encoding="utf-8") as fh:
    fh.write("COLIBRI-SERVE READY\n")
colibri.forget()
started, said = spawn.wake_colibri()
check("and does nothing at all against a warm one", started is False)

# ---------------------------------------------------------------------------
# 3b. the chain, which is what makes the server always up
#
# A generation two hours from its walltime submits the next one; that one pins
# 406.7 GB on another node while this one goes on answering; and only once it
# says LOADED does this one give its node back. So squeue lists TWO generations
# for an hour at a time and the board has to say which is which.
# ---------------------------------------------------------------------------
def gen(job, out="", err=""):
    """One generation's pair of logs, under the names the chain writes."""
    with open(os.path.join(logs, "colibri_serve_out-%s.txt" % job), "w") as fh:
        fh.write(out)
    with open(os.path.join(logs, "colibri_serve_err-%s.txt" % job), "w") as fh:
        fh.write(err)


# The fixed names are left saying FAILED on purpose: nothing below may read them.
with open(OUT, "w", encoding="utf-8") as fh:
    fh.write("COLIBRI-SERVE FAILED from a job that ended days ago\n")
with open(ERR, "w", encoding="utf-8") as fh:
    fh.write("nothing\n")

gen("5001", out="COLIBRI-SERVE READY\n", err="API listening on 127.0.0.1:8000\n")
QUEUE["lines"] = "5001|RUNNING|compute301|None|8:00:00"
now = state()
check("a generation is judged by ITS OWN log, not by a pair of fixed names a "
      "dead job left behind",
      now["state"] == "warm" and now["job"] == "5001")

# The hour of overlap: one warm, one still reading off the filer.
gen("5002")
QUEUE["lines"] = ("5001|RUNNING|compute301|None|1:30:00\n"
                  "5002|RUNNING|compute305|None|8:55:00")
now = state()
check("with two generations running, the one that can ANSWER is the one reported",
      now["state"] == "warm" and now["job"] == "5001")
check("and the other is named as the one behind it", now["next"] == "5002")
check("which is the fact the chain adds and the only one worth painting: the "
      "server is going somewhere",
      "next generation is loading on compute305" in now["detail"])

gen("5002", out="COLIBRI-SERVE LOADED host=compute305 port=8000\n")
now = state()
check("a successor that has finished pinning says so, because that is the moment "
      "the incumbent gives its node back",
      "loaded on compute305" in now["detail"] and "moment" in now["detail"])

# Both warm, which is the second the handover has not quite happened in.
gen("5002", out="COLIBRI-SERVE LOADED\nCOLIBRI-SERVE READY\n")
now = state()
check("between two warm generations the one with more walltime left wins, "
      "because that is the one that is not about to hand over",
      now["job"] == "5002" and now["next"] == "5001")

# A queued successor is a different sentence from a loading one.
QUEUE["lines"] = ("5001|RUNNING|compute301|None|1:30:00\n"
                  "5003|PENDING||Resources|9:00:00")
now = state()
check("a successor Slurm has not run yet reads as queued, not as loading",
      now["job"] == "5001" and "next generation is queued" in now["detail"])

check("and nothing about the four states moved: the chain is a clause, not a "
      "fifth state",
      now["state"] == "warm")

del os.environ["COLI_LOG_DIR"]
shutil.rmtree(logs, ignore_errors=True)

# ---------------------------------------------------------------------------
# 3c. the chain's own half, which is four shell files and no cluster
#
# The board can only report what the job writes, so the rules that make the
# handover gapless live over there. These are the four that cannot be read off
# `squeue` afterwards and would cost a day each to rediscover.
# ---------------------------------------------------------------------------
LLM = os.path.join(os.path.dirname(ROOT), "projects", "libr-local-llm")
SBATCH = os.path.join(LLM, "slurm_jobs", "colibri_serve.sbatch")
if not os.path.isfile(SBATCH):
    print("note libr-local-llm is not checked out here; skipping the chain's half")
else:
    job = open(SBATCH, encoding="utf-8").read()
    env = open(os.path.join(LLM, "scripts", "colibri-env.sh"), encoding="utf-8").read()

    def code(text):
        """The file with its comments taken out.

        These two files argue with themselves in prose -- the sbatch says at
        length why it is NOT `--dependency=afterany`, which is the board's own
        chain -- so a check for a flag has to read what runs rather than what is
        written about it.
        """
        return "\n".join(l for l in text.splitlines()
                          if not l.lstrip().startswith("#"))
    up = open(os.path.join(LLM, "bin", "coli-up"), encoding="utf-8").read()
    down = open(os.path.join(LLM, "bin", "coli-down"), encoding="utf-8").read()

    check("a successor OVERLAPS its incumbent rather than following it: there is "
          "no dependency anywhere in the chain, because a load that begins at the "
          "handover is an hour with no server",
          "--dependency" not in code(job) and "--dependency" not in code(env))
    check("and it is told to land somewhere else, because two 950 GB jobs do not "
          "fit on a 1 TB box",
          '--exclude="$MY_NODE"' in job)
    check("the incumbent gives its node back only once the successor has LOADED, "
          "which is the whole of what makes the handover gapless",
          "COLIBRI-SERVE LOADED" in job and 'scancel "$MY_JOB"' in job)
    check("the successor holds its WARM-UP until the incumbent has gone, because "
          "a warm-up is a real write and .coli_kv is one file per checkpoint",
          "coli_elders" in job and "HOLDING" in job)
    check("the fence still comes first and is still unskippable",
          job.index("COLI_DEBUG") < job.index("coli_load_modules"))
    check("every generation writes its own pair of logs",
          "colibri_serve_out-%j.txt" in job and "colibri_serve_out.txt" not in job)
    check("a generation is submitted in exactly one place, so a successor cannot "
          "quietly get different resources from the first one",
          "sbatch --parsable" in env and "sbatch --parsable" not in up)
    check("`coli-down` writes the flag BEFORE it cancels, because cancelling a "
          "generation on its own is how you replace a server rather than stop one",
          down.index("coli_mark_stopped") < down.index("scancel"))
    check("and a generation that starts after that flag stands down rather than "
          "serving", "coli_chain_stopped" in job)
    check("`coli-up` no longer tells somebody to tear the chain down to start it",
          "coli-down' first" not in up)
    for name in ("slurm_jobs/colibri_serve.sbatch", "scripts/colibri-env.sh",
                 "bin/coli-up", "bin/coli-down", "bin/coli", "bin/coli-ask"):
        check("%s is syntactically sound" % name,
              subprocess.run(["bash", "-n", os.path.join(LLM, name)]).returncode == 0)

# ---------------------------------------------------------------------------
# 4. the fifth layer, which is the sitting
# ---------------------------------------------------------------------------
tree = tempfile.mkdtemp(prefix="tutor-coli-tree-")
work = os.path.join(tree, "projects", "Harness")
live = os.path.join(work, "live")
os.makedirs(live)
open(os.path.join(work, "AI_INSTRUCTIONS.md"), "w").close()

R = {"default_agent": "claude", "hosts": {},
     "agents": {"claude": {"cmd": ["claude"]}, "codex": {"cmd": ["codex"]},
                "colibri": spec}}
course = {"root": work, "dir": "Harness", "name": "Harness"}


def sitting(**kw):
    with open(os.path.join(live, "state.json"), "w", encoding="utf-8") as fh:
        json.dump(kw, fh)


sitting(session="lecture")
check("a sitting that names no assistant resolves exactly as it always did",
      tutor.resolve_agent(R, course) == "claude")

sitting(session="lecture", agent="colibri")
check("a sitting that names one beats the machine default",
      tutor.resolve_agent(R, course) == "colibri")
check("and it beats the workspace's own answer, because a choice made for an "
      "evening is not a statement about the repository",
      tutor.resolve_agent(R, dict(course, agent="codex")) == "colibri")
check("the command line still beats the sitting",
      tutor.resolve_agent(R, course, "codex") == "codex")

sitting(session="lecture", agent="nonesuch")
said = []
check("a sitting asking for an assistant this machine has not got FALLS BACK "
      "rather than leaving the course with no tutor at all",
      tutor.resolve_agent(R, course, say=said.append) == "claude")
check("and says so, once, where somebody can see it",
      any("nonesuch" in m for m in said))
# The other layers still refuse, and must: a workspace naming an agent in
# writing is a decision, and quietly using a different one would be worse.
sitting(session="lecture")
check("a WORKSPACE naming an agent that does not exist still refuses",
      tutor.resolve_agent(R, dict(course, agent="nonesuch"),
                          say=lambda m: None) is None)

check("the name is validated as a name and nothing else, because the registry "
      "is in the launcher",
      config.clean_agent("Colibri") == "colibri"
      and config.clean_agent("../../etc/passwd") is None
      and config.clean_agent("") is None)
sitting(session="lecture", agent="../../etc/passwd")
check("so a path that reached state.json somehow is not read as an assistant",
      config.sitting_agent(work) is None)
check("and a workspace with no sitting at all answers None rather than raising",
      config.sitting_agent(os.path.join(tree, "nothing", "here")) is None
      and config.sitting_agent(None) is None)

# ---------------------------------------------------------------------------
# 5. the two refusals
# ---------------------------------------------------------------------------
check("the recipe says WHY it is one at a time, so the reason travels with it",
      "KV slot" in (spec.get("exclusive") or ""))
check("and why its cards must not be committed",
      "phi" in (spec.get("private") or ""))

# AND THAT `private` IS WHAT NAMES THE READER OF A FENCE, which is the half the
# board leans on. A workspace holding a fenced directory says so on both
# choosers and names the one assistant that may open it -- and it names it by
# looking for the recipe carrying `private`, because the alternative is the name
# `colibri` written into a browser, where it would go out of step with this
# table the first time either moved. Exactly one recipe may carry it: two would
# make "the one assistant" a list, and the board would take whichever sorted
# first.
carries = [n for n, sp in AGENTS.items() if sp.get("private")]
check("exactly one recipe in the table says it may read a fence, so naming it "
      "is a lookup rather than a second list: " + ", ".join(carries),
      carries == ["colibri"])
listed = json.loads(subprocess.run(
    [sys.executable, os.path.join(ROOT, "bin", "tutor"), "--agents", "--json"],
    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
    ).stdout.decode("utf-8", "replace").strip().splitlines()[-1])
check("and it reaches the browser, which is where the chooser reads it",
      [a["name"] for a in listed["agents"] if a.get("private")] == ["colibri"])
check("beside whether this machine has it at all, because an assistant that "
      "is not installed here cannot be the answer either",
      all("missing" in a for a in listed["agents"]))

os.environ["TUTORBOARD_COURSES"] = tree
atlas.forget()
other = os.path.join(tree, "projects", "Elsewhere")
os.makedirs(os.path.join(other, "live"))
open(os.path.join(other, "AI_INSTRUCTIONS.md"), "w").close()
with open(os.path.join(tree, "atlas.json"), "w", encoding="utf-8") as fh:
    json.dump({"families": [{"id": "projects", "name": "Projects"}]}, fh)
RT = dict(R, courses_dir=tree)

with open(os.path.join(other, "live", "agent.json"), "w", encoding="utf-8") as fh:
    json.dump({"host": tutor.this_host(), "agent": "colibri",
               "state": "working", "pid": os.getpid(),
               "last_seen": time.time()}, fh)
check("a colibri sitting already running somewhere else is found",
      tutor.agent_held_elsewhere(RT, course, "colibri") == "Elsewhere")
code, msg = tutor.agent_start(RT, course, "colibri")
check("and a second one is refused by name, saying which workspace holds it",
      code == 1 and "Elsewhere" in msg)
check("and saying why, in the recipe's own words", "KV slot" in msg)
check("nothing was written on the way to refusing",
      not os.path.exists(os.path.join(live, "agent.json")))

# A hosted agent is not affected by any of it.
code, msg = tutor.agent_start(RT, course, "claude")
check("and the refusal is the recipe's, not the file's: a hosted agent opens "
      "beside it",
      code != 1 or "KV slot" not in msg)

# The one on the other node is the case this has to catch: what is protected is
# a server on one machine, and the sitting that would evict it may be anywhere.
with open(os.path.join(other, "live", "agent.json"), "w", encoding="utf-8") as fh:
    json.dump({"host": "compute999", "agent": "colibri", "state": "working",
               "pid": 4021421, "last_seen": time.time()}, fh)
check("a colibri sitting listening on ANOTHER node is found too, off the "
      "heartbeat, because the pid over there names a process table this "
      "machine cannot read",
      tutor.agent_held_elsewhere(RT, course, "colibri") == "Elsewhere")
with open(os.path.join(other, "live", "agent.json"), "w", encoding="utf-8") as fh:
    json.dump({"host": "compute999", "agent": "colibri", "state": "working",
               "pid": 4021421, "last_seen": time.time() - 100000}, fh)
check("and one that stopped beating over there is not holding anything",
      tutor.agent_held_elsewhere(RT, course, "colibri") is None)
os.remove(os.path.join(other, "live", "agent.json"))

# And the cards. `git check-ignore` rather than a list of workspaces: the answer
# is written down in the repository that decides it.
git_tree = tempfile.mkdtemp(prefix="tutor-coli-git-")
tracked = os.path.join(git_tree, "Course")
os.makedirs(os.path.join(tracked, "live", "cards"))
open(os.path.join(tracked, "AI_INSTRUCTIONS.md"), "w").close()
subprocess.run(["git", "init", "-q", tracked], stdout=subprocess.DEVNULL)
check("a workspace whose live/ is committed says so",
      tutor.cards_are_tracked(tracked))
with open(os.path.join(tracked, ".gitignore"), "w", encoding="utf-8") as fh:
    fh.write("live/*\n!live/map.json\n")
check("and one that ignores live/ -- which is what the workspace holding `phi` "
      "does -- says so too",
      not tutor.cards_are_tracked(tracked))
check("a directory that is not a repository at all refuses nobody",
      not tutor.cards_are_tracked(git_tree + "-nothing"))

with open(os.path.join(tracked, ".gitignore"), "w", encoding="utf-8") as fh:
    fh.write("# nothing\n")
GT = dict(R, courses_dir=git_tree)
code, msg = tutor.agent_start(GT, {"root": tracked, "dir": "Course",
                                   "name": "Course"}, "colibri")
check("so a colibri sitting refuses to open where its card would be pushed",
      code == 1 and "committed" in msg)
check("and names the one line that changes it, rather than leaving it to be "
      "guessed at",
      ".gitignore" in msg)
code, msg = tutor.agent_start(GT, {"root": tracked, "dir": "Course",
                                   "name": "Course"}, "claude")
check("while a hosted assistant opens there as it always has",
      "committed" not in msg)
shutil.rmtree(git_tree, ignore_errors=True)
shutil.rmtree(tree, ignore_errors=True)
os.environ.pop("TUTORBOARD_COURSES", None)
atlas.forget()

print("%d FAILURES" % len(fails) if fails
      else "the local model is one tap away, and it refuses the two taps it should")
sys.exit(1 if fails else 0)
