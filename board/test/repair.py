#!/usr/bin/env python3
"""A failed relay job is repaired on the Mac, by a doing turn.

What the checks are about:

  * ONE WAKE, ITS OWN SIGNAL. A failed recipe's report drops a `[repair]`
    line, carrying the request id, and `turn_signal` reads it as `repair`.
  * A DOING TURN WHATEVER THE STANCE. `doing_now` gives it a doing turn's
    clock, and `board brief` answers doing for it in a workspace that
    teaches, naming the request, its recipe, the file and line it failed at,
    and the report to read whole. Any [repair] in a batch makes the turn a
    repair, and the brief names every one (`woken_for`).
  * FIX OR ASK. The line gives the fix-check-push-rerun steps with the exact
    `board job --fixes` command, or a diagnostic recipe to file with
    `board diagnose`; a diagnostic that comes back wakes the same turn.
  * NOTHING LOOPS. `MAX_FIXES` automatic attempts per failure, diagnostics
    and reruns alike, refused on both machines past it; a plain rerun of an
    open repair is refused, whatever its VAR values; `--fresh` is the
    owner's, never a turn's.
  * NO MODEL ON THE CLUSTER. `board ask-cluster` is retired, saying what
    replaced it, and a `turn` request is refused by the policy.

Synthetic workspaces only, plus a read of the real TRD-EHR failure 2110916.
"""
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
sys.path.insert(0, ROOT)
os.environ["TUTOR_SLURM"] = "0"
box = tempfile.mkdtemp(prefix="tutor-repair-state-")
os.environ["BOARD_STATE_DIR"] = box
from tutorboard import jobs                                            # noqa: E402
from tutorboard.course import threads                                  # noqa: E402

TUTOR = os.path.join(ROOT, "bin", "tutor")
BOARD = os.path.join(ROOT, "bin", "board")
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


from tutorboard.runner import turn as runturn  # noqa: E402

SWEEP = """#!/bin/bash
#RELAY-VAR EMBEDDER [a-z0-9.-]{1,40}

echo "RELAY: done"
"""
DIAGNOSE = """#!/bin/bash
#RELAY-VAR LOOK (RESULTS_DIR)(/[a-z_]{1,20}){0,2}

python -m relay_hook --look "${LOOK:-}"
"""
SPINE = {
    "version": 1,
    "deliverables": [{"id": "paper1", "title": "Paper 1", "doc": ""}],
    "threads": [
        {"id": "knn", "deliverable": "paper1", "title": "Neighbours",
         "files": ["src/knn.py"]},
        {"id": "tripod", "deliverable": "paper1", "title": "Tripod",
         "files": []},
    ],
}
CHECK = "uv run --extra test python -m pytest tests -q"
ORIGIN = "2026-10-02-knn-sweep"
FIRST = {"id": ORIGIN, "kind": "recipe", "label": "knn",
         "recipe": "slurm/sweep.sbatch", "env": {"EMBEDDER": "bge-small"},
         "produces": ["results/knn/best.json"], "export": [], "filed": 100.0}
# The lines the recipe's failure helper prints (slurm_jobs/lib/), as the
# report carries them: prefix dropped, paths already relative.
HELPED = ["error FileNotFoundError at scripts/predictions/best_k_panels.py:88 "
          "in main",
          "step scripts.predictions.best_k_panels, recipe slurm/sweep.sbatch",
          "missing RESULTS_DIR/trained_models/lr.joblib",
          "recipe slurm/sweep.sbatch failed: exit 1 after line 79, "
          "checkout 20436b6"]
FAILED = {"state": "failed", "exit": "1:0", "error": "FileNotFoundError",
          "jobid": "2110916", "ended": "2026-10-02T22:13:25",
          "relay": HELPED}
DONE = {"state": "completed", "exit": "0:0"}
scenes = tempfile.mkdtemp(prefix="tutor-repair-")


