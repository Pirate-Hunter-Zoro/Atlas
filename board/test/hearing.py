#!/usr/bin/env python3
"""The Mac hears the cluster: a pulled report wakes a turn, on a cadence.

What the checks are about:

  * ONE WAKE. A report a pull brought to an end drops the same `[job]` line a
    local ending does, in the same inbox, signalled `job`. Once per ending.
  * THE BASELINE IS SET AT FILING. A refusal arriving in the very first pull
    after a request is filed is still heard; a fresh clone hears nothing of
    the reports it arrived with.
  * THE CADENCE FOLLOWS THE REQUESTS. Two minutes while one is out, hourly
    otherwise, decided by `jobs.pull_due`, never by the timer.
  * ONE PATH ON BOTH MACHINES. A `results/` path the tree lacks is read from
    `exports/results/` by the thread check and the results library.

Synthetic repositories only: a bare origin, a "Mac" clone and a "cluster"
clone, with `TUTOR_SLURM=0` standing in for the Mac.
"""

import importlib.machinery
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ["TUTOR_SLURM"] = "0"
from tutorboard import jobs, paths                                     # noqa: E402
from tutorboard.course import results, threads                         # noqa: E402

TUTOR = os.path.join(ROOT, "bin", "tutor")
fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def git(cwd, *args):
    p = subprocess.run(["git"] + list(args), cwd=cwd, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, check=False)
    return p.stdout.decode("utf-8", "replace")


def inbox(ws):
    path = os.path.join(ws, "live", "inbox", "messages.jsonl")
    try:
        with open(path, encoding="utf-8") as fh:
            return [json.loads(l) for l in fh if l.strip()]
    except OSError:
        return []


_loader = importlib.machinery.SourceFileLoader("tutorcli_hearing", TUTOR)
_spec = importlib.util.spec_from_loader("tutorcli_hearing", _loader)
tutorcli = importlib.util.module_from_spec(_spec)
_loader.exec_module(tutorcli)

RECIPE = """#!/bin/bash
#SBATCH --job-name=sweep
#RELAY-VAR EMBEDDER [a-z0-9.-]{1,40}

echo "RELAY: done"
"""

SPINE = {
    "version": 1,
    "deliverables": [{"id": "paper1", "title": "Paper 1", "doc": ""}],
    "threads": [
        {"id": "knn", "deliverable": "paper1", "title": "Neighbours",
         "files": ["results/knn/sweep.png", "results/knn/gone.png"],
         "exports": [{"path": "results/knn/sweep.png", "aggregate": True}]},
    ],
}

