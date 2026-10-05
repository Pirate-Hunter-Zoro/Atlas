#!/usr/bin/env python3
"""A machine without Slurm files a request; the registry sees it and its report.

What the checks are about:

  * ONE VALIDATOR, REFUSING WHOLE. `jobs.validate` is pure, both machines call
    it, and a bad request comes back with every problem at once.
  * THE REGISTRY IS ONE VIEW. Local jobs, requests and reports merge, and a
    request with no report reads `requested` -- a status of its own, between
    `running` and `written`.
  * THE REQUEST COMMIT CARRIES THE REQUEST AND NOTHING ELSE. Whatever else the
    tree has going on stays out of it.
  * AN EXPORT IS THE OWNER'S WORD. `board thread export` lists it unanswered;
    only `--aggregate` lets a request name it.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
sys.path.insert(0, ROOT)
from tutorboard import jobs                                            # noqa: E402
from tutorboard.course import threads                                  # noqa: E402

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
                       stderr=subprocess.DEVNULL, check=False)
    return p.stdout.decode("utf-8", "replace")


RECIPE = """#!/bin/bash
#SBATCH --job-name=sweep
#RELAY-VAR EMBEDDER [a-z0-9.-]{1,40}
#RELAY-VAR REDRAW [01]
#RELAY-VAR PATH .*

