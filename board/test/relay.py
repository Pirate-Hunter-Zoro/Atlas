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
    exception type, a turn's note screened.

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

SPINE = {
    "version": 1,
    "deliverables": [{"id": "paper1", "title": "Paper 1", "doc": ""}],
    "threads": [
        {"id": "knn", "deliverable": "paper1", "title": "Neighbours",
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
    write(os.path.join(seed, "atlas.json"),
          json.dumps({"families": [{"id": "research"}]}))
    write(os.path.join(seed, ".gitignore"),
          "**/relay/state/\n/relay/state.json\n/relay/.lock\nai-config/\n")
    proj = os.path.join(seed, "research", "Proj")
    write(os.path.join(proj, "tutorboard.json"),
          json.dumps({"name": "Proj", "relay": {"turns": True}}))
    write(os.path.join(proj, "AI_INSTRUCTIONS.md"), "# contract\n")
    write(os.path.join(proj, ".gitignore"),
          "live/\nresults/\nlogs/\n!exports/**\n")
    write(os.path.join(proj, "threads.json"), json.dumps(SPINE))
    write(os.path.join(proj, "slurm", "sweep.sbatch"), RECIPE)
    write(os.path.join(proj, "slurm", "crash.sbatch"), CRASH)
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
    run_pass(now=time.time() + jobs.GRACE + 30)
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

    # --- turns: one at a time, under the guard, the note screened -----------
    for rid in ("t1", "t2"):
        file_from_mac({"id": rid, "kind": "turn", "thread": "knn",
                       "brief": "Why did L1 keep every dimension?"})
    got = run_pass()
    t1 = load(os.path.join(cws, "relay", "reports", "t1.json"))
    check("the first turn request is submitted as a job of its own",
          got["turn"] == "t1" and t1["state"] == "submitted")
    script = slurm.scripts[t1["jobid"]][0]
    body = open(script).read()
    check("which runs `tutor relay --turn` on c3_short and writes its exit code",
          "relay --turn" in body and "--partition=c3_short" in body
          and ".exit" in body)
    check("and the second waits: one turn at a time",
          not os.path.exists(os.path.join(cws, "relay", "reports", "t2.json")))
    run_pass()
    check("still waiting while the first is out",
          not os.path.exists(os.path.join(cws, "relay", "reports", "t2.json")))
    write(relay.note_path(cws, "t1"),
          "L1 kept 384 of 384 dimensions across 5 folds; the penalty never "
          "bound. Logs are in /media/lab/storage/run.\n")
    write(os.path.join(cws, "relay", "state", "t1.exit"), "0\n")
    slurm.queue.pop(t1["jobid"])
    got = run_pass()
    t1 = load(os.path.join(cws, "relay", "reports", "t1.json"))
    check("a finished turn's report carries its note, paths redacted",
          t1["state"] == "completed" and "384 of 384" in t1["note"]
          and "/media" not in t1["note"] and "<path>" in t1["note"])
    check("and the next turn starts", got["turn"] == "t2")
    t2 = load(os.path.join(cws, "relay", "reports", "t2.json"))
    write(relay.note_path(cws, "t2"), "SESSION-4 said so.\n")
    write(os.path.join(cws, "relay", "state", "t2.exit"), "0\n")
    slurm.queue.pop(t2["jobid"])
    run_pass()
    t2 = load(os.path.join(cws, "relay", "reports", "t2.json"))
    check("a note the PHI policy matches is withheld, not published",
          "withheld" in t2["note"] and "SESSION-4" not in json.dumps(t2))

    class Claude:
        def __call__(self, argv, **kw):
            self.argv, self.kw = argv, kw
            return Done(0, json.dumps({"result": "AUC 0.71 at k=12."}))
    claude = Claude()
    os.environ["ANTHROPIC_BASE_URL"] = "https://api.deepseek.example"
    code = relay.run_turn(cws, "t2", run=claude)
    check("inside its job a turn runs Claude headless in the workspace, "
          "routing scrubbed", code == 0 and claude.argv[:2] == ["claude", "-p"]
          and claude.kw["cwd"] == cws
          and "ANTHROPIC_BASE_URL" not in claude.kw["env"])
    check("told its note is public", "PUBLISHED" in claude.argv[2]
          and "Why did L1" in claude.argv[2])
    check("and its last message becomes the note",
          open(relay.note_path(cws, "t2")).read().strip() == "AUC 0.71 at k=12.")
    del os.environ["ANTHROPIC_BASE_URL"]

    leaving._POLICY["root"] = None
    os.rename(os.path.join(cluster, "ai-config"),
              os.path.join(base, "ai-config-away"))
    file_from_mac({"id": "t3", "kind": "turn", "thread": "knn", "brief": "x"})
    run_pass()
    t3 = load(os.path.join(cws, "relay", "reports", "t3.json"))
    check("without the PHI policy in the checkout, no turn runs",
          t3["state"] == "refused" and "PHI guard" in t3["problems"][0])
    os.rename(os.path.join(base, "ai-config-away"),
              os.path.join(cluster, "ai-config"))
    leaving._POLICY["root"] = None

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