def scene(reqs, reps, stance="teach"):
    """A workspace on disk holding these requests and reports. `{id: rec}`."""
    ws = tempfile.mkdtemp(dir=scenes)
    write(threads.path(ws), json.dumps(SPINE))
    write(os.path.join(ws, "tutorboard.json"),
          json.dumps({"name": "Proj", "stance": stance, "check": CHECK}))
    write(os.path.join(ws, "slurm", "sweep.sbatch"), SWEEP)
    write(os.path.join(ws, "slurm", "diagnose.sbatch"), DIAGNOSE)
    for r in reqs:
        write(os.path.join(ws, "relay", "requests", r["id"] + ".json"),
              json.dumps(r))
    for rid, rep in reps.items():
        write(os.path.join(ws, "relay", "reports", rid + ".json"),
              json.dumps(dict(rep, id=rid)))
    threads._cache.clear()
    return ws, dict((r["request"], r) for r in jobs.relayed(ws))


def diag(n, filed):
    return {"id": "d%d" % n, "kind": "recipe", "label": "knn",
            "recipe": "slurm/diagnose.sbatch", "env": {}, "produces": [],
            "export": [], "fixes": ORIGIN, "filed": filed}


def rerun(n, filed, **env):
    return dict(FIRST, id="r%d" % n, fixes=ORIGIN, filed=filed,
                env=env or FIRST["env"])


RERUN = ("board job --label knn --fixes %s --produces results/knn/best.json "
         "-- slurm/sweep.sbatch EMBEDDER=bge-small" % ORIGIN)

