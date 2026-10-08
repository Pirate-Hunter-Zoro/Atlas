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
  * AN EXPORT IS THE OWNER'S WORD: an entry in the subject's committed
    tutorboard.json `relay.exports` (`approval.py` proves the rule).
  * NO THREAD. A request carries an optional `label` and `session`; a
    `thread` is accepted and ignored, and validation never reads threads.json.
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
from tutorboard import exports, jobs                                   # noqa: E402
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
good = {"id": "2026-10-03-knn-sweep", "kind": "recipe", "label": "knn",
        "recipe": "slurm/sweep.sbatch", "env": {"EMBEDDER": "bge-small"},
        "produces": ["results/knn/best.json"], "export": ["results/sweep.png"]}
# The subject's approved exports, as `exports.approvals` reads them.
ALLOWED = [{"glob": "results/sweep.png"}, {"glob": "results/rows.csv"},
           {"glob": "results/agg/*.csv", "aggregate": True}]


def v(req, taken=(), colibri=False):
    return jobs.validate(req, ALLOWED, tracked, declared, taken, colibri)


ok, problems = v(good)
check("a recipe whose header declares PATH refuses every request on it",
      ok is None and any("PATH" in p for p in problems))

declared_clean = {"slurm/sweep.sbatch": (declared["slurm/sweep.sbatch"][0], [])}


def vc(req, taken=(), colibri=False):
    return jobs.validate(req, ALLOWED, tracked, declared_clean, taken, colibri)


ok, problems = vc(good)
check("with a clean header, a good request passes, as the request it is",
      problems == [] and ok["env"] == {"EMBEDDER": "bge-small"}
      and ok["export"] == ["results/sweep.png"] and ok["label"] == "knn"
      and "thread" not in ok)
bare = dict((k, v_) for k, v_ in good.items() if k != "label")
ok, problems = vc(dict(bare, thread="no-such-thread", session="20261008-120000"))
check("a request with no label passes; a `thread` is accepted and dropped, "
      "naming nothing the validator reads; a session rides along",
      problems == [] and "thread" not in ok and "label" not in ok
      and ok["session"] == "20261008-120000")
ok, problems = vc(dict(good, export=["results/agg/summary.csv"]))
check("a csv whose matching entry says aggregate exports",
      problems == [] and ok["export"] == ["results/agg/summary.csv"])
ok, problems = vc(dict(good, export=["results/rows.csv"]))
check("a csv matched without `aggregate` is refused, naming tutorboard.json",
      ok is None and any("tutorboard.json" in p and "aggregate" in p
                         for p in problems))

