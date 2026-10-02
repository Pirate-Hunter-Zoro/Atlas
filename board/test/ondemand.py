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

from tutorboard import colibri, jobs, missions                # noqa: E402

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
_PLACES = {"research/TRD-EHR": WS, "TRD-EHR": WS}
colibri.atlas.find = lambda ident, base=None: (
    {"root": _PLACES[ident], "id": "research/TRD-EHR"} if ident in _PLACES
    else None)
colibri.atlas.identify = lambda path: "research/TRD-EHR"


def slurm():
    with open(SLURM) as fh:
        return json.load(fh)


def reset():
    with open(SLURM, "w") as fh:
        json.dump({"next": 100, "jobs": [], "argv": []}, fh)
    for d in (STATE, os.path.join(QUEUE, "live")):
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
          all(got) and len(missions.tasks(QUEUE)) == 2)

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
after = missions.tasks(QUEUE)[0]
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
             "\"$@\" > %s/argv\nexit 0\n" % TMP)
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
    check("a first attempt opens a fresh conversation",
          "-c" not in fh.read().splitlines())

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
missions.claim_task(QUEUE, r6, "599")
colibri.mark_exit("599", 0)
colibri.recover("600")
r6 = missions.tasks(QUEUE)[0]
check("a task whose generation ended on purpose is requeued without a death",
      r6["queue"] == "queued" and r6["deaths"] == 0)

# ---------------------------------------------------------------------------
# 5. the cap: three deaths on one task fail it
# ---------------------------------------------------------------------------
reset()
put("700")
r7, _ = colibri.file("knn-across-embedders", "doomed", WS, start=submitter([]))
for gen in ("697", "698", "699"):
    cur = missions.tasks(QUEUE)[0]
    if cur["queue"] != "queued":
        break
    missions.claim_task(QUEUE, cur, gen)
    colibri.recover("700")                 # gen left squeue with no exit file
r7 = missions.tasks(QUEUE)[0]
check("three deaths on one task fail it", r7["queue"] == "failed")
check("with all three counted and the reason said",
      r7["deaths"] == 3 and "3 times" in r7["reason"])
check("and it is not retried", missions.next_task(QUEUE) is None)
check("two deaths were not enough",
      missions.task_verdict({"queue": "running", "gen": "1", "deaths": 1},
                            [], lambda g: False) == "death")

reset()
check("recovery is skipped where this generation is not listed: an "
      "unreachable controller is not every generation dead",
      colibri.recover("999") == [])

# ---------------------------------------------------------------------------
# 6. the relay's `colibri` request and its hook
# ---------------------------------------------------------------------------
base = {"id": "2026-10-03-coli-x", "kind": "colibri",
        "thread": "knn-across-embedders", "brief": "rerun it", "filed": 1.0}
clean = {"threads": [{"id": "knn-across-embedders"}]}
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
task = missions.tasks(QUEUE)[0]
missions.claim_task(QUEUE, task, "101")
missions.finish_task(QUEUE, missions.tasks(QUEUE)[0], True)
reviewed = []


def review(where, req):
    reviewed.append((where, req))
    return "the sweep reran; 4 panels changed; shipped"


out = colibri.relay_pass(review=review, start=submitter(calls))
check("a finished task gets one hosted review turn in its workspace",
      len(reviewed) == 1 and reviewed[0][0] == WS
      and reviewed[0][1]["kind"] == "turn")
check("and the report says completed, with only that turn's public note",
      out and out[0][1]["state"] == "completed"
      and out[0][1]["note"].startswith("the sweep reran")
      and out[0][1]["id"] == base["id"])
out = colibri.relay_pass(review=review, start=submitter(calls))
check("a reviewed task is not reviewed again", len(reviewed) == 1)
check("and a pass starts no generation for a task already started",
      len(calls) == 1)

shutil.rmtree(TMP, ignore_errors=True)
print("%d failed" % len(fails) if fails else "all on-demand checks pass")
sys.exit(1 if fails else 0)