base = tempfile.mkdtemp(prefix="tutor-hearing-")
try:
    origin = os.path.join(base, "origin.git")
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", origin],
                   check=True)
    mac = os.path.join(base, "mac")
    os.makedirs(mac)
    git(mac, "init", "-q", "-b", "main")
    for clone in (mac,):
        git(clone, "config", "user.email", "t@example.com")
        git(clone, "config", "user.name", "t")
    write(os.path.join(mac, "atlas.json"),
          json.dumps({"families": [{"id": "research"}]}))
    ws = os.path.join(mac, "research", "Proj")
    write(os.path.join(ws, "AI_INSTRUCTIONS.md"), "# contract\n")
    # Anchored: an unanchored `results/` would hide `exports/results/` too.
    write(os.path.join(ws, ".gitignore"), "live/\n/results/\n")
    write(os.path.join(ws, "slurm", "sweep.sbatch"), RECIPE)
    write(threads.path(ws), json.dumps(SPINE))
    git(mac, "add", "-A")
    git(mac, "commit", "-q", "-m", "start")
    git(mac, "remote", "add", "origin", origin)
    git(mac, "push", "-q", "-u", "origin", "main")
    cluster = os.path.join(base, "cluster")
    git(base, "clone", "-q", origin, cluster)
    git(cluster, "config", "user.email", "c@example.com")
    git(cluster, "config", "user.name", "c")
    cws = os.path.join(cluster, "research", "Proj")
    os.environ["TUTORBOARD_COURSES"] = mac
    stamp = os.path.join(base, "heard.stamp")

    # --- the cadence ----------------------------------------------------------
    check("nothing out: the pull is hourly",
          jobs.pull_interval([ws]) == jobs.PULL_IDLE == 3600)
    check("a pull is due on a fresh stamp, or one from the future",
          jobs.pull_due(0, 100, 3600) and jobs.pull_due(500, 100, 3600))
    check("an hourly pull is not due after two minutes",
          not jobs.pull_due(1000, 1120, jobs.PULL_IDLE))
    check("a two-minute pull is due on a timer that fired a few seconds early",
          jobs.pull_due(1000, 1112, jobs.PULL_BUSY))

    pulled = []

    def fake_pull(where, quiet=False):
        pulled.append(where)
        return True

    write(stamp, "%f\n" % 1000.0)
    got, interval, heard = tutorcli.hear_pass(stamp=stamp, now=1120,
                                              pull=fake_pull)
    check("idle, two minutes after the last pull: no pull",
          got is False and pulled == [] and interval == jobs.PULL_IDLE)

    # --- a request filed on the Mac --------------------------------------------
    req = {"id": "2026-10-03-knn-sweep", "kind": "recipe", "thread": "knn",
           "recipe": "slurm/sweep.sbatch", "env": {"EMBEDDER": "bge-small"},
           "produces": ["results/knn/best.json"],
           "export": ["results/knn/sweep.png"], "filed": 1100.0}
    _, ok, said = jobs.file_request(ws, req, push=False)
    git(mac, "push", "-q")
    check("the request is committed", ok)
    check("filing records the heard baseline, in an ignored ledger",
          os.path.isfile(os.path.join(ws, "live", "jobs.reported",
                                      jobs.HEARD))
          and git(mac, "status", "--porcelain").strip() == "")
    threads._cache.clear()
    check("a request out: the pull is every two minutes",
          jobs.pull_interval([ws]) == jobs.PULL_BUSY)
    got, interval, heard = tutorcli.hear_pass(stamp=stamp, now=1120,
                                              pull=fake_pull)
    check("so two minutes after the last pull, it pulls",
          got is True and len(pulled) == 1 and interval == jobs.PULL_BUSY
          and heard == [])

    lines = jobs.thread_relay(ws, "knn")
    check("`board brief` lists the request still out",
          any("Waiting on the cluster" in l for l in lines)
          and any("2026-10-03-knn-sweep" in l and "requested" in l
                  for l in lines))

    # --- the cluster says it is running, then that it ended ---------------------
    def cluster_reports(rep):
        git(cluster, "pull", "-q", "--ff-only")
        write(os.path.join(cws, "relay", "reports", rep["id"] + ".json"),
              json.dumps(rep))
        git(cluster, "add", "-A")
        git(cluster, "commit", "-q", "-m", "relay report " + rep["id"])
        git(cluster, "push", "-q")

    cluster_reports({"id": req["id"], "state": "running", "jobid": "88",
                     "submitted": 1200.0})
    got, _, heard = tutorcli.hear_pass(stamp=stamp, now=1300)
    check("a running report pulled in wakes nothing", got is True
          and heard == [] and inbox(ws) == [])

    write(os.path.join(cws, "exports", "results", "knn", "sweep.png"),
          "\x89PNG" + "x" * 2000)
    cluster_reports({"id": req["id"], "state": "failed", "jobid": "88",
                     "exit": "1:0", "ended": "2026-10-03T10:00:00",
                     "submitted": 1200.0, "produced": [],
                     "exported": ["results/knn/sweep.png"],
                     "relay": ["RELAY: k=300 best", "RELAY: then it fell over"],
                     "note": "the sweep ran out of memory at k=500"})
    got, interval, heard = tutorcli.hear_pass(stamp=stamp, now=1420)
    msgs = inbox(ws)
    check("the ended report is heard on the pull that brought it",
          got is True and [h["request"] for h in heard] == [req["id"]])
    check("one [job] line, signalled job, in the workspace's inbox",
          len(msgs) == 1 and msgs[0]["signal"] == "job"
          and msgs[0]["text"].startswith("[job]"))
    text = msgs[0]["text"] if msgs else ""
    check("it wakes a turn the way a local ending does",
          tutorcli.turn_signal("[2026-10-03 10:00:00] " + text) == "job")
    check("it says what ended, the exit, what is missing and what landed",
          "failed" in text and "1:0" in text
          and "MISSING results/knn/best.json" in text
          and "landed   results/knn/sweep.png" in text)
    check("it carries the RELAY: lines and the note, and no log",
          "RELAY: k=300 best" in text and "out of memory" in text
          and "log stays on the cluster" in text)
    check("it tells the turn to move the thread on through `board job`",
          "board thread" in text and "board job" in text
          and "board ask-cluster knn" in text)
    check("and the pull is hourly again", interval == jobs.PULL_IDLE)

    tutorcli.hear_pass(stamp=stamp, now=1600, force=True)
    check("heard once: the next pass drops nothing", len(inbox(ws)) == 1)
    shutil.rmtree(os.path.join(ws, "live", "jobs.reported"))
    git(mac, "commit", "-q", "--allow-empty", "-m", "elsewhere")
    jobs.hear(ws)
    check("a lost ledger is a new baseline, not a second wake",
          len(inbox(ws)) == 1)

    lines = jobs.thread_relay(ws, "knn")
    check("`board brief` gives the last report, its RELAY lines and note",
          any(l.startswith("The last cluster report: 2026-10-03-knn-sweep, "
                           "failed, exit 1:0") for l in lines)
          and "  RELAY: k=300 best" in lines
          and any("out of memory" in l for l in lines)
          and not any("Waiting" in l for l in lines))

    # --- a refusal in the first pull after filing --------------------------------
    req2 = dict(req, id="2026-10-03-knn-again", filed=1700.0)
    shutil.rmtree(os.path.join(ws, "live", "jobs.reported"))
    jobs.file_request(ws, req2, push=False)
    git(mac, "push", "-q")
    cluster_reports({"id": req2["id"], "state": "refused",
                     "problems": ["env DATA is not declared"]})
    tutorcli.hear_pass(stamp=stamp, now=1800, force=True)
    msgs = inbox(ws)
    check("a refusal arriving in the first pull after filing is heard",
          len(msgs) == 2 and "refused" in msgs[-1]["text"]
          and "env DATA is not declared" in msgs[-1]["text"])

    # --- a held step's check: one [coach] line, never a [job] one -----------------
    from tutorboard import holds
    git(cluster, "pull", "-q", "--ff-only")
    write(os.path.join(cws, "relay", "holds", "knn.json"), json.dumps(
        {"thread": "knn", "files": ["src/knn.py"], "at": 1900.0}))
    git(cluster, "add", "-A")
    git(cluster, "commit", "-q", "-m", "knn: hold")
    git(cluster, "push", "-q")
    cluster_reports({"id": "check-knn-1", "thread": "knn", "step": 1,
                     "state": "completed", "check": "src/knn.py", "exit": 0,
                     "relay": ["n=120 mean=0.42"]})
    before = len(inbox(ws))
    got, interval, heard = tutorcli.hear_pass(stamp=stamp, now=2000, force=True)
    msgs = inbox(ws)[before:]
    check("a pulled check report drops exactly one [coach] line, no [job] line",
          len(msgs) == 1 and msgs[0]["signal"] == "coach"
          and msgs[0]["text"].startswith("[coach] Step 1 of thread knn")
          and not any(m["text"].startswith("[job]") for m in msgs))
    check("and while the hold stands the pull runs every POLL_SECONDS",
          interval == holds.POLL_SECONDS)
    tutorcli.hear_pass(stamp=stamp, now=2100, force=True)
    check("and the next pull drops nothing more", len(inbox(ws)) == before + 1)
    plist = open(os.path.join(ROOT, "scripts", "launchd",
                              "org.atlas.tutor-pull.plist")).read()
    check("the Mac's timer fires often enough for that cadence",
          "<integer>%d</integer>" % holds.POLL_SECONDS in plist)

    # --- a fresh clone -----------------------------------------------------------
    fresh = os.path.join(base, "fresh")
    git(base, "clone", "-q", origin, fresh)
    fws = os.path.join(fresh, "research", "Proj")
    check("a fresh clone hears nothing of the reports it arrived with",
          jobs.hear(fws) == [] and jobs.hear(fws) == [] and inbox(fws) == [])

    # --- one path on both machines ---------------------------------------------
    rel = "results/knn/sweep.png"
    check("the Mac has no results/, only the export",
          not os.path.exists(os.path.join(ws, "results")))
    check("paths.present finds the exported copy",
          paths.present(ws, rel) == os.path.join(ws, "exports", rel)
          and paths.present(ws, "results/knn/none.png") == ""
          and paths.present(ws, "results/../../../etc/passwd") == "")
    threads._cache.clear()
    stale = threads.check(ws)
    check("`board thread --check` counts it present, and a lost one stale",
          not any("sweep.png" in l for l in stale)
          and any("gone.png" in l for l in stale))
    results.forget()
    figs = results.figures(ws)
    check("the results library offers it at its results/ path",
          [f["rel"] for f in figs] == [rel])
    path, _ = results.find(ws, results.ident(rel))
    check("and serves the exported bytes",
          path == os.path.realpath(os.path.join(ws, "exports", rel)))
    write(os.path.join(ws, rel), "\x89PNG" + "y" * 2000)
    results.forget()
    path, _ = results.find(ws, results.ident(rel))
    check("a figure results/ holds is read from there, and offered once",
          path == os.path.realpath(os.path.join(ws, rel))
          and len(results.figures(ws)) == 1)
finally:
    shutil.rmtree(base, ignore_errors=True)

print()
if fails:
    print("%d check(s) failed" % len(fails))
    sys.exit(1)
print("a pulled report wakes one turn, the pull follows the requests, and "
      "results/ falls back to exports/")