cases = (
    ("an id that is not an id", dict(good, id="Has Spaces")),
    ("an id already filed", good, ("2026-10-03-knn-sweep",)),
    ("a label that is not a slug", dict(good, label="Has Spaces")),
    ("a session that is not an id", dict(good, session="../x")),
    ("a recipe that is not tracked", dict(good, recipe="slurm/new.sbatch")),
    ("a recipe that is not a .sbatch", dict(good, recipe="slurm/other.sh")),
    ("a recipe outside the workspace", dict(good, recipe="../x.sbatch")),
    ("an undeclared variable", dict(good, env={"DATA": "x"})),
    ("a value its pattern does not match", dict(good, env={"REDRAW": "2"})),
    ("a comma smuggling a second variable",
     dict(good, env={"EMBEDDER": "a,LD_PRELOAD=/x"})),
    ("an export no entry approves", dict(good, export=["results/other.png"])),
    ("a csv approved without aggregate", dict(good, export=["results/rows.csv"])),
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

everything = dict(good, id="BAD", label="Ghost!", recipe="slurm/new.sbatch",
                  env={"DATA": "x"}, export=["results/rows.csv"],
                  produces=["../x"], extra=1)
ok, problems = vc(everything)
check("and every problem comes back at once, not the first",
      ok is None and len(problems) >= 6)
said = " ".join(problems)
check("each named: the id, the label, the recipe, the key, the produces path",
      "BAD" in said and "Ghost!" in said and "slurm/new.sbatch" in said
      and "DATA" in said and "../x" in said and "`extra`" in said)

turn = {"id": "2026-10-03-knn-turn", "kind": "turn", "thread": "knn",
        "brief": "Read dimension_importance.json and say whether L1 took."}
check("a turn request is refused, in one sentence naming the policy: no "
      "hosted model call on an institute machine",
      vc(turn) == (None, [jobs.NO_TURN])
      and "institute machine" in jobs.NO_TURN
      and "projects/libr-local-llm/docs/deepseek-egress.md" in jobs.NO_TURN)
check("whatever the workspace's tutorboard.json says",
      vc(turn, colibri=True) == (None, [jobs.NO_TURN]))

# --- `fixes`: a diagnostic or a rerun, linked to the request that failed first --
origin = "2026-10-03-knn-sweep"
fix = dict(good, id="2026-10-03-knn-fix", fixes=origin)
check("a turn carrying `fixes` is refused: no cluster turn diagnoses",
      vc(dict(turn, fixes=origin)) == (None, [jobs.NO_TURN]))
check("a `fixes` that is not a request id is refused",
      any("`fixes`" in p for p in vc(dict(fix, fixes="BAD ID"))[1]))
check("and so is one naming the request itself",
      vc(dict(fix, fixes=fix["id"]))[0] is None)
ok, problems = vc(dict(good, id="2026-10-03-knn-rerun", fixes=origin))
check("a recipe with `fixes` passes, carrying it",
      problems == [] and ok["fixes"] == origin)
check("a colibri request has no `fixes`",
      any("`fixes`" in p for p in jobs.validate(
          {"id": "c-1", "kind": "colibri", "label": "knn", "brief": "x",
           "fixes": origin}, ALLOWED, tracked, declared_clean, (),
          colibri=True)[1]))

failed_first = dict(good, id=origin)
on_disk = [failed_first]
failed = {origin}
check("fix_problems: no `fixes`, no problems",
      jobs.fix_problems(good, on_disk, failed) == [])
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
check("fix_problems: a `fixes` naming another label's request is allowed: "
      "labels name work, they do not fence it",
      jobs.fix_problems(fix, [dict(failed_first, label="tripod")],
                        failed) == [])
diagnostic = dict(fix, recipe="slurm/diagnose.sbatch", env={})
two_prior = on_disk + [dict(diagnostic, id="f-1", filed=1.0),
                       dict(fix, id="f-2", filed=2.0)]
three_prior = two_prior + [dict(fix, id="f-3", filed=3.0)]
check("fix_problems: two attempts before it, still allowed",
      jobs.fix_problems(dict(fix, filed=3.0), two_prior, failed) == [])
said = jobs.fix_problems(dict(fix, filed=4.0), three_prior, failed)
check("fix_problems: three before it, a diagnostic and two reruns, and the "
      "fourth is refused at the cap", len(said) == 1 and "cap is 3" in said[0]
      and jobs.fix_problems(dict(diagnostic, filed=4.0), three_prior,
                            failed) != [])
check("fix_problems: the cluster checking one filed counts only those "
      "before it", jobs.fix_problems(dict(fix, id="f-3", filed=3.0),
                                     three_prior, failed, mine=True) == [])
said = jobs.fix_problems(fix, on_disk, set())
check("fix_problems: a `fixes` naming a request with no failed report is "
      "refused, for a diagnostic and a rerun alike",
      len(said) == 1 and "saying it failed" in said[0]
      and jobs.fix_problems(diagnostic, on_disk, ()) != [])

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
          json.dumps(dict(good, id="r1", filed=5.0, thread="knn")))
    threads._cache.clear()
    view = jobs.view(ws)
    check("the view holds the local job and the request, each once",
          sorted(view) == ["77", "relay:r1"])
    check("a request with no report reads REQUESTED, with its label, the "
          "thread an older request carried, and its cmd",
          view["relay:r1"]["state"] == "REQUESTED"
          and view["relay:r1"]["thread"] == "knn"
          and view["relay:r1"]["label"] == "knn"
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
          and jobs.new_id("knn", "x", {jobs.new_id("knn", "x")}).endswith("-2")
          and jobs.new_id("", "x", (), now=0).endswith("-x"))

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
    write(os.path.join(proj, "slurm", "diagnose.sbatch"),
          "#!/bin/bash\necho 'RELAY: has RESULTS_DIR entries 0'\n")
    write(os.path.join(proj, "notes.md"), "draft\n")
    write(threads.path(proj), json.dumps(SPINE))
    write(os.path.join(proj, "tutorboard.json"), json.dumps(
        {"name": "Proj", "relay": {"exports": [{"glob": "results/*.png"}]}}))
    git(top, "add", "-A")
    git(top, "commit", "-q", "-m", "start")
    git(top, "remote", "add", "origin", origin)
    git(top, "push", "-q", "-u", "origin", "main")
    write(os.path.join(top, "elsewhere", "notes.md"), "draft\n")
    git(top, "add", "-A")
    git(top, "commit", "-q", "-m", "elsewhere")
    git(top, "push", "-q")
    # Work in flight outside the subject, which the request commit must leave
    # alone. Under the subject it would stop the filing (below).
    write(os.path.join(top, "elsewhere", "notes.md"), "draft, edited\n")
    write(os.path.join(top, "elsewhere", "scratch.py"), "x = 1\n")
    git(top, "add", "elsewhere/scratch.py")

    env = dict(os.environ, TUTOR_SLURM="0",
               TUTORBOARD_SESSION=os.path.join(base, "sessions",
                                               "20261008-120000"))

    def board(*args):
        p = subprocess.run([sys.executable, BOARD] + list(args), cwd=proj,
                           env=env, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=180)
        return p.returncode, p.stdout.decode("utf-8", "replace")

    code, out = board("job", "knn", "--", "slurm/sweep.sbatch")
    check("a thread named as a bare word is refused: work is named --label",
          code == 1 and "--label" in out
          and not os.path.isdir(os.path.join(proj, "relay")))
    code, out = board("job", "--", "sbatch", "slurm/sweep.sbatch")
    check("on the Mac a bare sbatch is an error, naming the recipe form",
          code == 1 and "no Slurm" in out and "<recipe.sbatch>" in out)
    code, out = board("job", "--label", "knn", "--", "slurm/sweep.sbatch",
                      "DATA=/x")
    check("an undeclared variable is refused before anything is committed",
          code == 1 and "DATA" in out
          and not os.path.isdir(os.path.join(proj, "relay")))
    head = git(top, "rev-parse", "HEAD").strip()
    # A tracked file under the subject differing from HEAD: nothing is filed.
    write(os.path.join(proj, "notes.md"), "draft, edited\n")
    code, out = board("job", "--label", "knn", "--", "slurm/sweep.sbatch",
                      "EMBEDDER=bge-small")
    check("a dirty subject files nothing, saying board push first",
          code == 1 and "board push first" in out and "notes.md" in out
          and not os.path.isdir(os.path.join(proj, "relay"))
          and git(top, "rev-parse", "HEAD").strip() == head)
    write(os.path.join(proj, "scratch.py"), "x = 1\n")
    git(top, "add", "research/Proj/scratch.py")
    git(top, "checkout", "--", "research/Proj/notes.md")
    code, out = board("job", "--label", "knn", "--", "slurm/sweep.sbatch",
                      "EMBEDDER=bge-small")
    check("and so does a file staged there and not committed",
          code == 1 and "board push first" in out and "scratch.py" in out
          and not os.path.isdir(os.path.join(proj, "relay")))
    git(top, "rm", "-q", "--cached", "research/Proj/scratch.py")
    os.remove(os.path.join(proj, "scratch.py"))
    code, out = board("job", "--label", "knn",
                      "--produces", "results/knn/best.json",
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
          " M elsewhere/notes.md" in status
          and "A  elsewhere/scratch.py" in status)
    filed = jobs.requests(proj)
    check("the request on disk is the contract's shape",
          len(filed) == 1 and filed[0]["kind"] == "recipe"
          and filed[0]["env"] == {"EMBEDDER": "bge-small"}
          and filed[0]["export"] == ["results/sweep.png"]
          and filed[0]["produces"] == ["results/knn/best.json"]
          and isinstance(filed[0]["filed"], float)
          and jobs.check(proj, filed[0], mine=True)[1] == [])
    check("stamped with the commit it was filed after, HEAD before its own",
          filed[0].get("commit") == head)
    check("carrying its label and the session $TUTORBOARD_SESSION names, "
          "and no thread", filed[0].get("label") == "knn"
          and filed[0].get("session") == "20261008-120000"
          and "thread" not in filed[0])
    code, out = board("job", "--show")
    check("`board job --show` lists the request", code == 0
          and "relay:" in out and "REQUESTED" in out)

    code, out = board("ask-cluster", "knn", "Why did L1 keep every dimension?")
    check("ask-cluster is retired, and names `board diagnose`",
          code == 2 and "retired" in out and "board diagnose" in out)

    # --- `--fixes`: the Mac files a diagnostic, then the rerun ----------------
    first = filed[0]["id"]
    code, out = board("diagnose", "--fixes", first, "--",
                      "slurm/diagnose.sbatch")
    check("`--fixes` naming a request with no failed report is refused",
          code == 1 and "saying it failed" in out
          and len(jobs.requests(proj)) == 1)
    write(os.path.join(proj, "relay", "reports", first + ".json"),
          json.dumps({"id": first, "state": "failed", "exit": "1:0"}))
    code, out = board("diagnose", "--fixes", first, "--",
                      "slurm/diagnose.sbatch")
    fixed = [r for r in jobs.requests(proj) if r.get("fixes")]
    check("`board diagnose --fixes` files it as `board job` would, naming "
          "the request", code == 0 and len(fixed) == 1
          and fixed[0]["fixes"] == first and fixed[0]["kind"] == "recipe")
    code, out = board("job", "--label", "other", "--", "slurm/sweep.sbatch",
                      "EMBEDDER=bge-small")
    check("then a plain rerun is refused, naming the flag, whatever its label",
          code == 1 and "--fixes %s" % first in out
          and len(jobs.requests(proj)) == 2)
    code, out = board("job", "--label", "knn", "--fixes", first, "--",
                      "slurm/sweep.sbatch", "EMBEDDER=bge-small")
    rerun = [r for r in jobs.requests(proj)
             if r.get("kind") == "recipe" and r.get("fixes")]
    check("`board job --fixes` files the rerun, naming it too",
          code == 0 and len(rerun) == 2 and rerun[-1]["fixes"] == first
          and rerun[-1]["env"] == {"EMBEDDER": "bge-small"})
    p = subprocess.run([sys.executable, BOARD, "job", "--fixes", first,
                        "--", "slurm/sweep.sbatch"], cwd=proj,
                       env=dict(env, TUTOR_SLURM="1"), stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=60)
    check("and with Slurm `--fixes` is refused: it links a relay request",
          p.returncode == 1 and b"--fixes" in p.stdout)

    # --- `board thread export` is retired ----------------------------------------
    code, out = board("thread", "export", "tripod", "results/t.csv")
    check("`board thread export` is retired, naming relay.exports and asking "
          "the owner's question", code == 1 and "retired" in out
          and "relay.exports" in out
          and "May results/t.csv be published?" in out)
    check("and it wrote nothing to the thread file",
          threads.thread(threads.read(proj)[0], "tripod")["exports"] == [])
