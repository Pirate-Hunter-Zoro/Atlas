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
    check("and, relay turns being off here, names the opt-in that would "
          "have a cluster turn diagnose it",
          "relay.turns" in text and "--fixes" not in text)
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
                              "tutor-pull.plist")).read()
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

# --- a failed job where relay turns are on: diagnosed there, fixed here ---------
import shlex                                                           # noqa: E402

ORIGIN = "2026-10-02-knn-sweep"
FIRST = {"id": ORIGIN, "kind": "recipe", "thread": "knn",
         "recipe": "slurm/sweep.sbatch", "env": {"EMBEDDER": "bge-small"},
         "produces": ["results/knn/best.json"], "export": [], "filed": 100.0}
FAILED = {"state": "failed", "exit": "1:0", "error": "FileNotFoundError",
          "jobid": "2110916", "ended": "2026-10-02T22:13:25"}
CHECK = "uv run --extra test python -m pytest tests -q"
scenes = tempfile.mkdtemp(prefix="tutor-fixing-")


def scene(reqs, reps, turns=True):
    """A workspace on disk holding these requests and reports. `{id: rec}`."""
    ws = tempfile.mkdtemp(dir=scenes)
    write(threads.path(ws), json.dumps(SPINE))
    write(os.path.join(ws, "tutorboard.json"),
          json.dumps({"name": "Proj", "check": CHECK,
                      "relay": {"turns": turns}}))
    for r in reqs:
        write(os.path.join(ws, "relay", "requests", r["id"] + ".json"),
              json.dumps(r))
    for rid, rep in reps.items():
        write(os.path.join(ws, "relay", "reports", rid + ".json"),
              json.dumps(dict(rep, id=rid)))
    threads._cache.clear()
    return ws, dict((r["request"], r) for r in jobs.relayed(ws))


def fix_turn(n, filed):
    return {"id": "fx%d" % n, "kind": "turn", "thread": "knn",
            "brief": "Diagnose fix attempt %d" % n, "fixes": ORIGIN,
            "filed": filed}