echo "RELAY: done"
"""

SPINE = {
    "version": 1,
    "deliverables": [{"id": "paper1", "title": "Paper 1", "doc": ""}],
    "threads": [
        {"id": "knn", "deliverable": "paper1", "title": "Neighbours",
         "exports": [{"path": "results/sweep.png", "aggregate": True},
                     "results/rows.csv"]},
        {"id": "tripod", "deliverable": "paper1", "title": "TRIPOD",
         "outputs": ["results/t.csv"]},
    ],
}

# --- the thread file's exports ------------------------------------------------
clean, problems = threads.validate(SPINE)
knn = threads.thread(clean, "knn")
check("a thread's exports validate, a bare string read as not yet answered",
      not problems and knn["exports"] == [
          {"path": "results/sweep.png", "aggregate": True},
          {"path": "results/rows.csv", "aggregate": False}])
check("and a thread with none has an empty list",
      threads.thread(clean, "tripod")["exports"] == [])
check("only an aggregate one is exportable",
      threads.exportable(knn, "results/sweep.png")
      and not threads.exportable(knn, "results/rows.csv"))
bad = json.loads(json.dumps(SPINE))
bad["threads"][0]["exports"] = [{"path": "scripts/x.png"},
                                {"path": "results/model.joblib"},
                                {"path": "results/a.png", "aggregate": "yes"}]
_, problems = threads.validate(bad)
check("an export outside results/, of the wrong kind, or with a non-boolean "
      "aggregate is refused, all three at once", len(problems) == 3)

# --- the validator ------------------------------------------------------------------
declared = {"slurm/sweep.sbatch": jobs.declarations(RECIPE)}
check("a recipe's header declares its variables, and PATH is never one",
      sorted(declared["slurm/sweep.sbatch"][0]) == ["EMBEDDER", "REDRAW"]
      and any("PATH" in p for p in declared["slurm/sweep.sbatch"][1]))
check("the header ends at the first line of code",
      jobs.declarations("#!/bin/bash\necho hi\n#RELAY-VAR X .*\n") == ({}, []))
tracked = {"slurm/sweep.sbatch", "slurm/other.sh"}
good = {"id": "2026-10-03-knn-sweep", "kind": "recipe", "thread": "knn",
        "recipe": "slurm/sweep.sbatch", "env": {"EMBEDDER": "bge-small"},
        "produces": ["results/knn/best.json"], "export": ["results/sweep.png"]}


def v(req, taken=(), turns=False):
    return jobs.validate(req, clean, tracked, declared, taken, turns)


ok, problems = v(good)
check("a recipe whose header declares PATH refuses every request on it",
      ok is None and any("PATH" in p for p in problems))

declared_clean = {"slurm/sweep.sbatch": (declared["slurm/sweep.sbatch"][0], [])}


def vc(req, taken=(), turns=False):
    return jobs.validate(req, clean, tracked, declared_clean, taken, turns)


ok, problems = vc(good)
check("with a clean header, a good request passes, as the request it is",
      problems == [] and ok["env"] == {"EMBEDDER": "bge-small"}
      and ok["export"] == ["results/sweep.png"])

cases = (
    ("an id that is not an id", dict(good, id="Has Spaces")),
    ("an id already filed", good, ("2026-10-03-knn-sweep",)),
    ("a thread the file lacks", dict(good, thread="ghost")),
    ("a recipe that is not tracked", dict(good, recipe="slurm/new.sbatch")),
    ("a recipe that is not a .sbatch", dict(good, recipe="slurm/other.sh")),
    ("a recipe outside the workspace", dict(good, recipe="../x.sbatch")),
    ("an undeclared variable", dict(good, env={"DATA": "x"})),
    ("a value its pattern does not match", dict(good, env={"REDRAW": "2"})),
    ("a comma smuggling a second variable",
     dict(good, env={"EMBEDDER": "a,LD_PRELOAD=/x"})),
    ("an export not marked aggregate", dict(good, export=["results/rows.csv"])),
    ("an export outside results/", dict(good, export=["scripts/a.png"])),
    ("an export of the wrong kind", dict(good, export=["results/m.joblib"])),
    ("a produces path that climbs out", dict(good, produces=["../../etc"])),
    ("a key the contract does not have", dict(good, shell="rm -rf /")),
    ("a kind that does not exist", dict(good, kind="shell")),
)
for case in cases:
    name, req = case[0], case[1]
    taken = case[2] if len(case) > 2 else ()
    ok, problems = vc(req, taken)
    check("refused: " + name, ok is None and len(problems) >= 1)

everything = dict(good, id="BAD", thread="ghost", recipe="slurm/new.sbatch",
                  env={"DATA": "x"}, export=["results/rows.csv"],
                  produces=["../x"], extra=1)
ok, problems = vc(everything)
check("and every problem comes back at once, not the first",
      ok is None and len(problems) >= 6)
said = " ".join(problems)
check("each named: the id, the thread, the recipe, the key, the produces path",
      "BAD" in said and "ghost" in said and "slurm/new.sbatch" in said
      and "DATA" in said and "../x" in said and "`extra`" in said)

turn = {"id": "2026-10-03-knn-turn", "kind": "turn", "thread": "knn",
        "brief": "Read dimension_importance.json and say whether L1 took."}
check("a turn request passes where the workspace opted in",
      vc(turn, turns=True)[1] == [])
check("and is refused where it has not",
      any("relay.turns" in p for p in vc(turn)[1]))
check("a turn with no brief is refused",
      vc(dict(turn, brief="  "), turns=True)[0] is None)

# --- `fixes`: a fix turn or a rerun, linked to the request that failed first --
origin = "2026-10-03-knn-sweep"
fix = dict(turn, id="2026-10-03-knn-fix", fixes=origin)
ok, problems = vc(fix, turns=True)
check("a turn with a valid `fixes` passes, carrying it",
      problems == [] and ok["fixes"] == origin)
check("a `fixes` that is not a request id is refused",
      any("`fixes`" in p for p in vc(dict(fix, fixes="BAD ID"),
                                      turns=True)[1]))
check("and so is one naming the request itself",
      vc(dict(fix, fixes=fix["id"]), turns=True)[0] is None)
ok, problems = vc(dict(good, id="2026-10-03-knn-rerun", fixes=origin))
check("a recipe with `fixes` passes, carrying it",
      problems == [] and ok["fixes"] == origin)
check("a colibri request has no `fixes`",
      any("`fixes`" in p for p in jobs.validate(
          {"id": "c-1", "kind": "colibri", "thread": "knn", "brief": "x",
           "fixes": origin}, clean, tracked, declared_clean, (), True,
          True)[1]))

failed_first = dict(good, id=origin)
on_disk = [failed_first]
failed = {origin}
check("fix_problems: no `fixes`, no problems",
      jobs.fix_problems(turn, on_disk, failed) == [])
check("fix_problems: a `fixes` naming nothing filed is refused",
      any("not a filed request" in p for p in jobs.fix_problems(
          dict(fix, fixes="2026-01-01-ghost"), on_disk, failed)))
check("fix_problems: a `fixes` naming a turn is refused",
      any("not a recipe" in p for p in jobs.fix_problems(
          dict(fix, fixes="t-0"), on_disk + [dict(turn, id="t-0")], failed)))
check("fix_problems: a `fixes` naming a rerun is refused: name the first",
      any("failed first" in p for p in jobs.fix_problems(
          dict(fix, fixes="rr"), on_disk + [dict(good, id="rr",
                                                 fixes=origin)],
          failed | {"rr"})))
check("fix_problems: a `fixes` naming another thread's request is refused",
      any("thread tripod" in p for p in jobs.fix_problems(
          fix, [dict(failed_first, thread="tripod")], failed)))
one_prior = on_disk + [dict(fix, id="f-1", filed=1.0)]
two_prior = one_prior + [dict(fix, id="f-2", filed=2.0)]
check("fix_problems: one fix turn before it, still allowed",
      jobs.fix_problems(fix, one_prior, failed) == [])
said = jobs.fix_problems(dict(fix, filed=3.0), two_prior, failed)
check("fix_problems: two before it, the third is refused at the cap",
      len(said) == 1 and "cap is 2" in said[0])
check("fix_problems: the cluster checking one filed counts only those "
      "before it", jobs.fix_problems(dict(fix, id="f-2", filed=2.0),
                                     two_prior, failed, mine=True) == [])
check("fix_problems: a rerun recipe is not a fix turn and has no cap",
      jobs.fix_problems(dict(good, id="rr", fixes=origin), two_prior,
                        failed) == [])
said = jobs.fix_problems(fix, on_disk, set())
check("fix_problems: a `fixes` naming a request with no failed report is "
      "refused, for a fix turn and a rerun alike",
      len(said) == 1 and "saying it failed" in said[0]
      and jobs.fix_problems(dict(good, id="rr", fixes=origin), on_disk, ())
      != [])

# --- the merged registry, and `requested` ----------------------------------------
base = tempfile.mkdtemp(prefix="tutor-requests-")
try:
    ws = os.path.join(base, "ws")
    write(threads.path(ws), json.dumps(SPINE))
    write(os.path.join(ws, "jobs.jsonl"), json.dumps(
        {"thread": "tripod", "jobid": "77", "cmd": "sbatch t.sbatch",
         "submitted": 1.0}) + "\n" + json.dumps(
        {"jobid": "77", "state": "RUNNING"}) + "\n")
    write(os.path.join(ws, "relay", "requests", "r1.json"),
          json.dumps(dict(good, id="r1", filed=5.0)))
    threads._cache.clear()
    view = jobs.view(ws)
    check("the view holds the local job and the request, each once",
          sorted(view) == ["77", "relay:r1"])
    check("a request with no report reads REQUESTED, with its thread and cmd",
          view["relay:r1"]["state"] == "REQUESTED"
          and view["relay:r1"]["thread"] == "knn"
          and "EMBEDDER=bge-small" in view["relay:r1"]["cmd"]
          and view["relay:r1"]["submitted"] == 5.0)
    st = threads.stages(ws)
    check("and its thread says requested, while the local job's says running",
          st["knn"]["status"] == "requested"
          and st["tripod"]["status"] == "running")
    check("requested sits between running and written",
          threads.STAGES.index("running") < threads.STAGES.index("requested")
          < threads.STAGES.index("written"))
    busy = dict((j["thread"], j) for j in jobs.running(ws))
    check("the busy strip carries the request, as REQUESTED",
          busy["knn"]["state"] == "REQUESTED")

    t = threads.thread(clean, "knn")
    req_rec = {"thread": "knn", "jobid": "relay:x", "state": "REQUESTED"}
    run_rec = {"thread": "knn", "jobid": "9", "state": "RUNNING"}
    check("stage: a request alone is requested",
          threads.stage(t, set(), {}, [], [req_rec])["status"] == "requested")
    check("stage: a request beside a running job is running",
          threads.stage(t, set(), {}, [], [req_rec, run_rec])["status"]
          == "running")

    write(os.path.join(ws, "relay", "reports", "r1.json"), json.dumps(
        {"id": "r1", "state": "running", "jobid": "88", "submitted": 6.0}))
    threads._cache.clear()
    view = jobs.view(ws)
    check("a report saying running makes it RUNNING, with its Slurm id",
          view["relay:r1"]["state"] == "RUNNING"
          and view["relay:r1"]["slurm"] == "88"
          and threads.stages(ws)["knn"]["status"] == "running")

    write(os.path.join(ws, "relay", "reports", "r1.json"), json.dumps(
        {"id": "r1", "state": "completed", "jobid": "88", "exit": "0:0",
         "produced": ["results/knn/best.json"], "note": "k=300 best"}))
    threads._cache.clear()
    view = jobs.view(ws)
    check("a completed report ends it, carrying exit, produced and note",
          view["relay:r1"]["state"] == "COMPLETED"
          and view["relay:r1"]["exit"] == "0:0"
          and view["relay:r1"]["note"] == "k=300 best"
          and threads.stages(ws)["knn"]["status"] == "open")
    write(os.path.join(ws, "relay", "reports", "r1.json"), json.dumps(
        {"id": "r1", "state": "refused", "problems": ["env DATA ..."]}))
    threads._cache.clear()
    check("and a refused one is terminal too",
          threads.finished(jobs.view(ws)["relay:r1"])
          and threads.stages(ws)["knn"]["status"] == "open")

    # On the cluster, the relay's own submission is a local job too.
    write(os.path.join(ws, "relay", "reports", "r1.json"), json.dumps(
        {"id": "r1", "state": "running", "jobid": "77"}))
    threads._cache.clear()
    view = jobs.view(ws)
    check("a report naming a job this machine registered folds into it, once",
          sorted(view) == ["77"] and view["77"]["request"] == "r1")
    check("and the raw sbatch registry is not touched by any of it",
          [j.get("jobid") for j in threads.jobs_of(ws)] == ["77", "77"])
    check("ids are dated, slugged and made unique",
          jobs.new_id("knn", "Sweep.sbatch", (), now=0).endswith("-knn-sweep-sbatch")
          and jobs.new_id("knn", "x", {jobs.new_id("knn", "x")}).endswith("-2"))

    # --- the command, on a machine without Slurm ------------------------------------
    origin = os.path.join(base, "origin.git")
    subprocess.run(["git", "init", "-q", "--bare", origin], check=True)
    top = os.path.join(base, "repo")
    os.makedirs(top)
    git(top, "init", "-q", "-b", "main")
    git(top, "config", "user.email", "t@example.com")
    git(top, "config", "user.name", "t")
    proj = os.path.join(top, "research", "Proj")
    write(os.path.join(proj, "AI_INSTRUCTIONS.md"), "# contract\n")
    write(os.path.join(proj, ".gitignore"), "live/\nresults/\n")
    write(os.path.join(proj, "slurm", "sweep.sbatch"),
          RECIPE.replace("#RELAY-VAR PATH .*\n", ""))
    write(os.path.join(proj, "notes.md"), "draft\n")
    write(threads.path(proj), json.dumps(SPINE))
    git(top, "add", "-A")
    git(top, "commit", "-q", "-m", "start")
    git(top, "remote", "add", "origin", origin)
    git(top, "push", "-q", "-u", "origin", "main")
    # Work in flight that the request commit must leave alone.
    write(os.path.join(proj, "notes.md"), "draft, edited\n")
    write(os.path.join(proj, "scratch.py"), "x = 1\n")
    git(top, "add", "research/Proj/scratch.py")

    env = dict(os.environ, TUTOR_SLURM="0")

    def board(*args):
        p = subprocess.run([sys.executable, BOARD] + list(args), cwd=proj,
                           env=env, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=180)
        return p.returncode, p.stdout.decode("utf-8", "replace")

    code, out = board("job", "knn", "--", "sbatch", "slurm/sweep.sbatch")
    check("on the Mac a bare sbatch is an error, naming the recipe form",
          code == 1 and "no Slurm" in out and "<recipe.sbatch>" in out)
    code, out = board("job", "knn", "--", "slurm/sweep.sbatch", "DATA=/x")
    check("an undeclared variable is refused before anything is committed",
          code == 1 and "DATA" in out
          and not os.path.isdir(os.path.join(proj, "relay")))
    head = git(top, "rev-parse", "HEAD").strip()
    code, out = board("job", "knn", "--produces", "results/knn/best.json",
                      "--export", "results/sweep.png", "--",
                      "slurm/sweep.sbatch", "EMBEDDER=bge-small")
    check("a good request is filed and pushed", code == 0 and "filed" in out)
    files = git(top, "show", "--name-only", "--format=", "HEAD").split()
    check("in one commit that touches relay/requests/ and nothing else",
          git(top, "rev-parse", "HEAD~1").strip() == head and len(files) == 1
          and files[0].startswith("research/Proj/relay/requests/"))
    check("and it reached origin",
          git(top, "rev-parse", "HEAD").strip()
          == git(origin, "rev-parse", "main").strip())
    status = git(top, "status", "--porcelain")
    check("the owner's edit and their staged file are still where they were",
          " M research/Proj/notes.md" in status
          and "A  research/Proj/scratch.py" in status)
    filed = jobs.requests(proj)
    check("the request on disk is the contract's shape",
          len(filed) == 1 and filed[0]["kind"] == "recipe"
          and filed[0]["env"] == {"EMBEDDER": "bge-small"}
          and filed[0]["export"] == ["results/sweep.png"]
          and filed[0]["produces"] == ["results/knn/best.json"]
          and isinstance(filed[0]["filed"], float)
          and jobs.check(proj, filed[0], mine=True)[1] == [])
    threads._cache.clear()
    code, out = board("thread", "--show", "knn")
    check("and `board thread --show` says the thread is requested",
          code == 0 and json.loads(out)["stage"]["status"] == "requested")
    code, out = board("job", "--show")
    check("`board job --show` lists the request", code == 0
          and "relay:" in out and "REQUESTED" in out)

    code, out = board("ask-cluster", "knn", "Why did L1 keep every dimension?")
    check("ask-cluster is refused where the workspace has not opted in",
          code == 1 and "relay.turns" in out)

    # --- `--fixes`: the Mac files a fix turn, then the rerun ------------------
    write(os.path.join(proj, "tutorboard.json"),
          json.dumps({"name": "Proj", "relay": {"turns": True}}))
    first = filed[0]["id"]
    code, out = board("ask-cluster", "knn", "--fixes", first,
                      "Read the log and say the fix.")
    check("`--fixes` naming a request with no failed report is refused",
          code == 1 and "saying it failed" in out
          and not [r for r in jobs.requests(proj) if r.get("kind") == "turn"])
    write(os.path.join(proj, "relay", "reports", first + ".json"),
          json.dumps({"id": first, "state": "failed", "exit": "1:0"}))
    code, out = board("ask-cluster", "knn", "--fixes", first,
                      "Read the log and say the fix.")
    fixed = [r for r in jobs.requests(proj) if r.get("kind") == "turn"]
    check("`board ask-cluster --fixes` files a fix turn naming the request",
          code == 0 and len(fixed) == 1 and fixed[0]["fixes"] == first
          and "-fix" in fixed[0]["id"]
          and fixed[0]["brief"] == "Read the log and say the fix.")
    code, out = board("job", "knn", "--", "slurm/sweep.sbatch",
                      "EMBEDDER=bge-small")
    check("then a rerun without `--fixes` is refused, naming the flag",
          code == 1 and "--fixes %s" % first in out
          and len(jobs.requests(proj)) == 2)
    code, out = board("job", "knn", "--fixes", first, "--",
                      "slurm/sweep.sbatch", "EMBEDDER=bge-small")
    rerun = [r for r in jobs.requests(proj)
             if r.get("kind") == "recipe" and r.get("fixes")]
    check("`board job --fixes` files the rerun, naming it too",
          code == 0 and len(rerun) == 1 and rerun[0]["fixes"] == first
          and rerun[0]["env"] == {"EMBEDDER": "bge-small"})
    p = subprocess.run([sys.executable, BOARD, "job", "knn", "--fixes", first,
                        "--", "slurm/sweep.sbatch"], cwd=proj,
                       env=dict(env, TUTOR_SLURM="1"), stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=60)
    check("and with Slurm `--fixes` is refused: it links a relay request",
          p.returncode == 1 and b"--fixes" in p.stdout)

    # --- `board thread export` ---------------------------------------------------
    code, out = board("thread", "export", "tripod", "results/t.csv")
    check("`board thread export` lists it unanswered and prints the question",
          code == 0 and "May results/t.csv be published?" in out
          and "--aggregate" in out)
    one = threads.thread(threads.read(proj)[0], "tripod")
    check("and it is not exportable until the owner says so",
          one["exports"] == [{"path": "results/t.csv", "aggregate": False}])
    board("thread", "export", "tripod", "results/t.csv", "--aggregate")
    one = threads.thread(threads.read(proj)[0], "tripod")
    check("--aggregate records the owner's yes",
          threads.exportable(one, "results/t.csv"))
    board("thread", "export", "tripod", "results/t.csv", "--drop")
    one = threads.thread(threads.read(proj)[0], "tripod")
    check("--drop unlists it", one["exports"] == [])
finally:
    shutil.rmtree(base, ignore_errors=True)

# --- the real repository -------------------------------------------------------------
recipe = os.path.join(REPO, "research", "TRD-EHR", "slurm_jobs", "quick_runs",
                      "neighbor_count_sweep.sbatch")
with open(recipe, encoding="utf-8") as fh:
    names, said = jobs.declarations(fh.read())
check("TRD-EHR's neighbour sweep declares EMBEDDER and REDRAW for the relay",
      said == [] and sorted(names) == ["EMBEDDER", "REDRAW"])
check("TRD-EHR has opted in to relay turns, so a failed job is diagnosed there",
      jobs.context(os.path.join(REPO, "research", "TRD-EHR"))["turns"] is True)
for ws in ("research/TRD-EHR", "research/PSYCH-ASR", "projects/libr-local-llm"):
    root = os.path.join(REPO, ws)
    if os.path.isdir(root):
        check("%s: git would see a request" % ws, jobs.request_visible(root) == "")

# --- a request is public the moment it is pushed --------------------------------
leaky = tempfile.mkdtemp(prefix="tutor-leak-")
try:
    req = {"id": "x-1", "kind": "turn", "thread": "knn",
           "brief": "read the traceback in /mnt/lab/storage/run.log"}
    target, done, said = jobs.file_request(leaky, req, push=False)
    check("a brief naming an absolute path is refused, and nothing is written",
          not done and "path" in said and not os.path.exists(target))
    from tutorboard import atlas, leaving
    saved = dict(leaving._POLICY)
    leaving._POLICY.update(root=atlas.root(),
                           fn=lambda t: "SESSION-" in str(t))
    try:
        said = jobs.request_leak(leaky, dict(req, brief="what SESSION-4 said"))
    finally:
        leaving._POLICY.clear()
        leaving._POLICY.update(saved)
    check("and so is one the PHI policy matches", "PHI policy" in said)
finally:
    shutil.rmtree(leaky, ignore_errors=True)

print()
if fails:
    print("%d check(s) failed" % len(fails))
    sys.exit(1)
print("a request is checked whole, filed alone, and read as requested until "
      "its report lands")