try:
    # --- a failed recipe: a [repair] line, fix or ask ------------------------------
    ws, recs = scene([FIRST], {ORIGIN: FAILED})
    text = jobs.relay_sense(ws, recs[ORIGIN])
    check("a failed recipe wakes a repair: its line opens [repair], and "
          "turn_signal reads it so",
          jobs.repairs(ws, recs[ORIGIN]) and text.startswith("[repair] ")
          and runturn.turn_signal("[2026-10-02 22:20:00] " + text)
          == "repair")
    check("it names the whole report to read, where it failed, and the recipe",
          "relay/reports/%s.json" % ORIGIN in text
          and "scripts/predictions/best_k_panels.py:88" in text
          and "after its line 79" in text and "slurm/sweep.sbatch" in text)
    check("A: fix here, run the subject's check from its tutorboard.json "
          "(no thread is read), ship with `board push`, then the exact "
          "rerun, last",
          "the subject's check, %s" % CHECK in text
          and 'board push "<what changed>"' in text and RERUN in text
          and text.index("board push") < text.index(RERUN))
    check("B: or ask with a diagnostic recipe this workspace has, through "
          "`board diagnose --fixes`",
          "board diagnose --fixes %s -- slurm/diagnose.sbatch [LOOK=...]"
          % ORIGIN in text and "produces nothing" in text)
    check("attempt 1 of the cap, which counts diagnostics and reruns alike",
          "attempt 1 of %d" % jobs.MAX_FIXES in text and jobs.MAX_FIXES == 3)
    check("and it neither moves a thread on nor names a cluster turn",
          "tick the task" not in text and "thread" not in text and "ask-cluster" not in text
          and "relay.turns" not in text)

    ws, recs = scene([FIRST], {ORIGIN: DONE})
    text = jobs.relay_sense(ws, recs[ORIGIN])
    check("a recipe that completed is a plain [job] line, no repair",
          not jobs.repairs(ws, recs[ORIGIN]) and text.startswith("[job] ")
          and "on knn has come back" in text and "board thread" not in text)
    ws, recs = scene([dict(FIRST, kind="colibri", brief="x")],
                     {ORIGIN: FAILED})
    check("and a failed request that is no recipe is no repair either",
          not jobs.repairs(ws, recs[ORIGIN])
          and jobs.relay_sense(ws, recs[ORIGIN]).startswith("[job] "))

    # --- a diagnostic comes back ---------------------------------------------------
    ws, recs = scene([FIRST, diag(1, 200.0)],
                     {ORIGIN: FAILED,
                      "d1": dict(DONE, relay=["has RESULTS_DIR/trained_models "
                                              "entries 0"])})
    text = jobs.relay_sense(ws, recs["d1"])
    check("a diagnostic that came back wakes a repair too, to apply it",
          jobs.is_diagnostic(ws, recs["d1"]) and jobs.repairs(ws, recs["d1"])
          and text.startswith("[repair] ") and "it came back" in text
          and "entries 0" in text)
    check("its rerun is the failed request's recipe and values, not the "
          "diagnostic's, and the location is the failure's",
          RERUN in text and "slurm/diagnose.sbatch EMBEDDER" not in text
          and "relay/reports/%s.json" % ORIGIN in text
          and "best_k_panels.py:88" in text)
    check("it is attempt 2 of 3", "attempt 2 of 3" in text)
    check("and the repair stays open: a plain rerun is refused",
          jobs.open_fix(ws, "slurm/sweep.sbatch",
                        {"EMBEDDER": "bge-small"}) == ORIGIN)

    # --- the last attempt, then the cap -------------------------------------------
    ws, recs = scene([FIRST, diag(1, 200.0), rerun(2, 300.0)],
                     {ORIGIN: FAILED, "d1": DONE, "r2": FAILED})
    text = jobs.relay_sense(ws, recs["r2"])
    check("a failed rerun with one attempt left: fix and rerun, and no "
          "diagnostic after it",
          "attempt 3 of 3" in text and RERUN in text
          and "board diagnose" not in text and "last attempt" in text)
    ws, recs = scene([FIRST, diag(1, 200.0), rerun(2, 300.0),
                      rerun(3, 400.0)],
                     {ORIGIN: FAILED, "d1": DONE, "r2": FAILED, "r3": FAILED})
    text = jobs.relay_sense(ws, recs["r3"])
    check("after three attempts it gives up, naming each, and the owner "
          "decides",
          "last of 3 automatic attempts" in text and "d1: diagnostic" in text
          and "r2: rerun, failed" in text and "owner decides" in text
          and "--fresh" in text and "board job --label knn --fixes" not in text
          and "board diagnose" not in text)
    check("and a plain rerun is still refused at the cap",
          jobs.open_fix(ws, "slurm/sweep.sbatch",
                        {"EMBEDDER": "bge-small"}) == ORIGIN)

    ws, recs = scene([FIRST, rerun(2, 300.0)], {ORIGIN: FAILED, "r2": DONE})
    text = jobs.relay_sense(ws, recs["r2"])
    check("a rerun that completed closes the repair: a [job] line",
          text.startswith("[job] ") and "repair of %s is done" % ORIGIN in text
          and jobs.open_fix(ws, "slurm/sweep.sbatch",
                            {"EMBEDDER": "bge-small"}) == "")
    ws, recs = scene([FIRST, rerun(2, 300.0)], {ORIGIN: FAILED})
    check("a rerun still out leaves the plain rerun allowed",
          jobs.open_fix(ws, "slurm/sweep.sbatch",
                        {"EMBEDDER": "bge-small"}) == "")
    ws, recs = scene([FIRST, rerun(2, 300.0)],
                     {ORIGIN: FAILED, "r2": {"state": "refused",
                                             "problems": ["env ..."]}})
    text = jobs.relay_sense(ws, recs["r2"])
    check("a refused attempt invites no refile: the owner decides",
          text.startswith("[job] ") and "Do not file it again" in text
          and "owner decides" in text and "through `board job`" not in text)

    ws, recs = scene([FIRST], {ORIGIN: FAILED})
    check("open_fix keys on the recipe alone: another value of a VAR is the "
          "same repair; another recipe is not",
          jobs.open_fix(ws, "slurm/sweep.sbatch",
                        {"EMBEDDER": "bge-small"}) == ORIGIN
          and jobs.open_fix(ws, "slurm/sweep.sbatch",
                            {"EMBEDDER": "bge-large"}) == ORIGIN
          and jobs.open_fix(ws, "slurm/sweep.sbatch") == ORIGIN
          and jobs.open_fix(ws, "slurm/other.sbatch") == "")
    ws, recs = scene([FIRST, diag(1, 200.0), rerun(2, 300.0),
                      rerun(3, 400.0, EMBEDDER="bge-base")],
                     {ORIGIN: FAILED, "d1": DONE, "r2": FAILED, "r3": FAILED})
    check("a capped chain cannot restart by changing a VAR: the open repair "
          "is still the first request's, and its cap still stands",
          jobs.open_fix(ws, "slurm/sweep.sbatch",
                        {"EMBEDDER": "bge-large"}) == ORIGIN
          and jobs.fix_problems(rerun(4, 500.0, EMBEDDER="bge-large"),
                                jobs.requests(ws), {ORIGIN}) != [])
    ws, recs = scene([dict(FIRST, filed="soon")], {})
    check("a malformed `filed` reads as 0, and every reader still reads it",
          recs[ORIGIN]["submitted"] == 0.0
          and jobs.open_fix(ws, "slurm/sweep.sbatch",
                            {"EMBEDDER": "bge-small"}) == ""
          and jobs.context(ws)["failed"] == set())

    # --- the cap, on both machines -------------------------------------------------
    filed = [FIRST, diag(1, 1.0), rerun(2, 2.0)]
    check("fix_problems: two attempts before it, a third is allowed",
          jobs.fix_problems(rerun(3, 3.0), filed, {ORIGIN}) == [])
    said = jobs.fix_problems(diag(4, 4.0), filed + [rerun(3, 3.0)], {ORIGIN})
    check("fix_problems: a fourth is refused, diagnostic or rerun, naming "
          "--fresh", len(said) == 1 and "cap is 3" in said[0]
          and "--fresh" in said[0]
          and jobs.fix_problems(rerun(4, 4.0), filed + [rerun(3, 3.0)],
                                {ORIGIN}) != [])
    check("fix_problems: the cluster checking one filed counts only those "
          "before it", jobs.fix_problems(rerun(3, 3.0), filed + [
              rerun(3, 3.0), diag(4, 4.0)], {ORIGIN}, mine=True) == [])
    check("fix_problems: an attempt for a request with no failed report is "
          "refused", any("saying it failed" in p for p in jobs.fix_problems(
              diag(1, 1.0), [FIRST], set())))
    ok, problems = jobs.validate(
        {"id": "t-1", "kind": "turn", "thread": "knn", "brief": "why",
         "fixes": ORIGIN}, threads.validate(SPINE)[0], set(), {}, ())
    check("a turn request is refused by the policy, `fixes` or not: no "
          "hosted turn diagnoses", ok is None and problems == [jobs.NO_TURN])

    # --- heard: the [repair] line wakes a doing turn ---------------------------------
    top = tempfile.mkdtemp(dir=scenes)
    git(top, "init", "-q", "-b", "main")
    git(top, "config", "user.email", "t@example.com")
    git(top, "config", "user.name", "t")
    ws = os.path.join(top, "research", "Proj")
    write(os.path.join(ws, ".gitignore"), "live/\nrelay/state/\n")
    write(threads.path(ws), json.dumps(SPINE))
    write(os.path.join(ws, "tutorboard.json"),
          json.dumps({"name": "Proj", "check": CHECK}))
    write(os.path.join(ws, "slurm", "sweep.sbatch"), SWEEP)
    write(os.path.join(ws, "slurm", "diagnose.sbatch"), DIAGNOSE)
    write(os.path.join(ws, "relay", "requests", ORIGIN + ".json"),
          json.dumps(FIRST))
    write(os.path.join(ws, "live", "state.json"),
          json.dumps({"course": "Proj", "session": "lecture"}))
    git(top, "add", "-A")
    git(top, "commit", "-q", "-m", "a request")
    threads._cache.clear()
    jobs.hear(ws)
    write(os.path.join(ws, "relay", "reports", ORIGIN + ".json"),
          json.dumps(dict(FAILED, id=ORIGIN)))
    git(top, "add", "-A")
    git(top, "commit", "-q", "-m", "relay report")
    heard = jobs.hear(ws, now=500.0)
    with open(os.path.join(ws, "live", "inbox", "messages.jsonl"),
              encoding="utf-8") as fh:
        msgs = [json.loads(l) for l in fh if l.strip()]
    check("the pulled failure drops one [repair] line, signalled repair, "
          "carrying its request",
          [h["request"] for h in heard] == [ORIGIN] and len(msgs) == 1
          and msgs[0]["signal"] == "repair" and msgs[0]["request"] == ORIGIN
          and msgs[0]["text"].startswith("[repair] "))
    check("and `last_repair` finds that request again",
          jobs.last_repair(ws) == ORIGIN)
    check("the workspace teaches, so its sitting is a teaching turn ...",
          not runturn.doing_now(ws))
    CLOCK = {"headless_timeout": 900, "doing_timeout": 3600}
    check("... but the repair is a doing turn, on a doing turn's clock",
          runturn.doing_now(ws, "repair")
          and runturn.turn_timeout(CLOCK, ws, None, "repair") == 3600
          and runturn.turn_timeout(CLOCK, ws, None, "job") == 900)

    def brief_now():
        p = subprocess.run([sys.executable, BOARD, "brief"], cwd=ws,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           timeout=120, env=dict(os.environ))
        return p.returncode, p.stdout.decode("utf-8", "replace")

    code, plain = brief_now()
    check("`board brief` outside a repair turn says nothing of it",
          code == 0 and "REPAIRS A FAILED" not in plain
          and "mode: teach" in plain)
    write(os.path.join(ws, "live", "agent.json"), json.dumps(
        {"state": "working", "mode": "headless", "pid": os.getpid(),
         "turn_signal": "repair"}))
    code, out = brief_now()
    check("inside a [repair] turn `board brief` answers doing, in a "
          "workspace that teaches", code == 0
          and "THIS TURN REPAIRS A FAILED CLUSTER JOB" in out
          and "mode: teach" in out and out != plain)
    check("naming the request, its recipe, the file and line, and the report",
          "request  %s" % ORIGIN in out and "recipe   slurm/sweep.sbatch" in out
          and "at scripts/predictions/best_k_panels.py:88 "
          "(FileNotFoundError)" in out
          and "after line 79 of the recipe" in out
          and "report   relay/reports/%s.json" % ORIGIN in out
          and "0 of 3 automatic attempts" in out)
    doing = out.split("--- the method", 1)[-1]
    taught = plain.split("--- the method", 1)[-1]
    check("and the sitting's sense is the doing one, not the lesson's",
          doing != taught)
    write(os.path.join(ws, "live", "agent.json"), json.dumps(
        {"state": "working", "mode": "headless", "pid": os.getpid(),
         "turn_signal": "job"}))
    code, out = brief_now()
    check("a [job] turn in the same workspace is not briefed as a repair",
          code == 0 and "REPAIRS A FAILED" not in out)
    os.remove(os.path.join(ws, "live", "agent.json"))

    # --- a batch: any [repair] in it makes the turn a repair, naming each -----------
    SECOND = dict(FIRST, id="2026-10-02-tripod-sweep", thread="tripod",
                  filed=150.0)
    write(os.path.join(ws, "relay", "requests", SECOND["id"] + ".json"),
          json.dumps(SECOND))
    write(os.path.join(ws, "relay", "reports", SECOND["id"] + ".json"),
          json.dumps(dict(FAILED, id=SECOND["id"])))
    threads._cache.clear()
    inbox = os.path.join(ws, "live", "inbox", "messages.jsonl")
    with open(inbox, encoding="utf-8") as fh:
        kept = [json.loads(l) for l in fh if l.strip()]
    student = {"id": "s1", "rev": 0, "kind": "text", "answers": None,
               "t": 400.0, "iso": "2026-10-02 22:19:00", "from": "student",
               "text": "can you look at the knn figure?", "read": False}
    with open(inbox, "w", encoding="utf-8") as fh:
        for m in [student] + kept:
            fh.write(json.dumps(m) + "\n")
    second = dict((r["request"], r) for r in jobs.relayed(ws))[SECOND["id"]]
    jobs.drop(ws, second, now=600.0, text=jobs.relay_sense(ws, second),
              signal=jobs.REPAIR)
    p = subprocess.run([sys.executable, BOARD, "inbox"], cwd=ws,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       timeout=120)
    batch = p.stdout.decode("utf-8", "replace")
    signal, rids = runturn.woken_for(ws, batch)
    check("a batch whose first message is the student's, with two [repair] "
          "lines behind it: turn_signal reads the student's, woken_for reads "
          "repair and names both requests",
          runturn.turn_signal(batch) == "" and signal == "repair"
          and rids == [ORIGIN, SECOND["id"]])
    check("a signal with machinery of its own is kept, the repairs still named",
          runturn.woken_for(ws, "[2026-10-02 22:18:00] [ship] a mission "
                             "finished\n" + batch) == ("ship", rids))
    check("a revision ahead of a repair stays a revision, its own prompt and "
          "session", runturn.woken_for(ws, "[2026-10-02 22:18:00] [revise] the "
                                        "deck\n" + batch) == ("revise", rids))
    check("a batch with no [repair] in it is what turn_signal says",
          runturn.woken_for(ws, "[2026-10-02 22:19:00] hello") == ("", []))
    write(os.path.join(ws, "live", "agent.json"), json.dumps(
        {"state": "working", "mode": "headless", "pid": os.getpid(),
         "turn_signal": "ship", "turn_repairs": rids}))
    code, out = brief_now()
    check("the brief is a doing turn's and names every [repair] request in "
          "the batch, each with its report",
          code == 0 and "THIS TURN REPAIRS A FAILED CLUSTER JOB" in out
          and "woken for 2 [repair] requests" in out
          and "request  %s" % ORIGIN in out
          and "request  %s" % SECOND["id"] in out
          and "report   relay/reports/%s.json" % SECOND["id"] in out)
    os.remove(os.path.join(ws, "live", "agent.json"))
    os.remove(os.path.join(ws, "relay", "requests", SECOND["id"] + ".json"))
    os.remove(os.path.join(ws, "relay", "reports", SECOND["id"] + ".json"))
    threads._cache.clear()

    # --- the commands ------------------------------------------------------------------
    env = dict(os.environ, TUTOR_SLURM="0")

    def board(*args, **extra):
        p = subprocess.run([sys.executable, BOARD] + list(args), cwd=ws,
                           env=dict(env, **extra), stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=120)
        return p.returncode, p.stdout.decode("utf-8", "replace")

    code, out = board("ask-cluster", "knn", "Why did it fail?")
    check("`board ask-cluster` is retired, saying what replaced it, and "
          "files nothing",
          code == 2 and "retired" in out and "board diagnose" in out
          and len(jobs.requests(ws)) == 1)
    code, out = board("diagnose", "--fixes", ORIGIN, "--",
                      "slurm/missing.sbatch")
    check("`board diagnose` is `board job`: the same check, the same words",
          code == 1 and "board job:" in out and "slurm/missing.sbatch" in out)
    code, out = board("job", "--label", "knn", "--", "slurm/sweep.sbatch",
                      "EMBEDDER=bge-small")
    check("a plain rerun of the failed request is refused, naming --fixes "
          "and --fresh", code == 1 and "--fixes %s" % ORIGIN in out
          and "--fresh" in out)
    code, out = board("job", "--label", "knn", "--", "slurm/sweep.sbatch",
                      "EMBEDDER=bge-large")
    check("and so is one that changes a VAR: the repair is keyed on the "
          "recipe", code == 1 and "--fixes %s" % ORIGIN in out
          and len(jobs.requests(ws)) == 1)
    code, out = board("job", "--label", "knn", "--fresh", "--fixes", ORIGIN, "--",
                      "slurm/sweep.sbatch", "EMBEDDER=bge-small")
    check("--fresh and --fixes together are refused",
          code == 1 and "name one" in out)
    write(os.path.join(ws, "live", "agent.json"), json.dumps(
        {"state": "working", "mode": "headless", "pid": os.getpid(),
         "turn_signal": "repair"}))
    code, out = board("job", "--label", "knn", "--fresh", "--", "slurm/sweep.sbatch",
                      "EMBEDDER=bge-small")
    check("and --fresh is refused inside a turn: it is the owner's way past "
          "the cap", code == 1 and "owner's" in out
          and len(jobs.requests(ws)) == 1)
    os.remove(os.path.join(ws, "live", "agent.json"))
    code, out = board("job", "--label", "knn", "--fresh", "--", "slurm/sweep.sbatch",
                      "EMBEDDER=bge-large")
    fresh = [r for r in jobs.requests(ws) if r.get("id") != ORIGIN]
    check("outside a turn --fresh files it as a new request, no `fixes`: "
          "the owner's override", "its repair is open" not in out
          and len(fresh) == 1 and "fixes" not in fresh[0]
          and fresh[0].get("env") == {"EMBEDDER": "bge-large"})
