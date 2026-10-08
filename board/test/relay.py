#!/usr/bin/env python3
"""The cluster's relay: a request pulled, run, ended and reported, through git.

What the checks are about:

  * A REQUEST RUNS. Pulled from origin, checked again, submitted wrapped, seen
    running, ended from squeue and its exit file, its exports copied, and its
    report pushed -- which the Mac's merged registry then reads.
  * A REFUSAL IS A REPORT. A bad request is never submitted; its report says
    every problem.
  * TWO PASSES AT ONCE: one runs, the other skips.
  * AN EXPORT OVER THE CAP is refused in the report and never copied.
  * A DIRTY TREE SKIPS THE PASS, and `relay/state.json` says why.
  * A REJECTED PUSH is retried by the next pass, rebased, never forced.
  * A REPORT IS PUBLIC: `RELAY:` lines only, paths redacted, a crash by its
    exception type.
  * NO HOSTED MODEL RUNS HERE: a `turn` request is refused by the policy.
  * A COLIBRI TASK IS READ-ONLY: done with no change git can see, it
    completes with its `RELAY:` lines; any change fails it, uncommitted.

Git is real (a bare origin and two clones); Slurm is a table.
"""

import fcntl
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
sys.path.insert(0, ROOT)
from tutorboard import jobs, leaving, relay                            # noqa: E402
from tutorboard.course import threads                                  # noqa: E402

TUTOR = os.path.join(ROOT, "bin", "tutor")
fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


def write(path, text, mode="w"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, mode, encoding="utf-8") as fh:
        fh.write(text)


def git(cwd, *args):
    p = subprocess.run(["git"] + list(args), cwd=cwd, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, check=False)
    return p.stdout.decode("utf-8", "replace").strip()