finally:
    shutil.rmtree(base, ignore_errors=True)

# --- a subject with no thread file -----------------------------------------------------
bare_base = tempfile.mkdtemp(prefix="tutor-nothread-")
try:
    origin = os.path.join(bare_base, "origin.git")
    subprocess.run(["git", "init", "-q", "--bare", origin], check=True)
    top = os.path.join(bare_base, "repo")
    os.makedirs(top)
    git(top, "init", "-q", "-b", "main")
    git(top, "config", "user.email", "t@example.com")
    git(top, "config", "user.name", "t")
    subj = os.path.join(top, "projects", "Plain")
    write(os.path.join(subj, ".gitignore"), "results/\nphi/\n")
    write(os.path.join(subj, "slurm", "sweep.sbatch"),
          RECIPE.replace("#RELAY-VAR PATH .*\n", ""))
    write(os.path.join(subj, "tutorboard.json"), json.dumps(
        {"name": "Plain", "relay": {"colibri": True,
                                    "exports": [{"glob": "results/*.png"}]}}))
    git(top, "add", "-A")
    git(top, "commit", "-q", "-m", "start")
    git(top, "remote", "add", "origin", origin)
    git(top, "push", "-q", "-u", "origin", "main")
    check("the fixture subject has no thread file",
          not os.path.exists(os.path.join(subj, "threads.json")))
    ok, problems = jobs.check(subj, {
        "id": "2026-10-08-sweep", "kind": "recipe",
        "recipe": "slurm/sweep.sbatch", "env": {"EMBEDDER": "bge-small"},
        "produces": [], "export": ["results/a.png"]})
    check("a request with no thread validates where no threads.json exists",
          problems == [] and ok["export"] == ["results/a.png"])
    ok, problems = jobs.check(subj, dict(
        {"id": "2026-10-08-sweep", "kind": "recipe",
         "recipe": "slurm/sweep.sbatch"}, thread="anything-at-all"))
    check("and one naming a thread no file declares validates too: the key "
          "is accepted and ignored", problems == [] and "thread" not in ok)
    check("`kind: turn` is refused there all the same",
          jobs.check(subj, {"id": "t-9", "kind": "turn", "brief": "x"})
          == (None, [jobs.NO_TURN]))

    benv = dict(os.environ, TUTOR_SLURM="0")
    benv.pop("TUTORBOARD_SESSION", None)

    def bboard(*args, **extra):
        p = subprocess.run([sys.executable, BOARD] + list(args), cwd=subj,
                           env=dict(benv, **extra), stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=180)
        return p.returncode, p.stdout.decode("utf-8", "replace")

    code, out = bboard("colibri", "--label", "rows", "--session",
                       "20261008-090000", "count the rows per site")
    filed = jobs.requests(subj)
    check("on the Mac `board colibri` files a colibri request in a subject "
          "with no threads.json", code == 0 and len(filed) == 1
          and filed[0]["kind"] == "colibri" and filed[0]["label"] == "rows"
          and filed[0]["session"] == "20261008-090000"
          and "thread" not in filed[0]
          and git(top, "rev-parse", "HEAD").strip()
          == git(origin, "rev-parse", "main").strip())

    # On the cluster it queues the task itself: a fake squeue (no
    # generation up) and a fake coli-up, in this test's own queue.
    fakes = os.path.join(bare_base, "bin")
    write(os.path.join(fakes, "squeue"), "#!/bin/sh\nexit 0\n")
    write(os.path.join(fakes, "coli-up"), "#!/bin/sh\necho submitted as job 555\n")
    for name in ("squeue", "coli-up"):
        os.chmod(os.path.join(fakes, name), 0o755)
    queue = os.path.join(bare_base, "queue")
    os.makedirs(os.path.join(queue, "state"))
    code, out = bboard("colibri", "--label", "rows", "count the rows again",
                       TUTOR_SLURM="1", COLI_QUEUE_ROOT=queue,
                       COLI_STATE_DIR=os.path.join(queue, "state"),
                       COLI_UP=os.path.join(fakes, "coli-up"),
                       PATH=fakes + os.pathsep + os.environ["PATH"])
    from tutorboard import colibri
    tasks = colibri.tasks(queue)
    check("on the cluster `board colibri` files a task with the label, and "
          "starts a generation", code == 0 and len(tasks) == 1
          and tasks[0]["label"] == "rows" and "555" in out)