finally:
    shutil.rmtree(scenes, ignore_errors=True)
    shutil.rmtree(box, ignore_errors=True)

# --- the real failure: TRD-EHR's 2110916 -------------------------------------------
# Frozen as it was when it failed: the real workspace's own files, with only that
# request and its report under relay/, so the requests filed since (its repair
# among them) do not move what this checks.
rid = "2026-10-02-knn-across-embedders-neighbor-count-sweep"
live_trd = os.path.join(REPO, "research", "TRD-EHR")
frozen = tempfile.mkdtemp(prefix="repair-2110916-")
trd = os.path.join(frozen, "TRD-EHR")
for _rel in ("threads.json", "tutorboard.json", "slurm_jobs/quick_runs/neighbor_count_sweep.sbatch",
             "slurm_jobs/quick_runs/diagnose.sbatch", "relay/requests/%s.json" % rid,
             "relay/reports/%s.json" % rid):
    os.makedirs(os.path.dirname(os.path.join(trd, _rel)), exist_ok=True)
    shutil.copy(os.path.join(live_trd, _rel), os.path.join(trd, _rel))
real = dict((r["request"], r) for r in jobs.relayed(trd)).get(rid)
check("2110916 is request %s, failed, in TRD-EHR" % rid,
      real is not None and real.get("slurm") == "2110916"
      and jobs.ended_failed(real))
