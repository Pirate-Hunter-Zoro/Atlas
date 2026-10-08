#!/usr/bin/env python3
"""Colibri on demand: the task queue, the self-clone, the idle exit, the cap.

No cluster and no model. A fake `squeue` and `sbatch` read and write one JSON
file standing for Slurm's queue, and `end()` below plays Slurm ending a job:
it drops the job, and releases or drops every clone waiting on it the way
`--dependency=afternotok` with `--kill-on-invalid-dep=yes` does. `sacct` is
refused on the real cluster, so a clean exit is told from a death only by the
exit file a generation writes as its last act -- which is what is tested.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ATLAS = os.path.dirname(ROOT)
ENV_SH = os.path.join(ATLAS, "projects", "libr-local-llm", "scripts",
                      "colibri-env.sh")
sys.path.insert(0, ROOT)

from tutorboard import colibri, jobs, relay                   # noqa: E402

fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


TMP = tempfile.mkdtemp(prefix="ondemand-")
BIN = os.path.join(TMP, "bin")
QUEUE = os.path.join(TMP, "libr-local-llm")
STATE = os.path.join(QUEUE, "slurm_jobs", "state")
LOGS = os.path.join(QUEUE, "slurm_jobs", "logs")
WS = os.path.join(TMP, "TRD-EHR")
SLURM = os.path.join(TMP, "slurm.json")
for d in (BIN, STATE, LOGS, WS):
    os.makedirs(d)

FAKE_SQUEUE = r'''#!/usr/bin/env python3
import json, sys
a = sys.argv[1:]
fmt = a[a.index("-o") + 1] if "-o" in a else "%i %T"
only = a[a.index("-j") + 1] if "-j" in a else None
with open(SLURM) as fh:
    q = json.load(fh)
for j in q["jobs"]:
    if only and j["id"] != only:
        continue
    reason = "(Dependency)" if j.get("dep") else "None"
    line = (fmt.replace("%i", j["id"]).replace("%T", j["state"])
               .replace("%N", j.get("node", "")).replace("%r", reason)
               .replace("%L", "8:00:00"))
    print(line)
'''.replace("SLURM", repr(SLURM))

FAKE_SBATCH = r'''#!/usr/bin/env python3
import json, sys
with open(SLURM) as fh:
    q = json.load(fh)
q["next"] += 1
jid = str(q["next"])
dep = ""
for x in sys.argv[1:]:
    if x.startswith("--dependency="):
        dep = x.split("=", 1)[1]
q["jobs"].append({"id": jid, "state": "PENDING", "dep": dep,
                  "kill": "--kill-on-invalid-dep=yes" in sys.argv})
q["argv"].append(sys.argv[1:])
with open(SLURM, "w") as fh:
    json.dump(q, fh)
print(jid)
'''.replace("SLURM", repr(SLURM))

for name, body in (("squeue", FAKE_SQUEUE), ("sbatch", FAKE_SBATCH)):
    with open(os.path.join(BIN, name), "w") as fh:
        fh.write(body)
    os.chmod(os.path.join(BIN, name), 0o755)

os.environ["PATH"] = BIN + os.pathsep + os.environ["PATH"]
os.environ["COLI_QUEUE_ROOT"] = QUEUE
os.environ["COLI_STATE_DIR"] = STATE
os.environ["COLI_LOG_DIR"] = LOGS
os.environ["USER"] = os.environ.get("USER") or "tester"

# The workspaces a task names, without walking the real repository.
_PLACES = {"projects/TRD-EHR": WS, "TRD-EHR": WS}
colibri.atlas.find = lambda ident, base=None: (
    {"root": _PLACES[ident], "id": "projects/TRD-EHR"} if ident in _PLACES
    else None)
colibri.atlas.identify = lambda path: "projects/TRD-EHR"


def slurm():
    with open(SLURM) as fh:
        return json.load(fh)


def reset():
    with open(SLURM, "w") as fh:
        json.dump({"next": 100, "jobs": [], "argv": []}, fh)
    for d in (STATE, os.path.join(QUEUE, "live"),
              os.path.join(QUEUE, "relay")):
        shutil.rmtree(d, ignore_errors=True)
    os.makedirs(STATE)
    colibri.forget()


def put(jid, state="RUNNING", dep=""):
    q = slurm()
    q["jobs"].append({"id": jid, "state": state, "dep": dep, "kill": True})
    with open(SLURM, "w") as fh:
        json.dump(q, fh)


def end(jid, code=None):
    """Slurm ends `jid`. `code` is what the job wrote as its last act; None is a
    death, which writes nothing. Clones waiting on it are released or dropped."""
    if code is not None:
        colibri.mark_exit(jid, code)
    q = slurm()
    keep = []
    for j in q["jobs"]:
        if j["id"] == jid:
            continue
        if j.get("dep") == "afternotok:" + jid:
            if code == 0 and j.get("kill"):
                continue                    # never satisfiable: dropped
            j["dep"], j["state"] = "", "RUNNING"
        keep.append(j)
    q["jobs"] = keep
    with open(SLURM, "w") as fh:
        json.dump(q, fh)


def submitter(calls, list_it=True):
    """A `start` for `colibri.file`: one generation, counted."""
    def start():
        calls.append(1)
        q = slurm()
        q["next"] += 1
        jid = str(q["next"])
        if list_it:
            q["jobs"].append({"id": jid, "state": "PENDING", "dep": ""})
        with open(SLURM, "w") as fh:
            json.dump(q, fh)
        return jid, "generation %s submitted" % jid
    return start


def sh(script):
    """Run bash with colibri-env.sh sourced against the temp tree."""
    env = dict(os.environ, LLM_REPO=QUEUE)
    return subprocess.run(["bash", "-c", ". %s; %s" % (ENV_SH, script)],
                          env=env, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, universal_newlines=True)


# ---------------------------------------------------------------------------
# 1. the self-clone, as colibri-env.sh submits it
# ---------------------------------------------------------------------------
reset()
p = sh("coli_submit_clone 100")
argv = (slurm()["argv"] or [[]])[-1]
check("a clone is submitted and its id printed", p.stdout.strip() == "101")
check("it waits on its parent ending NOT ok",
      "--dependency=afternotok:100" in argv)
check("and Slurm drops it if that can never happen",
      "--kill-on-invalid-dep=yes" in argv)
check("it carries one more death in its lineage than its parent",
      any("COLI_LINEAGE=1" in x for x in argv))
check("an on-demand generation is the default and the chain is off",
      any("COLI_DEMAND=1" in x and "COLI_CHAIN=0" in x for x in argv))

reset()
put("200")
put("201", "PENDING", "afternotok:200")
put("202")
open(os.path.join(STATE, "closing-202"), "w").close()
live = sh("coli_live_jobs").stdout.split()
check("the shell's live list skips a clone standing by and a closing generation",
      live[:1] == ["200"] and "201" not in live and "202" not in live)
check("and so does the board's",
      [r["id"] for r in colibri.live_generations()] == ["200"])

# ---------------------------------------------------------------------------
# 2. two tasks filed at once start one generation
# ---------------------------------------------------------------------------
for list_it, how in ((True, "listed at once"),
                     (False, "not yet listed by squeue")):
    reset()
    calls, got = [], []
    start = submitter(calls, list_it)

    def go(n):
        got.append(colibri.file("knn-across-embedders", "task %d" % n, WS,
                                start=start)[0])

    ts = [threading.Thread(target=go, args=(n,)) for n in range(2)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    check("two tasks filed at once start ONE generation (%s)" % how,
          len(calls) == 1)
    check("and both are queued (%s)" % how,
          all(got) and len(colibri.tasks(QUEUE)) == 2)

reset()
calls = []
put("300")
colibri.file("knn-across-embedders", "a task", WS, start=submitter(calls))
check("a task filed with a generation running starts nothing", calls == [])
reset()
calls = []
put("301", "PENDING", "afternotok:300")
colibri.file("knn-across-embedders", "a task", WS, start=submitter(calls))
check("a clone standing by is not a generation: a task starts one",
      len(calls) == 1)

# ---------------------------------------------------------------------------
# 3. a death mid-task, resumed by the clone
# ---------------------------------------------------------------------------
reset()
put("400")
put("401", "PENDING", "afternotok:400")
rec, _ = colibri.file("knn-across-embedders", "rerun the sweep", WS,
                      start=submitter([]))
seen = []


def dies(task, job):
    seen.append(dict(task))
    end(job)                                # no exit file: a node failure
    return colibri.HOP


rc = colibri.work("400", run=dies, ready=lambda: True, sleep=lambda s: None,
                  idle=0, say=lambda s: None)
check("the generation that died under its task exits not-ok", rc != 0)
check("Slurm releases the clone", [j["id"] for j in slurm()["jobs"]] == ["401"]
      and slurm()["jobs"][0]["state"] == "RUNNING")


def finishes(task, job):
    seen.append(dict(task))
    return 0


rc = colibri.work("401", run=finishes, ready=lambda: True,
                  sleep=lambda s: None, idle=0, say=lambda s: None)
after = colibri.tasks(QUEUE)[0]
check("the clone resumes the task and finishes it", after["queue"] == "done")
check("as its second attempt, with one death counted",
      seen[-1]["attempts"] == 2 and after["deaths"] == 1)
check("in the same conversation, which coli-code resumes by name",
      seen[-1]["session"] == seen[0]["session"] == rec["session"])
check("and then exits cleanly on an empty queue", rc == 0)

# run_task resumes a second attempt with -c and the conversation's name.
fake = os.path.join(BIN, "coli-code")
with open(fake, "w") as fh:
    fh.write("#!/bin/bash\nprintf '%%s\\n' \"$COLI_SESSION_ID\" \"$COLI_JOB\" "
             "\"$@\" > %s/argv\necho 'RELAY: graded 3 sessions'\nexit 0\n"
             % TMP)
os.chmod(fake, 0o755)
os.environ["COLI_CODE"] = fake
colibri.run_task(dict(after, attempts=2), "401")
with open(os.path.join(TMP, "argv")) as fh:
    lines = fh.read().splitlines()
check("a resumed task runs coli-code with --continue, its session and its job",
      lines[0] == rec["session"] and lines[1] == "401" and "-c" in lines
      and WS in lines)
colibri.run_task(dict(after, attempts=1), "401")
with open(os.path.join(TMP, "argv")) as fh:
    said = fh.read()
check("a first attempt opens a fresh conversation",
      "-c" not in said.splitlines())
check("told its work is read-only: outputs under phi/, no tracked file "
      "touched", "under this workspace's `phi/`" in said
      and "Never edit, create, delete or rename a tracked file" in said
      and "RELAY:" in said and "hosted" not in said and "ships" not in said)
check("and so is a resumed one",
      "`phi/`" in colibri.TASK_RESUME_PROMPT
      and "tracked file" in colibri.TASK_RESUME_PROMPT)
check("with no fence for its output, the client's output goes nowhere",
      not colibri.tasks(QUEUE)[0].get("out"))
os.environ["COLI_SESSION_ROOT"] = os.path.join(TMP, "sessions", "phi")
colibri.run_task(dict(after, attempts=1), "401")
out = colibri.tasks(QUEUE)[0].get("out")
check("behind the fence, it is kept, and its path is on the task",
      out == os.path.join(TMP, "sessions", "phi", "tasks",
                          after["id"] + ".out")
      and open(out).read() == "RELAY: graded 3 sessions\n")
os.environ["COLI_SESSION_ROOT"] = os.path.join(TMP, "sessions")
check("a session root that is not a phi/ directory is no fence",
      colibri.output_path(after) is None)
del os.environ["COLI_SESSION_ROOT"]

# ---------------------------------------------------------------------------
# 4. a clean exit drops the clone
# ---------------------------------------------------------------------------
reset()
put("500")
put("501", "PENDING", "afternotok:500")
rc = colibri.work("500", run=finishes, ready=lambda: True,
                  sleep=lambda s: None, idle=0, say=lambda s: None)
check("an empty queue for the idle limit is a clean exit", rc == 0)
check("and the generation marks itself closing, under the queue lock",
      colibri.closing("500"))
end("500", rc)
check("its last act is a 0 in the exit file", colibri.ended_clean("500"))
check("and Slurm drops the clone", slurm()["jobs"] == [])
calls = []
colibri.file("knn-across-embedders", "later", WS, start=submitter(calls))
check("a task filed afterwards starts a new generation", len(calls) == 1)

# A warm handover is an end on purpose: the task is requeued, not a death.
reset()
put("600")
r6, _ = colibri.file("knn-across-embedders", "x", WS, start=submitter([]))
colibri.claim_task(QUEUE, r6, "599")
colibri.mark_exit("599", 0)
colibri.recover("600")
r6 = colibri.tasks(QUEUE)[0]
check("a task whose generation ended on purpose is requeued without a death",
      r6["queue"] == "queued" and r6["deaths"] == 0)

# ---------------------------------------------------------------------------
# 5. the cap: three deaths on one task fail it
# ---------------------------------------------------------------------------
reset()
put("700")
r7, _ = colibri.file("knn-across-embedders", "doomed", WS, start=submitter([]))
for gen in ("697", "698", "699"):
    cur = colibri.tasks(QUEUE)[0]
    if cur["queue"] != "queued":
        break
    colibri.claim_task(QUEUE, cur, gen)
    colibri.recover("700")                 # gen left squeue with no exit file
r7 = colibri.tasks(QUEUE)[0]
check("three deaths on one task fail it", r7["queue"] == "failed")
check("with all three counted and the reason said",
      r7["deaths"] == 3 and "3 times" in r7["reason"])
check("and it is not retried", colibri.next_task(QUEUE) is None)
check("two deaths were not enough",
      colibri.task_verdict({"queue": "running", "gen": "1", "deaths": 1},
                            [], lambda g: False) == "death")

reset()
check("recovery is skipped where this generation is not listed: an "
      "unreachable controller is not every generation dead",
      colibri.recover("999") == [])

# ---------------------------------------------------------------------------
# 6. the relay's `colibri` request and its hook
# ---------------------------------------------------------------------------
base = {"id": "2026-10-03-coli-x", "kind": "colibri",
        "label": "knn-across-embedders", "brief": "rerun it", "filed": 1.0}
clean = []          # the subject's approved exports: none, and none needed
ok, probs = jobs.validate(base, clean, set(), {}, colibri=True)
check("a colibri request validates where the workspace opted in", ok and not probs)
ok, probs = jobs.validate(base, clean, set(), {}, colibri=False)
check("and is refused where it did not, naming the key",
      ok is None and any("relay.colibri" in x for x in probs))
ok, probs = jobs.validate(dict(base, brief=""), clean, set(), {}, colibri=True)
check("a colibri request needs a brief", ok is None and probs)

reset()
calls = []
first = colibri.relay_file(WS, base, start=submitter(calls))
check("the relay files a request as a task, and starts a generation",
      first["state"] == "submitted" and len(calls) == 1)
check("its report never carries the brief",
      "rerun it" not in json.dumps(first))
task = colibri.tasks(QUEUE)[0]
check("the task carries the request's label, and no thread",
      task.get("label") == "knn-across-embedders" and not task.get("thread"))
colibri.claim_task(QUEUE, task, "101")
colibri.finish_task(QUEUE, colibri.tasks(QUEUE)[0], True)
checked = []


def clean_check(where, rec):
    checked.append(where)
    return {"changed": 0, "relay": ["graded 3 sessions"]}


out = colibri.relay_pass(check=clean_check, start=submitter(calls))
check("a finished task is checked once, in its workspace", checked == [WS])
check("with no change, the report says completed and carries only its "
      "RELAY: lines", out and out[0][1]["state"] == "completed"
      and out[0][1]["relay"] == ["graded 3 sessions"]
      and out[0][1]["changed"] == 0 and out[0][1]["id"] == base["id"]
      and "rerun it" not in json.dumps(out) and "diff" not in out[0][1])
out = colibri.relay_pass(check=clean_check, start=submitter(calls))
check("a checked task is not checked again", len(checked) == 1)
check("and a pass starts no generation for a task already started",
      len(calls) == 1)

reset()
colibri.relay_file(WS, base, start=submitter([]))
colibri.claim_task(QUEUE, colibri.tasks(QUEUE)[0], "102")
colibri.finish_task(QUEUE, colibri.tasks(QUEUE)[0], True)
out = colibri.relay_pass(check=lambda where, rec: None,
                         start=submitter([]))
check("a check that cannot read leaves the task done and unchecked",
      out[0][1]["state"] == "running" and "check" in out[0][1]["note"]
      and not colibri.tasks(QUEUE)[0].get("checked"))
out = colibri.relay_pass(start=submitter([]))
check("and so does a pass with no check at all",
      out[0][1]["state"] == "running")
out = colibri.relay_pass(check=lambda where, rec: {"changed": 2, "relay": []},
                         start=submitter([]))
t = colibri.tasks(QUEUE)[0]
check("a task that changed tracked files is failed, with the reason",
      t["queue"] == "failed" and t["reason"] == relay.CHANGED
      and out[0][1]["state"] == "failed" and relay.CHANGED in out[0][1]["note"])
check("and its report counts the paths and names none",
      out[0][1]["changed"] == 2 and "2 path(s)" in out[0][1]["note"]
      and "uncommitted" in out[0][1]["note"])

# The check itself, on a real repository: what git can see, since the baseline.
def g(*args):
    return subprocess.run(["git"] + list(args), cwd=WS, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT).stdout.decode()


g("init", "-q", "-b", "main")
g("config", "user.email", "t@example.com")
g("config", "user.name", "t")
for rel, text in (("fit.py", "x = 1\n"), (".gitignore", "phi/\nlive/\n")):
    with open(os.path.join(WS, rel), "w") as fh:
        fh.write(text)
g("add", "-A")
g("commit", "-q", "-m", "seed")
with open(os.path.join(WS, "owner.md"), "w") as fh:
    fh.write("the owner's, before the task\n")
reset()
rec, _ = colibri.file("knn-across-embedders", "grade it", WS,
                      start=submitter([]))
check("filing keeps what git already sees changed as the task's baseline",
      list(rec["baseline"]) == ["owner.md"])
os.makedirs(os.path.join(WS, "phi"))
with open(os.path.join(WS, "phi", "grades.json"), "w") as fh:
    fh.write("{}\n")
check("writing under the ignored phi/ is no change",
      relay.check_task(WS, rec) == {"changed": 0, "relay": []})
with open(os.path.join(WS, "fit.py"), "w") as fh:
    fh.write("x = 2\n")
with open(os.path.join(WS, "owner.md"), "a") as fh:
    fh.write("and the task wrote here too\n")
check("a tracked edit, and a baseline file changed again, are the task's",
      relay.check_task(WS, rec)["changed"] == 2)
check("a workspace git cannot read is checked again later, never passed",
      relay.check_task(os.path.join(TMP, "nowhere"), rec) is None)

# ---------------------------------------------------------------------------
# the unguarded front end, which the node never runs
#
# `coli-code -a opencode` has no pre-tool hook, so it cannot carry the egress
# guard and still gets a shell. Refused wherever Slurm is, and anywhere in a
# workspace that holds phi/; and where it does run, no inherited opencode
# config reaches it.
# ---------------------------------------------------------------------------
CODE = os.path.join(ATLAS, "projects", "libr-local-llm", "bin", "coli-code")
CC = tempfile.mkdtemp(prefix="colicode-")
WITH = os.path.join(CC, "with-slurm")
WITHOUT = os.path.join(CC, "without-slurm")
for d in (WITH, WITHOUT):
    os.makedirs(d)


def stub(where, name, body):
    path = os.path.join(where, name)
    with open(path, "w") as fh:
        fh.write("#!/bin/bash\n" + body + "\n")
    os.chmod(path, 0o755)


stub(WITH, "sbatch", "exit 0")
for d in (WITH, WITHOUT):
    stub(d, "squeue", 'case "$*" in *"%i"*) [ -n "$CC_JOB" ] && '
                      'echo "999 RUNNING node1 None 5:00:00" ;; '
                      '*"%L"*) echo 5:00:00 ;; *"%N"*) echo node1 ;; esac; '
                      'exit 0')
    stub(d, "srun", 'env > "%s/srun.env"; printf "%%s\\n" "$@" > "%s/srun.argv"'
                    % (CC, CC))
# The rest of the PATH, less any real Slurm, so "no sbatch" means none.
REST = [d for d in os.environ.get("PATH", "").split(os.pathsep)
        if d and not os.path.exists(os.path.join(d, "sbatch"))]


def coli(slurm, workdir, *args, job=False):
    env = dict(os.environ,
               PATH=os.pathsep.join([WITH if slurm else WITHOUT] + REST),
               COLI_SESSION_ROOT=os.path.join(CC, "sessions", "phi"),
               OPENCODE_CONFIG=os.path.join(CC, "elsewhere.json"),
               OPENCODE_CONFIG_CONTENT='{"enabled_providers": ["deepseek"]}',
               CC_JOB="1" if job else "")
    env.pop("COLI_JOB", None)
    p = subprocess.run(["bash", CODE, "-d", workdir] + list(args), env=env,
                       stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, timeout=60)
    return p.returncode, p.stderr.decode()


PLAIN = os.path.join(CC, "plain")
HOLDS = os.path.join(CC, "holds")
SAYS = os.path.join(CC, "says")
for d in (PLAIN, os.path.join(HOLDS, "phi"), os.path.join(SAYS, "src")):
    os.makedirs(d)
for d in (PLAIN, HOLDS, SAYS):
    os.makedirs(os.path.join(d, ".git"))
with open(os.path.join(SAYS, "tutorboard.json"), "w") as fh:
    fh.write('{"phi": true}\n')

rc, err = coli(True, PLAIN, "-a", "opencode", "hi")
check("opencode is refused wherever Slurm is, in any directory",
      rc == 2 and "runs Slurm" in err)
rc, err = coli(True, PLAIN, "hi")
check("and the guarded front end is not: it goes on to look for a server",
      rc == 76 and "runs Slurm" not in err)
rc, err = coli(False, HOLDS, "-a", "opencode", "hi")
check("without Slurm, opencode is refused in a workspace that holds phi/",
      rc == 2 and "holds phi/" in err)
rc, err = coli(False, os.path.join(SAYS, "src"), "-a", "opencode", "hi")
check("and below a tutorboard.json that says \"phi\": true",
      rc == 2 and "holds phi/" in err)
if not os.path.isfile(os.path.join(ATLAS, "ai-config", "adapters",
                                   "generic.py")):
    print("note ai-config is not checked out here; skipping the run that "
          "reaches srun")
else:
    rc, err = coli(False, PLAIN, "-a", "opencode", "hi", job=True)
    with open(os.path.join(CC, "srun.env")) as fh:
        seen = fh.read()
    with open(os.path.join(CC, "srun.argv")) as fh:
        argv = fh.read()
    check("where it does run, an inherited opencode config is not handed on",
          rc == 0 and "OPENCODE_CONFIG" not in seen)
    check("and the far side's login profile cannot set one either",
          "unset OPENCODE_CONFIG OPENCODE_CONFIG_CONTENT;" in argv
          and argv.index("unset OPENCODE_CONFIG") < argv.index("exec opencode"))
shutil.rmtree(CC, ignore_errors=True)

shutil.rmtree(TMP, ignore_errors=True)
print("%d failed" % len(fails) if fails else "all on-demand checks pass")
sys.exit(1 if fails else 0)