def load(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


class Done:
    def __init__(self, code=0, out="", err=""):
        self.returncode, self.stdout, self.stderr = code, out, err


class Slurm:
    """sbatch, scontrol and squeue from a table. `queue` is what squeue
    holds; `run_job` executes a submitted wrapper the way a node would."""

    def __init__(self):
        self.calls, self.envs, self.scripts = [], [], {}
        self.queue = {}
        self.next_id = 500
        self.slow = 0

    def __call__(self, argv, **kw):
        self.calls.append(list(argv))
        name = os.path.basename(argv[0])
        if name == "sbatch":
            if self.slow:
                time.sleep(self.slow)
            self.next_id += 1
            jid = str(self.next_id)
            self.envs.append(kw.get("env"))
            exported = {}
            for a in argv:
                if a.startswith("--export=ALL"):
                    for pair in a.split(",")[1:]:
                        k, _, v = pair.partition("=")
                        exported[k] = v
            self.scripts[jid] = (argv[-1], kw.get("cwd"), exported)
            self.queue[jid] = "PENDING"
            return Done(0, jid + "\n")
        if name == "scontrol":
            return Done(0, "JobId=%s StdOut=logs/job-%%j.out "
                           "StdErr=logs/job-%%j.err\n" % argv[-1])
        if name == "squeue":
            return Done(0, "".join("%s|%s\n" % kv
                                   for kv in sorted(self.queue.items())))
        raise AssertionError("unexpected command %r" % argv)

    def run_job(self, jid):
        script, cwd, exported = self.scripts[jid]
        os.makedirs(os.path.join(cwd, "logs"), exist_ok=True)
        with open(os.path.join(cwd, "logs", "job-%s.out" % jid), "w") as out, \
                open(os.path.join(cwd, "logs", "job-%s.err" % jid), "w") as err:
            p = subprocess.run(["bash", script], cwd=cwd, stdout=out,
                               stderr=err, env=dict(os.environ, **exported))
        self.queue.pop(jid, None)
        return p.returncode


RECIPE = """#!/bin/bash
#SBATCH --time=00:05:00
#SBATCH --partition=c3
#RELAY-VAR EMBEDDER [a-z0-9-]{1,40}
#RELAY-VAR SIZE [0-9]{1,8}

set -e
mkdir -p results
echo "RELAY: auc 0.71 for $EMBEDDER"
echo "RELAY: wrote /media/lab/storage/x.csv"
echo "RELAY: SESSION-17 by name"
echo "row-level noise that must not cross"
head -c "${SIZE:-100}" /dev/zero > results/sweep.png
head -c 6000000 /dev/zero > results/big.png
echo '{"auc": 0.71}' > results/out.json
"""

CRASH = """#!/bin/bash
#SBATCH --time=00:05:00
echo "starting"
echo 'Traceback (most recent call last):' >&2
echo '  File "fit.py", line 3, in <module>' >&2
echo 'ValueError: patient 1234 has a bad value' >&2
exit 1
"""

DIAGNOSE = """#!/bin/bash
#SBATCH --time=00:05:00
echo "RELAY: has RESULTS_DIR/trained_models entries 0"
"""

SPINE = {
    "version": 1,
    "deliverables": [{"id": "paper1", "title": "Paper 1", "doc": ""}],
    "threads": [
        {"id": "knn", "deliverable": "paper1", "title": "Neighbours",
         "files": ["src/knn.py", "slurm/crash.sbatch"],
         "exports": [{"path": "results/sweep.png", "aggregate": True},
                     {"path": "results/big.png", "aggregate": True},
                     "results/rows.csv"]},
    ],
}

# The lab's policy, standing in: it names session content by a token.
POLICY = "import re\n\ndef names_phi(text):\n    return bool(re.search(r'SESSION-\\d+', str(text)))\n"

base = tempfile.mkdtemp(prefix="tutor-relay-")
saved_env = dict(os.environ)
try:
    origin = os.path.join(base, "origin.git")
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", origin],
                   check=True)
    seed = os.path.join(base, "seed")
    os.makedirs(seed)
    git(seed, "init", "-q", "-b", "main")
    for k, v in (("user.email", "t@example.com"), ("user.name", "t")):
        git(seed, "config", k, v)
    write(os.path.join(seed, ".gitignore"),
          "**/relay/state/\n/relay/state.json\n/relay/.lock\nai-config/\n")
    proj = os.path.join(seed, "research", "Proj")
    write(os.path.join(proj, "tutorboard.json"),
          json.dumps({"name": "Proj"}))
    write(os.path.join(proj, "AI_INSTRUCTIONS.md"), "# contract\n")
    write(os.path.join(proj, ".gitignore"),
          "live/\nresults/\nlogs/\n!exports/**\n")
    write(os.path.join(proj, "threads.json"), json.dumps(SPINE))
    write(os.path.join(proj, "slurm", "sweep.sbatch"), RECIPE)
    write(os.path.join(proj, "slurm", "crash.sbatch"), CRASH)
    write(os.path.join(proj, "slurm", "diagnose.sbatch"), DIAGNOSE)
    write(os.path.join(proj, "jobs.jsonl"), "")
    git(seed, "add", "-A")
    git(seed, "commit", "-q", "-m", "seed")
    git(seed, "remote", "add", "origin", origin)
    git(seed, "push", "-q", "-u", "origin", "main")

    def clone(name):
        where = os.path.join(base, name)
        git(base, "clone", "-q", origin, where)
        for k, v in (("user.email", "%s@example.com" % name),
                     ("user.name", name)):
            git(where, "config", k, v)
        return where

    mac, cluster = clone("mac"), clone("cluster")
    mws = os.path.join(mac, "research", "Proj")
    cws = os.path.join(cluster, "research", "Proj")
    write(os.path.join(cluster, "ai-config", "policy", "phi.py"), POLICY)

    def file_from_mac(req):
        """The Mac's side of the code: checked, written, committed, pushed."""
        git(mac, "pull", "-q", "--rebase")
        req = dict(req, filed=time.time())
        ok, problems = jobs.check(mws, req)
        path, done, said = jobs.file_request(mws, ok or req, push=False)
        git(mac, "push", "-q")
        return ok, problems

    def origin_report(rid):
        return git(origin, "show", "main:research/Proj/relay/reports/%s.json"
                   % rid)

    slurm = Slurm()
    os.environ["SLURM_JOB_ID"] = "999"          # as inside a scrontab job
    # Colibri's queue is this test's, empty: never this machine's real one.
    os.environ["COLI_QUEUE_ROOT"] = os.path.join(base, "queue")
    os.makedirs(os.environ["COLI_QUEUE_ROOT"])

    def run_pass(now=None):
        return relay.run_pass(cluster, run=slurm, now=now)

    # --- a request runs --------------------------------------------------------
    good = {"id": "r1", "kind": "recipe", "thread": "knn",
            "recipe": "slurm/sweep.sbatch",
            "env": {"EMBEDDER": "bge-small", "SIZE": "100"},
            "produces": ["results/out.json", "results/none.json"],
            "export": ["results/sweep.png", "results/big.png"]}
    ok, problems = file_from_mac(good)
    check("the Mac side files the request clean", problems == [])
    got = run_pass()
    check("the pass pulls it and submits it", got["submitted"] == ["r1"]
          and not got["skipped"] and not got["error"])
    rep = load(os.path.join(cws, "relay", "reports", "r1.json"))
    jid = rep and rep.get("jobid")
    check("its report says submitted, with the Slurm id",
          rep and rep["state"] == "submitted" and jid in slurm.scripts)
    sent = [c for c in slurm.calls if os.path.basename(c[0]) == "sbatch"][-1]
    check("sbatch got the wrapper and only the declared variables",
          sent[-1].endswith(os.path.join("relay", "state", "r1.sbatch"))
          and "--export=ALL,EMBEDDER=bge-small,SIZE=100" in sent)
    check("from an environment without the pass's own Slurm variables",
          slurm.envs[-1] is not None and "SLURM_JOB_ID" not in slurm.envs[-1])
    check("and the report reached origin", '"submitted"' in origin_report("r1"))
    check("the job is registered in the relay's ignored registry, not the "
          "tracked one", "r1" in json.dumps(jobs.records(
              cws, jobs.relay_registry(cws)))
          and open(os.path.join(cws, "jobs.jsonl")).read() == ""
          and git(cluster, "check-ignore", "-q",
                  "research/Proj/relay/state/jobs.jsonl") == "")

    slurm.queue[jid] = "RUNNING"
    run_pass()
    check("squeue saying RUNNING moves the report to running",
          load(os.path.join(cws, "relay", "reports", "r1.json"))["state"]
          == "running")
    check("and nothing else is submitted twice",
          sum(1 for c in slurm.calls if os.path.basename(c[0]) == "sbatch") == 1)

    check("the wrapped job runs and exits 0", slurm.run_job(jid) == 0)
    got = run_pass()
    rep = load(os.path.join(cws, "relay", "reports", "r1.json"))
    check("gone from squeue with its exit file: completed, exit 0:0",
          got["ended"] == ["r1"] and rep["state"] == "completed"
          and rep["exit"] == "0:0")
    check("it names which produces exist and which do not",
          rep["produced"] == ["results/out.json"]
          and rep["missing"] == ["results/none.json"])
    check("an export inside the cap is copied to exports/ and committed",
          rep["exported"] == ["results/sweep.png"]
          and os.path.isfile(os.path.join(cws, "exports", "results", "sweep.png"))
          and "research/Proj/exports/results/sweep.png" in git(
              cluster, "ls-files"))
    check("an export over the 5 MB cap is refused in the report, never copied",
          [r["path"] for r in rep.get("export_refused") or []]
          == ["results/big.png"]
          and "cap" in rep["export_refused"][0]["why"]
          and not os.path.exists(os.path.join(cws, "exports", "results",
                                              "big.png")))
    check("the report carries only RELAY: lines, a path made <path>, and "
          "what the policy matches withheld",
          rep["relay"] == ["auc 0.71 for bge-small", "wrote <path>"])
    whole = json.dumps(rep)
    check("and no other line of the log", "row-level noise" not in whole
          and "/media" not in whole and "SESSION-17" not in whole)
    check("its note is a sentence the code wrote",
          "completed" in rep["note"] and "1 exported, 1 refused" in rep["note"])
    check("the commit touches only relay/reports/ and exports/",
          all(p.startswith(("research/Proj/relay/reports/",
                            "research/Proj/exports/"))
              for p in git(cluster, "show", "--name-only", "--format=",
                           "HEAD").split()))
    check("and carries no trailer", "Co-Authored" not in git(
        cluster, "log", "-1", "--format=%B"))
    git(mac, "pull", "-q", "--rebase")
    threads._cache.clear()
    view = jobs.view(mws)
    check("the Mac's merged registry reads it COMPLETED, exports and all",
          view["relay:r1"]["state"] == "COMPLETED"
          and view["relay:r1"]["exported"] == ["results/sweep.png"]
          and os.path.isfile(os.path.join(mws, "exports", "results",
                                          "sweep.png")))
    check("and its thread is no longer requested or running",
          threads.stages(mws)["knn"]["status"] not in ("requested", "running"))

    # --- a refusal ---------------------------------------------------------------
    bad = dict(good, id="r2", env={"EMBEDDER": "bge-small", "DATA": "x"})
    write(os.path.join(mws, "relay", "requests", "r2.json"), json.dumps(bad))
    git(mac, "add", "-A")
    git(mac, "commit", "-q", "-m", "a request the Mac's check would refuse")
    git(mac, "push", "-q")
    n = len(slurm.scripts)
    got = run_pass()
    rep = load(os.path.join(cws, "relay", "reports", "r2.json"))
    check("a bad request is refused, not submitted",
          got["refused"] == ["r2"] and len(slurm.scripts) == n
          and rep["state"] == "refused")
    check("and its report names the undeclared key",
          any("DATA" in p for p in rep["problems"]))
    check("and is pushed", '"refused"' in origin_report("r2"))

    # --- two passes at once --------------------------------------------------------
    held = open(os.path.join(cluster, relay.LOCK), "a+")
    fcntl.flock(held.fileno(), fcntl.LOCK_EX)
    check("a pass while another holds the lock skips",
          run_pass()["skipped"] == "another pass holds the lock")
    held.close()
    file_from_mac(dict(good, id="r3"))
    slurm.slow = 1.0
    results = []
    workers = [threading.Thread(target=lambda: results.append(run_pass()))
               for _ in range(2)]
    for w in workers:
        w.start()
    for w in workers:
        w.join()
    slurm.slow = 0
    check("two passes started together: one submits, the other skips",
          sorted(bool(r.get("skipped")) for r in results) == [False, True]
          and sum(1 for c in slurm.calls if os.path.basename(c[0]) == "sbatch"
                  and c[-1].endswith("r3.sbatch")) == 1)

    # --- a job that leaves squeue without its exit file -----------------------
    jid3 = load(os.path.join(cws, "relay", "reports", "r3.json"))["jobid"]
    slurm.queue.pop(jid3)
    later = time.time() + jobs.GRACE + 30
    run_pass(now=later)
    rep = load(os.path.join(cws, "relay", "reports", "r3.json"))
    check("a job just gone without its exit file is not called on one look",
          rep["state"] == "submitted")
    run_pass(now=later + jobs.GONE_GRACE + 1)
    rep = load(os.path.join(cws, "relay", "reports", "r3.json"))
    check("a job gone from squeue without an exit file failed, and the note "
          "says it died", rep["state"] == "failed" and rep["exit"] == ""
          and "time limit" in rep["note"])
    check("and nothing it was to export is copied",
          [r["why"] for r in rep["export_refused"]]
          == ["the job did not complete"] * 2)

    # --- a crash is reported by its exception type ----------------------------
    file_from_mac({"id": "r4", "kind": "recipe", "thread": "knn",
                   "recipe": "slurm/crash.sbatch"})
    run_pass()
    jid4 = load(os.path.join(cws, "relay", "reports", "r4.json"))["jobid"]
    slurm.run_job(jid4)
    run_pass()
    rep = load(os.path.join(cws, "relay", "reports", "r4.json"))
    check("a crash is failed, exit 1:0, carrying ValueError and not its message",
          rep["state"] == "failed" and rep["exit"] == "1:0"
          and rep.get("error") == "ValueError"
          and "1234" not in json.dumps(rep) and "starting" not in json.dumps(rep))

    # --- a dirty tree skips the pass -------------------------------------------
    file_from_mac(dict(good, id="r5"))
    write(os.path.join(cws, "AI_INSTRUCTIONS.md"), "# an owner's edit\n", "a")
    got = run_pass()
    st = load(os.path.join(cluster, "relay", "state.json"))
    check("an edit outside the cluster's paths skips the pass",
          "AI_INSTRUCTIONS.md" in got["skipped"]
          and not os.path.exists(os.path.join(cws, "relay", "requests",
                                              "r5.json")))
    check("and relay/state.json says so", "AI_INSTRUCTIONS.md" in st["skipped"])
    check("the owner's edit is left where it was",
          "an owner's edit" in open(os.path.join(cws, "AI_INSTRUCTIONS.md")).read())
    git(cluster, "checkout", "--", "research/Proj/AI_INSTRUCTIONS.md")
    write(os.path.join(cws, "jobs.jsonl"), '{"jobid": "1", "thread": "knn"}\n',
          "a")
    got = run_pass()
    check("but the job registry, which only a Slurm machine appends to, does "
          "not skip it", not got["skipped"] and "r5" in got["submitted"])
    check("and is not the relay's to commit",
          "M research/Proj/jobs.jsonl" in git(cluster, "status", "--porcelain"))
    git(cluster, "checkout", "--", "research/Proj/jobs.jsonl")
    write(os.path.join(cluster, "notes.md"), "x\n")
    git(cluster, "add", "notes.md")
    git(cluster, "commit", "-q", "-m", "an unpushed commit of the owner's")
    got = run_pass()
    check("an unpushed commit outside the cluster's paths skips it too",
          "notes.md" in got["skipped"])
    git(cluster, "reset", "-q", "--hard", "HEAD~1")

    # --- a rejected push is retried ---------------------------------------------
    flag = os.path.join(base, "reject")
    hook = os.path.join(origin, "hooks", "pre-receive")
    write(hook, "#!/bin/sh\nif [ -e %s ]; then echo rejected >&2; exit 1; fi\n"
          % flag)
    os.chmod(hook, os.stat(hook).st_mode | stat.S_IEXEC)
    file_from_mac(dict(good, id="r6"))
    write(flag, "")
    got = run_pass()
    st = load(os.path.join(cluster, "relay", "state.json"))
    check("a rejected push is recorded, the report kept locally",
          "push rejected" in got["error"] and st["push_pending"] is True
          and os.path.isfile(os.path.join(cws, "relay", "reports", "r6.json"))
          and origin_report("r6").startswith("fatal"))
    os.remove(flag)
    write(os.path.join(mws, "notes.md"), "the Mac moved on\n")
    git(mac, "add", "-A")
    git(mac, "commit", "-q", "-m", "Mac work meanwhile")
    git(mac, "push", "-q")
    got = run_pass()
    st = load(os.path.join(cluster, "relay", "state.json"))
    check("the next pass rebases onto the Mac's commit and pushes it",
          not got["error"] and st["push_pending"] is False
          and '"submitted"' in origin_report("r6")
          and st["last_pushed"] == git(origin, "rev-parse", "main")
          and git(origin, "rev-list", "--count", "main") == git(
              cluster, "rev-list", "--count", "HEAD"))
    check("without forcing: the Mac's commit is still on origin",
          "Mac work meanwhile" in git(origin, "log", "--format=%s", "main"))

    # --- a turn: refused on both machines, by the policy ----------------------
    n = len(slurm.scripts)
    ok, problems = file_from_mac({"id": "t1", "kind": "turn", "thread": "knn",
                                  "brief": "Why did L1 keep every dimension?"})
    got = run_pass()
    t1 = load(os.path.join(cws, "relay", "reports", "t1.json"))
    check("a turn request is refused on the Mac, in one sentence naming the "
          "policy", ok is None and problems == [jobs.NO_TURN]
          and "institute machine" in jobs.NO_TURN
          and "deepseek-egress.md" in jobs.NO_TURN)
    check("and by the cluster, which runs nothing for it",
          "t1" in got["refused"] and t1["state"] == "refused"
          and t1["problems"] == [jobs.NO_TURN] and len(slurm.scripts) == n)
    check("the relay has no turn to run, and the command no --turn",
          not hasattr(relay, "run_turn") and "turn" not in got
          and "--turn" not in open(TUTOR, encoding="utf-8").read().split(
              "def cmd_relay", 1)[1].split("\ndef ", 1)[0])

    # --- a failed recipe: asked with a diagnostic, repaired on the Mac ---------
    file_from_mac({"id": "k1", "kind": "recipe", "thread": "knn",
                   "recipe": "slurm/crash.sbatch"})
    run_pass()
    k1 = load(os.path.join(cws, "relay", "reports", "k1.json"))
    slurm.run_job(k1["jobid"])
    run_pass()
    k1 = load(os.path.join(cws, "relay", "reports", "k1.json"))
    check("a crash recipe fails, by its exception type, and its note names "
          "no cluster turn", k1["state"] == "failed"
          and k1["error"] == "ValueError" and "turn" not in k1["note"]
          and "diagnostic recipe" in k1["note"])
    ok, problems = file_from_mac({"id": "fx1", "kind": "turn", "thread": "knn",
                                  "brief": "Diagnose it.", "fixes": "r2"})
    got = run_pass()
    fx1 = load(os.path.join(cws, "relay", "reports", "fx1.json"))
    check("a turn carrying `fixes` is refused on both machines: no model "
          "diagnoses beside the data",
          jobs.NO_TURN in problems and "fx1" in got["refused"]
          and fx1["state"] == "refused" and jobs.NO_TURN in fx1["problems"])

    before = git(origin, "rev-parse", "main").strip()
    ok, problems = file_from_mac({"id": "dg1", "kind": "recipe",
                                  "thread": "knn",
                                  "recipe": "slurm/diagnose.sbatch",
                                  "fixes": "k1"})
    got = run_pass()
    dg1 = load(os.path.join(cws, "relay", "reports", "dg1.json"))
    check("the Mac files a diagnostic, a recipe like any other, and the pass "
          "submits it", problems == [] and got["submitted"] == ["dg1"])
    slurm.run_job(dg1["jobid"])
    run_pass()
    dg1 = load(os.path.join(cws, "relay", "reports", "dg1.json"))
    touched = set(git(origin, "log", "--name-only", "--format=",
                      "%s..main" % before).split())
    check("it completes with only its RELAY: lines, and publishes its reports "
          "and nothing else", dg1["state"] == "completed"
          and dg1["relay"] == ["has RESULTS_DIR/trained_models entries 0"]
          and touched == {"research/Proj/relay/reports/dg1.json",
                          "research/Proj/relay/requests/dg1.json"})
    git(mac, "pull", "-q", "--rebase")
    rec = dict((r["request"], r) for r in jobs.relayed(mws))["dg1"]
    said = jobs.relay_sense(mws, rec)
    check("the Mac's [repair] line applies what it found, then reruns the "
          "failed recipe with `board job --fixes`",
          said.startswith("[repair]") and "it came back" in said
          and "board push" in said
          and "board job knn --fixes k1 -- slurm/crash.sbatch" in said)
    check("and a plain rerun of the recipe is refused on the Mac meanwhile",
          jobs.open_fix(mws, "knn", "slurm/crash.sbatch") == "k1")

    for rid in ("rk2", "rk3"):
        ok, problems = file_from_mac({"id": rid, "kind": "recipe",
                                      "thread": "knn",
                                      "recipe": "slurm/crash.sbatch",
                                      "fixes": "k1"})
    got = run_pass()
    check("two reruns are submitted: three attempts in all",
          problems == [] and sorted(got["submitted"]) == ["rk2", "rk3"])
    git(mac, "pull", "-q", "--rebase")
    write(os.path.join(mws, "relay", "requests", "dg4.json"), json.dumps(
        {"id": "dg4", "kind": "recipe", "thread": "knn",
         "recipe": "slurm/diagnose.sbatch", "fixes": "k1",
         "filed": time.time()}))
    git(mac, "add", "-A")
    git(mac, "commit", "-q", "-m", "a fourth attempt no Mac would file")
    git(mac, "push", "-q")
    got = run_pass()
    dg4 = load(os.path.join(cws, "relay", "reports", "dg4.json"))
    check("a fourth attempt for one request is refused at the cap, "
          "diagnostic or not", "dg4" in got["refused"]
          and dg4["state"] == "refused"
          and any("cap is 3" in p for p in dg4["problems"]))
    git(mac, "pull", "-q", "--rebase")
    rec = dict((r["request"], r) for r in jobs.relayed(mws))["dg4"]
    said = jobs.relay_sense(mws, rec)
    check("and its [job] line invites no refile",
          "Do not file it again" in said and "owner decides" in said
          and "through `board job`" not in said)
    file_from_mac({"id": "dg5", "kind": "recipe", "thread": "knn",
                   "recipe": "slurm/diagnose.sbatch", "fixes": "r1"})
    got = run_pass()
    dg5 = load(os.path.join(cws, "relay", "reports", "dg5.json"))
    check("the cluster refuses an attempt whose request did not fail",
          dg5["state"] == "refused"
          and any("saying it failed" in p for p in dg5["problems"]))

    # --- what reaches origin is what the pass wrote -------------------------------
    write(os.path.join(cws, "exports", "results", "stray.csv"), "a,b\n1,2\n")
    write(os.path.join(cws, "relay", "reports", "forged.json"), "{}\n")
    file_from_mac(dict(good, id="r8"))
    got = run_pass()
    st = load(os.path.join(cluster, "relay", "state.json"))
    shown = git(origin, "show", "--name-only", "--format=", "main")
    check("a file in exports/ or relay/reports/ no pass wrote is never "
          "committed", "r8.json" in origin_report("r8") or '"submitted"'
          in origin_report("r8"))
    check("and is named in relay/state.json instead",
          "stray.csv" not in shown and "forged.json" not in shown
          and any("stray.csv" in p for p in st["unpublished"])
          and any("forged.json" in p for p in st["unpublished"]))
    os.remove(os.path.join(cws, "exports", "results", "stray.csv"))
    os.remove(os.path.join(cws, "relay", "reports", "forged.json"))

    # --- a malformed request cannot stall or escape -----------------------------
    reqdir = os.path.join(mws, "relay", "requests")
    git(mac, "pull", "-q", "--rebase")
    write(os.path.join(reqdir, "esc.json"), json.dumps(
        {"id": "../../exports/results/x", "kind": "recipe", "thread": "knn",
         "recipe": "slurm/sweep.sbatch", "filed": "yesterday"}))
    write(os.path.join(reqdir, "nul.json"), json.dumps(
        {"id": None, "kind": "recipe", "thread": "knn",
         "recipe": "slurm/sweep.sbatch", "filed": 5}))
    git(mac, "add", "-A")
    git(mac, "commit", "-q", "-m", "two requests no Mac would file")
    git(mac, "push", "-q")
    got = run_pass()
    check("a bad id and a mixed `filed` are refused, not a crash of the pass",
          not got["error"] and sorted(got["refused"]) == ["esc", "nul"]
          and load(os.path.join(cws, "relay", "reports", "esc.json"))[
              "state"] == "refused")
    check("and the report is named for the request's file, never its id",
          not os.path.exists(os.path.join(cws, "exports", "results", "x.json"))
          and load(os.path.join(cws, "relay", "reports", "nul.json"))["id"]
          == "nul")
    before = git(origin, "rev-parse", "main")
    got = run_pass()
    check("and the next pass neither refuses them again nor commits",
          got["refused"] == [] and git(origin, "rev-parse", "main") == before)

    # --- a colibri request: a task, read-only, checked once it is done -------
    from tutorboard import atlas as _atlas, colibri as coli, missions
    git(mac, "pull", "-q", "--rebase")
    write(os.path.join(mws, "tutorboard.json"),
          json.dumps({"name": "Proj", "relay": {"colibri": True}}))
    write(os.path.join(mws, ".gitignore"), "phi/\n", "a")
    git(mac, "add", "-A")
    git(mac, "commit", "-q", "-m", "Proj takes Colibri tasks")
    git(mac, "push", "-q")
    queue = os.environ["COLI_QUEUE_ROOT"]
    os.environ["COLI_STATE_DIR"] = os.path.join(base, "coli-state")
    os.environ["TUTORBOARD_COURSES"] = cluster
    _atlas.forget()
    real_start, real_jobs = coli.start_generation, coli._all_jobs
    coli.start_generation = lambda: ("", "no Slurm in this test")
    coli._all_jobs = lambda: []

    def task_of(rid):
        return [t for t in missions.tasks(queue) if t["request"] == rid][0]

    def colibri_runs(rid, out_text, tracked=(), ignored=()):
        """What a generation does with the task: claims it, writes, prints
        its RELAY: lines behind the fence, finishes it."""
        task = task_of(rid)
        out = os.path.join(base, "sessions", "phi", "tasks",
                           task["id"] + ".out")
        write(out, out_text)
        missions.update_task(queue, task, out=out)
        missions.claim_task(queue, task_of(rid), "101")
        for rel, text in list(tracked) + list(ignored):
            write(os.path.join(cws, rel), text)
        missions.finish_task(queue, task_of(rid), True)

    def pushed_since(sha):
        return set(git(origin, "log", "--name-only", "--format=",
                       "%s..main" % sha).split())
    try:
        file_from_mac({"id": "c1", "kind": "colibri", "thread": "knn",
                       "brief": "grade the diarization of SESSION-1"})
        got = run_pass()
        c1 = load(os.path.join(cws, "relay", "reports", "c1.json"))
        check("a colibri request is queued as a task, and the pass still "
              "publishes", not got["error"] and c1["state"] == "submitted"
              and task_of("c1")["queue"] == "queued"
              and '"submitted"' in origin_report("c1"))
        check("its report never carries the brief",
              "SESSION" not in json.dumps(c1) and "grade" not in json.dumps(c1))
        check("the task keeps what git already saw changed there as its "
              "baseline", task_of("c1")["baseline"] == {})

        colibri_runs("c1", "reading SESSION-1 now\n"
                     "RELAY: graded 12 sessions, mean DER 0.18\n"
                     "RELAY: SESSION-1 was the worst\n"
                     "RELAY: wrote it under /media/lab/phi/grades\n",
                     ignored=[("phi/grades/SESSION-1.json", "{}\n")])
        real_changes = relay.workspace_changes
        relay.workspace_changes = lambda ws: None
        try:
            got = run_pass()
        finally:
            relay.workspace_changes = real_changes
        c1 = load(os.path.join(cws, "relay", "reports", "c1.json"))
        check("where git cannot say, the task stays unchecked and is asked "
              "about next pass", c1["state"] == "running"
              and "check" in c1["note"] and not task_of("c1").get("checked"))
        before = git(origin, "rev-parse", "main")
        got = run_pass()
        c1 = load(os.path.join(cws, "relay", "reports", "c1.json"))
        check("a task that wrote only under the ignored phi/ completes",
              not got["error"] and "c1" in got["ended"]
              and c1["state"] == "completed" and c1["changed"] == 0
              and '"completed"' in origin_report("c1"))
        check("its report carries its RELAY: lines, public: a line the policy "
              "names withheld, a path redacted",
              c1["relay"][0] == "graded 12 sessions, mean DER 0.18"
              and len(c1["relay"]) == 2 and "<path>" in c1["relay"][1]
              and "SESSION" not in json.dumps(c1))
        check("and no diff: nothing it wrote is committed",
              "diff" not in c1 and pushed_since(before)
              == set(["research/Proj/relay/reports/c1.json"]))

        write(os.path.join(cws, "notes", "owner.md"), "the owner's, before\n")
        file_from_mac({"id": "c2", "kind": "colibri", "thread": "knn",
                       "brief": "reconstruct the transcript"})
        run_pass()
        check("the owner's edit from before the task is its baseline",
              list(task_of("c2")["baseline"]) == ["research/Proj/notes/owner.md"])
        colibri_runs("c2", "RELAY: reconstructed 1 transcript\n",
                     tracked=[("AI_INSTRUCTIONS.md", "# edited by a task\n"),
                              ("notes/transcript.txt", "a line of dialogue\n")])
        before = git(origin, "rev-parse", "main")
        got = run_pass()
        c2 = load(os.path.join(cws, "relay", "reports", "c2.json"))
        check("a task that changed what git sees fails, saying why, and the "
              "pass is not skipped for it", not got["skipped"]
              and c2["state"] == "failed" and relay.CHANGED in c2["note"]
              and task_of("c2")["queue"] == "failed")
        check("counting only its own changes, and naming none of them",
              c2["changed"] == 2 and "AI_INSTRUCTIONS" not in json.dumps(c2)
              and "transcript.txt" not in json.dumps(c2)
              and "owner.md" not in json.dumps(c2))
        check("nothing it changed is committed; the changes stay on the "
              "cluster", pushed_since(before)
              == set(["research/Proj/relay/reports/c2.json"])
              and "edited by a task" in open(
                  os.path.join(cws, "AI_INSTRUCTIONS.md")).read()
              and os.path.isfile(os.path.join(cws, "notes", "transcript.txt")))
        checked = task_of("c2")["checked"]
        got = run_pass()
        check("and the next pass neither skips nor checks it again",
              not got["skipped"] and not got["error"]
              and task_of("c2")["checked"] == checked)
        git(mac, "pull", "-q", "--rebase")
        rec = [r for r in jobs.relayed(mws) if r["request"] == "c2"][0]
        said = jobs.relay_sense(mws, rec)
        check("the Mac's [job] line says the task failed its check, by count",
              said.startswith("[job]") and "FAILED its check" in said
              and "2 tracked path(s)" in said and "for the owner" in said)
    finally:
        coli.start_generation, coli._all_jobs = real_start, real_jobs
        git(cluster, "checkout", "--", "research/Proj/AI_INSTRUCTIONS.md")
        shutil.rmtree(os.path.join(cws, "notes"), ignore_errors=True)
        shutil.rmtree(os.path.join(queue, "live"), ignore_errors=True)
        os.environ.pop("TUTORBOARD_COURSES", None)
        os.environ.pop("COLI_STATE_DIR", None)
        _atlas.forget()

    # --- a hold: the owner's edit to a held file does not skip the pass -------
    git(mac, "pull", "-q", "--rebase")
    write(os.path.join(mws, "relay", "holds", "knn.json"), json.dumps(
        {"thread": "knn", "files": ["src/knn.py"], "at": time.time()}))
    write(os.path.join(mws, "src", "knn.py"), "x = 1\n")
    git(mac, "add", "-A")
    git(mac, "commit", "-q", "-m", "knn: hold")
    git(mac, "push", "-q")
    run_pass()
    write(os.path.join(cws, "src", "knn.py"), "x = 2  # the owner, mid-step\n")
    git(mac, "pull", "-q", "--rebase")
    write(os.path.join(mws, "notes.md"), "the Mac pushes elsewhere\n", "a")
    git(mac, "add", "-A")
    git(mac, "commit", "-q", "-m", "Mac work elsewhere")
    git(mac, "push", "-q")
    file_from_mac(dict(good, id="r9"))
    got = run_pass()
    check("an uncommitted edit to a held file does not skip the pass",
          not got["skipped"] and "r9" in got["submitted"]
          and '"submitted"' in origin_report("r9"))
    check("and the edit survives the pull, uncommitted",
          "mid-step" in open(os.path.join(cws, "src", "knn.py")).read()
          and "src/knn.py" in git(cluster, "status", "--porcelain")
          and "the Mac pushes elsewhere" in open(
              os.path.join(cws, "notes.md")).read())
    git(cluster, "checkout", "--", "research/Proj/src/knn.py")

    # --- the command, status and where ------------------------------------------
    bin_dir = os.path.join(base, "bin")
    for name, body in (
            ("sbatch", 'echo 7777\n'),
            ("scontrol", 'echo "JobId=7777 StdOut=logs/x.out"\n'),
            ("squeue", 'echo "7777|PENDING"\n')):
        write(os.path.join(bin_dir, name), "#!/bin/sh\n" + body)
        os.chmod(os.path.join(bin_dir, name), 0o755)
    file_from_mac(dict(good, id="r7"))
    env = dict(os.environ, PATH=bin_dir + os.pathsep + os.environ["PATH"],
               TUTORBOARD_COURSES=cluster, BOARD_STATE_DIR=os.path.join(
                   base, "state"), TUTOR_SLURM="1")

    def tutor(*args, **kw):
        p = subprocess.run([sys.executable, TUTOR] + list(args), cwd=base,
                           env=dict(env, **kw), stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=300)
        return p.returncode, p.stdout.decode("utf-8", "replace")
    code, out = tutor("relay", "--once")
    check("`tutor relay --once` runs a pass", code == 0
          and "1 submitted" in out
          and load(os.path.join(cws, "relay", "reports", "r7.json"))["jobid"]
          == "7777")
    code, out = tutor("relay", "--status")
    check("`tutor relay --status` shows the last pass and the requests",
          code == 0 and "last pass" in out and "research/Proj" in out
          and "submitted" in out and "7777 (PENDING)" in out)
    code, out = tutor("relay", "--once", TUTOR_SLURM="0")
    check("and refuses on a machine without Slurm",
          code == 1 and "no Slurm" in out)
    check("`tutor where` prints the relay's last pass",
          relay.where_line(cluster).startswith("relay: last pass")
          and "relay.where_line()" in open(TUTOR, encoding="utf-8").read())

    # --- the scrontab entry ---------------------------------------------------------
    block = relay.scrontab_block("/usr/bin/python3", "/x/board/bin/tutor",
                                 "/x/relay.log")
    check("the entry runs one pass every five minutes on c3_short",
          "*/5 * * * * /usr/bin/python3 /x/board/bin/tutor relay --once --quiet"
          in block and "#SCRON --partition=c3_short" in block
          and "#SCRON --output=/x/relay.log" in block)
    old = "# mine\n0 * * * * true\n" + relay.scrontab_block("a", "b", "c")
    new = relay.merged_crontab(old, block)
    check("installing replaces the old block and keeps the owner's lines",
          new.count(relay.SCRON_BEGIN) == 1 and "0 * * * * true" in new
          and "/x/relay.log" in new)

    class Scron:
        def __init__(self):
            self.written = None

        def __call__(self, argv, **kw):
            if argv[1:] == ["-l"]:
                return Done(0, "# mine\n")
            self.written = open(argv[1]).read()
            return Done(0, "")
    os.environ["BOARD_STATE_DIR"] = os.path.join(base, "state")
    scron = Scron()
    ok, _ = relay.install(run=scron)
    check("`tutor relay --install` writes it through scrontab",
          ok and scron.written and "relay --once" in scron.written
          and scron.written.startswith("# mine"))
finally:
    os.environ.clear()
    os.environ.update(saved_env)
    shutil.rmtree(base, ignore_errors=True)

# --- the real repository ------------------------------------------------------------
check("the root .gitignore keeps the relay's state out of git",
      subprocess.run(["git", "check-ignore", "-q",
                      "research/TRD-EHR/relay/state/x.exit"],
                     cwd=REPO).returncode == 0
      and subprocess.run(["git", "check-ignore", "-q", "relay/state.json"],
                         cwd=REPO).returncode == 0)
check("TRD-EHR tracks what the relay exports",
      subprocess.run(["git", "check-ignore", "-q",
                      "research/TRD-EHR/exports/results/a/figures/x.png"],
                     cwd=REPO).returncode == 1)

print()
if fails:
    print("%d check(s) failed" % len(fails))
    sys.exit(1)
print("a request is pulled, run, ended from squeue and reported through git")