try:
    ws, recs = scene([FIRST], {ORIGIN: FAILED})
    text = jobs.relay_sense(ws, recs[ORIGIN])
    line = next((l.strip() for l in text.splitlines()
                 if l.strip().startswith("board ask-cluster")), "")
    words = shlex.split(line)
    brief = words[-1] if len(words) == 6 else ""
    check("a failed recipe, relay turns on: the turn files fix attempt 1 itself",
          words[:5] == ["board", "ask-cluster", "knn", "--fixes", ORIGIN]
          and "fix attempt 1 of 2" in text and "tick the task" not in text)
    check("with one brief the code wrote: under the cap, diagnose and edit "
          "nothing, CAUSE/FIX or UNKNOWN, the exit and error, publishable",
          0 < len(brief) <= jobs.MAX_BRIEF and "Do not edit anything" in brief
          and "CAUSE:" in brief and "FIX:" in brief and "UNKNOWN:" in brief
          and "exit 1" in brief and "FileNotFoundError" in brief
          and "`" not in brief and "$" not in brief
          and jobs.request_leak(ws, {"id": "x", "kind": "turn",
                                     "thread": "knn", "brief": brief}) == "")
    check("no rerun while no fix turn is filed for it",
          jobs.open_fix(ws, "knn", "slurm/sweep.sbatch") == "")

    ws, recs = scene([FIRST], {ORIGIN: {"state": "refused",
                                        "problems": ["env DATA ..."]}})
    check("a refused recipe files no fix",
          "--fixes" not in jobs.relay_sense(ws, recs[ORIGIN]))

    plain = {"id": "t1", "kind": "turn", "thread": "knn", "brief": "look",
             "filed": 50.0}
    ws, recs = scene([plain], {"t1": FAILED})
    text = jobs.relay_sense(ws, recs["t1"])
    check("a failed turn that is no fix keeps the plain wording",
          "--fixes" not in text and 'board ask-cluster knn "<what to read>"'
          in text and "tick the task" in text)

    rerun = dict(FIRST, id="r2", fixes=ORIGIN, filed=300.0)
    ws, recs = scene([FIRST, fix_turn(1, 200.0), rerun],
                     {ORIGIN: FAILED,
                      "fx1": {"state": "completed",
                              "note": "CAUSE: a path. FIX: in run.py ..."},
                      "r2": FAILED})
    text = jobs.relay_sense(ws, recs["r2"])
    check("a failed rerun after one fix files attempt 2 of 2, for the first",
          "fix attempt 2 of 2" in text and "--fixes %s" % ORIGIN in text
          and "Request r2 ran" in text)
    check("a plain rerun of that recipe is refused: its chain is open",
          jobs.open_fix(ws, "knn", "slurm/sweep.sbatch") == ORIGIN
          and jobs.open_fix(ws, "knn", "slurm/other.sbatch") == ""
          and jobs.open_fix(ws, "tripod", "slurm/sweep.sbatch") == "")
    ws, recs = scene([FIRST, fix_turn(1, 200.0), rerun],
                     {ORIGIN: FAILED, "fx1": {"state": "completed",
                                              "note": "CAUSE: x\nFIX: y"},
                      "r2": {"state": "completed", "exit": "0:0"}})
    check("and allowed once the newest rerun in the chain completed",
          jobs.open_fix(ws, "knn", "slurm/sweep.sbatch") == "")
    ws, recs = scene([FIRST, fix_turn(1, 200.0), rerun],
                     {ORIGIN: FAILED, "fx1": {"state": "completed",
                                              "note": "CAUSE: x\nFIX: y"}})
    check("or while that rerun is still out",
          jobs.open_fix(ws, "knn", "slurm/sweep.sbatch") == "")

    ws, recs = scene([FIRST, fix_turn(1, 200.0), fix_turn(2, 400.0),
                      dict(rerun, id="r3", filed=500.0)],
                     {ORIGIN: FAILED,
                      "fx1": {"state": "completed", "note": "CAUSE: one"},
                      "fx2": {"state": "completed", "note": "CAUSE: two"},
                      "r3": FAILED})
    text = jobs.relay_sense(ws, recs["r3"])
    check("after two fix turns it gives up, naming each and what it said",
          "gave up" in text and "fx1: CAUSE: one" in text
          and "fx2: CAUSE: two" in text and "board ask-cluster" not in text
          and "owner decides" in text)
    check("and a plain rerun is still refused at the cap; `--fixes` is the "
          "owner's way back in",
          jobs.open_fix(ws, "knn", "slurm/sweep.sbatch") == ORIGIN)

    def after_fix(rep, more=()):
        ws, recs = scene([FIRST, fix_turn(1, 200.0)] + list(more),
                         {ORIGIN: FAILED, "fx1": rep})
        return jobs.relay_sense(ws, recs["fx1"])
    text = after_fix({"state": "completed", "exit": "0:0",
                      "note": "CAUSE: the sweep read a missing panel file.\n"
                              "FIX: in load_panel, read PANEL_DIR."})
    rerun_line = ("board job knn --fixes %s --produces results/knn/best.json "
                  "-- slurm/sweep.sbatch EMBEDDER=bge-small" % ORIGIN)
    check("a CAUSE/FIX note: the Mac turn applies the fix in the thread's "
          "files, runs the workspace's check, ships it with `board push`",
          "Apply that FIX yourself" in text
          and "results/knn/sweep.png" in text and CHECK in text
          and 'board push "knn: <what changed>"' in text
          and "tick the task" not in text)
    check("and reruns with the exact `board job --fixes` command, last",
          rerun_line in text
          and text.index("board push") < text.index(rerun_line)
          and "the rerun is filed" in text)
    check("a FIX line may sit past the first line, under markdown",
          "Apply that FIX" in after_fix(
              {"state": "completed", "exit": "0:0",
               "note": "**CAUSE:** a path.\n\n- **FIX:** read PANEL_DIR."}))
    text = after_fix({"state": "completed", "exit": "0:0",
                      "note": "UNKNOWN: read the log and the loader; no "
                              "single cause."})
    check("an UNKNOWN note: no rerun, the card says what it checked and the "
          "owner decides",
          "board job knn --fixes" not in text and "owner decides" in text
          and "what it checked" in text and "board ask-cluster" not in text
          and "tick the task" not in text)
    text = after_fix({"state": "completed", "exit": "0:0",
                      "note": "CAUSE: a path, and no fix given."})
    check("a CAUSE with no FIX is no fix either",
          "board job knn --fixes" not in text and "owner decides" in text)
    text = after_fix({"state": "failed", "exit": "124:0",
                      "note": "The turn left no note."})
    check("a fix turn that itself failed files attempt 2",
          "fix attempt 2 of 2" in text
          and "board ask-cluster knn --fixes %s" % ORIGIN in text)

    text = after_fix({"state": "refused", "problems": ["the cap is 2"]})
    check("a refused fix turn invites no refile: the owner decides",
          "file it again through `board job`" not in text
          and "Do not file it again" in text and "owner decides" in text
          and "tick the task" not in text)
    ws, recs = scene([FIRST, fix_turn(1, 200.0), rerun],
                     {ORIGIN: FAILED, "fx1": {"state": "completed",
                                              "note": "CAUSE: x\nFIX: y"},
                      "r2": {"state": "refused", "problems": ["env ..."]}})
    text = jobs.relay_sense(ws, recs["r2"])
    check("and so does a refused rerun",
          "rerun for %s" % ORIGIN in text and "Do not file it again" in text
          and "file it again through `board job`" not in text)

    ws, recs = scene([dict(FIRST, filed="soon")], {})
    check("a malformed `filed` reads as 0 in the registry, and every reader "
          "still reads it", recs[ORIGIN]["submitted"] == 0.0
          and jobs.open_fix(ws, "knn", "slurm/sweep.sbatch") == ""
          and jobs.context(ws)["failed"] == set())
finally:
    shutil.rmtree(scenes, ignore_errors=True)

print()
if fails:
    print("%d check(s) failed" % len(fails))
    sys.exit(1)
print("a pulled report wakes one turn, the pull follows the requests, and "
      "results/ falls back to exports/")