if real:
    text = jobs.relay_sense(trd, real)
    check("were it heard now it would wake a repair, attempt 1 of 3, with "
          "the exact rerun and TRD-EHR's own diagnostic",
          text.startswith("[repair] ") and "attempt 1 of 3" in text
          and ("board job --fixes %s --produces "
               "results/bge-small-en-v1.5/google_medgemma-27b-text-it/"
               "neighbor_count_sweep -- slurm_jobs/quick_runs/"
               "neighbor_count_sweep.sbatch EMBEDDER=bge-small-en-v1.5"
               % rid) in text
          and "board diagnose --fixes %s -- "
              "slurm_jobs/quick_runs/diagnose.sbatch" % rid in text)
    check("and a plain rerun of it is refused until it carries --fixes",
          jobs.open_fix(trd,
                        "slurm_jobs/quick_runs/neighbor_count_sweep.sbatch",
                        {"EMBEDDER": "bge-small-en-v1.5"}) == rid)
    lines = jobs.repair_brief(trd, rid)
    check("its brief names the request, recipe and report; its report "
          "carries no RELAY: lines, so a diagnostic is how to ask",
          any(rid in l for l in lines)
          and any("neighbor_count_sweep.sbatch" in l for l in lines)
          and any("relay/reports/%s.json" % rid in l for l in lines)
          and any("a diagnostic recipe is how to ask" in l for l in lines))
    check("with no thread read, the brief and the [repair] line name "
          "TRD-EHR's own check from its tutorboard.json",
          any(l.strip().startswith("check") and "pytest tests" in l
              for l in lines)
          and "the subject's check, uv run" in text)
    ok, problems = jobs.check(trd, {
        "id": "x-diagnose", "kind": "recipe", "thread": "knn-across-embedders",
        "recipe": "slurm_jobs/quick_runs/diagnose.sbatch",
        "env": {"EMBEDDER": "bge-small-en-v1.5",
                "LOOK": "RESULTS_DIR/trained_models"},
        "produces": [], "export": [], "fixes": rid, "filed": 1.0})
    check("and its diagnostic would pass the check, once the recipe is "
          "committed", not [p for p in problems
                            if "not tracked and unchanged" not in p])

shutil.rmtree(frozen, ignore_errors=True)

print()
if fails:
    print("%d check(s) failed" % len(fails))
    sys.exit(1)
print("a failed relay job wakes a doing turn that fixes it or asks, and "
      "nothing loops")