finally:
    shutil.rmtree(bare_base, ignore_errors=True)

# --- the real repository -------------------------------------------------------------
recipe = os.path.join(REPO, "research", "TRD-EHR", "slurm_jobs", "quick_runs",
                      "neighbor_count_sweep.sbatch")
with open(recipe, encoding="utf-8") as fh:
    names, said = jobs.declarations(fh.read())
check("TRD-EHR's neighbour sweep declares EMBEDDER and REDRAW for the relay",
      said == [] and sorted(names) == ["EMBEDDER", "REDRAW"])
with open(os.path.join(REPO, "research", "TRD-EHR", "slurm_jobs", "quick_runs",
                       "diagnose.sbatch"), encoding="utf-8") as fh:
    names, said = jobs.declarations(fh.read())
check("TRD-EHR has a diagnostic recipe, declaring EMBEDDER, LOOK and MODULE",
      said == [] and sorted(names) == ["EMBEDDER", "LOOK", "MODULE"]
      and jobs.diagnostics(os.path.join(REPO, "research", "TRD-EHR"))
      == [("slurm_jobs/quick_runs/diagnose.sbatch",
           ["EMBEDDER", "LOOK", "MODULE"])])
for ws in ("research/TRD-EHR", "research/PSYCH-ASR", "projects/libr-local-llm"):
    root = os.path.join(REPO, ws)
    if os.path.isdir(root):
        check("%s: git would see a request" % ws, jobs.request_visible(root) == "")

# --- a request is public the moment it is pushed --------------------------------
leaky = tempfile.mkdtemp(prefix="tutor-leak-")
try:
    req = {"id": "x-1", "kind": "colibri", "label": "knn",
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
