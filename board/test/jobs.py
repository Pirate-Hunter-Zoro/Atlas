#!/usr/bin/env python3
"""Long work is registered to a thread, and reports itself when it ends.

What the checks are about:

  * `board job` SUBMITS AND REGISTERS. The sbatch runs, the id is read, and one
    record lands in the registry, in the place git can see.
  * THE POLL REPORTS EACH ENDING ONCE. sacct is asked about the jobs still out;
    an ending is appended and becomes one `[job]` line in the inbox, which
    wakes a turn the way `[direction]` does.
  * RUNNING IS VISIBLE. The thread says `running` while a job is out, and the
    payload carries the job for the busy strip.
  * EVERY CONTRACT SAYS IT. A bare sbatch is work the board cannot see.
"""

import importlib.machinery
import importlib.util
import json
import os
import stat
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
sys.path.insert(0, ROOT)
from tutorboard import jobs, missions                                  # noqa: E402
from tutorboard.course import threads                                  # noqa: E402

BOARD = os.path.join(ROOT, "bin", "board")
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
    subprocess.run(["git"] + list(args), cwd=cwd, stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL, check=False)


class Done:
    def __init__(self, code=0, out="", err=""):
        self.returncode, self.stdout, self.stderr = code, out, err


class Slurm:
    """sbatch, scontrol and sacct, answering from a table."""

    def __init__(self):
        self.calls = []
        self.states = {}           # jobid -> list of (JobID, State, Exit, End)
        self.sacct_ok = True
        self.next_id = 1000

    def __call__(self, argv, **kw):
        self.calls.append(list(argv))
        name = os.path.basename(argv[0])
        if name == "sbatch":
            self.next_id += 1
            return Done(0, "%d;cluster\n" % self.next_id)
        if name == "scontrol":
            return Done(0, "JobId=%s JobName=sweep UserId=me(1) "
                           "StdOut=logs/sweep-%%j.out WorkDir=/x\n" % argv[-1])
        if name == "sacct":
            if not self.sacct_ok:
                return Done(1, "", "slurm_load_jobs error")
            ids = argv[argv.index("-j") + 1].split(",")
            rows = []
            for i in ids:
                rows += ["|".join(r) for r in self.states.get(i, [])]
            return Done(0, "\n".join(rows) + "\n")
        raise AssertionError("unexpected command %r" % argv)


def workspace(base, name, ignore):
    ws = os.path.join(base, name)
    os.makedirs(ws)
    git(ws, "init", "-q")
    git(ws, "config", "user.email", "t@example.com")
    git(ws, "config", "user.name", "t")
    write(os.path.join(ws, ".gitignore"), ignore)
    write(os.path.join(ws, "AI_INSTRUCTIONS.md"), "# contract\n")
    os.makedirs(os.path.join(ws, "live"), exist_ok=True)
    clean, problems = threads.validate(SPINE)
    assert not problems, problems
    write(threads.path(ws), json.dumps(SPINE))
    return ws


SPINE = {
    "version": 1,
    "deliverables": [{"id": "paper1", "title": "Paper 1", "doc": ""}],
    "threads": [
        {"id": "knn", "deliverable": "paper1", "title": "Weighted neighbours",
         "question": "Does weighting beat cosine?",
         "outputs": ["results/knn.csv"], "tasks": [{"text": "Run the sweep",
                                                     "done": False}]},
        {"id": "tripod", "deliverable": "paper1", "title": "TRIPOD"},
    ],
}

base = tempfile.mkdtemp(prefix="tutor-jobs-")

# --- where the registry lives -----------------------------------------------
wholesale = workspace(base, "wholesale", "live/\n")
allowed = workspace(base, "allowed", "live/*\n!live/jobs.jsonl\n")
check("where live/ is ignored wholesale the registry is jobs.jsonl at the root",
      jobs.registry(wholesale, create=True) == os.path.join(wholesale, "jobs.jsonl"))
check("where live/ allowlists it, the registry is live/jobs.jsonl",
      jobs.registry(allowed, create=True)
      == os.path.join(allowed, "live", "jobs.jsonl"))
check("a reader with no registry is handed a path that holds nothing, and git "
      "is not asked", threads.jobs_of(wholesale) == [])

# --- submitting ---------------------------------------------------------------
slurm = Slurm()
rec, why = jobs.submit(wholesale, "knn", ["sbatch", "sweep.sbatch"],
                       produces=["results/knn.csv"], cwd=wholesale, run=slurm,
                       now=time.time())
check("submit runs sbatch with --parsable added",
      slurm.calls[0] == ["sbatch", "--parsable", "sweep.sbatch"])
check("and registers {thread, jobid, cmd, produces, submitted}",
      rec and rec["jobid"] == "1001" and rec["thread"] == "knn"
      and rec["cmd"] == "sbatch sweep.sbatch"
      and rec["produces"] == ["results/knn.csv"] and rec["submitted"] > 0)
check("with the log scontrol names, %j filled in, workspace-relative",
      rec["log"] == os.path.join("logs", "sweep-1001.out"))
check("in the root registry, which git can see",
      os.path.isfile(os.path.join(wholesale, "jobs.jsonl"))
      and not jobs.ignored(wholesale, "jobs.jsonl"))
rec2, why2 = jobs.submit(wholesale, "knn", ["srun", "x"], run=slurm)
check("anything but sbatch is refused, and nothing is registered",
      rec2 is None and "sbatch" in why2 and len(jobs.records(wholesale)) == 1)

threads._cache.clear()
check("a registered job makes its thread running",
      threads.stages(wholesale)["knn"]["status"] == "running")
check("and the payload carries it for the busy strip, titled",
      jobs.running(wholesale)[0]["title"] == "Weighted neighbours"
      and jobs.running(wholesale)[0]["state"] == "PENDING")

# --- polling --------------------------------------------------------------------
slurm.states["1001"] = [("1001", "RUNNING", "0:0", "Unknown")]
check("a job still running ends nothing", jobs.poll(wholesale, run=slurm) == [])
check("but the change to RUNNING is appended, once",
      jobs.records(wholesale)["1001"]["state"] == "RUNNING")
n = len(threads.jobs_of(wholesale))
jobs.poll(wholesale, run=slurm)
check("and an unchanged state appends nothing", len(threads.jobs_of(wholesale)) == n)

slurm.sacct_ok = False
check("sacct that cannot be asked reports nothing and ends nothing",
      jobs.poll(wholesale, run=slurm) == []
      and jobs.records(wholesale)["1001"]["state"] == "RUNNING")
slurm.sacct_ok = True

slurm.states["1001"] = [("1001", "COMPLETED", "0:0", "2026-10-01T10:00:00")]
ended = jobs.report(wholesale, run=slurm)
check("a terminal state is reported", len(ended) == 1
      and ended[0]["state"] == "COMPLETED" and ended[0]["exit"] == "0:0")
check("and a second pass does not report it again",
      jobs.report(wholesale, run=slurm) == [])
threads._cache.clear()
check("its thread is no longer running",
      threads.stages(wholesale)["knn"]["status"] == "open"
      and jobs.running(wholesale) == [])

inbox = os.path.join(wholesale, "live", "inbox", "messages.jsonl")
with open(inbox, encoding="utf-8") as fh:
    lines = [json.loads(x) for x in fh if x.strip()]
check("exactly one [job] line is in the inbox, unread, signalled `job`",
      len(lines) == 1 and lines[0]["signal"] == "job"
      and not lines[0]["read"] and lines[0]["text"].startswith("[job] "))
said = lines[0]["text"]
check("it names the thread, the job, the exit and what it was to produce",
      "knn (Weighted neighbours)" in said and "1001" in said
      and "MISSING results/knn.csv" in said and "board thread" in said)
check("and a clean ending asks for no log", "did NOT end cleanly" not in said)

# A failure, an array, and a job Slurm never heard of.
rec, _ = jobs.submit(wholesale, "tripod", ["sbatch", "a.sbatch"], run=slurm,
                     cwd=wholesale)
slurm.states[rec["jobid"]] = [(rec["jobid"], "FAILED", "1:0", "2026-10-01T11:00:00")]
ended = jobs.poll(wholesale, run=slurm)
text = jobs.sense(wholesale, ended[0])
check("a failed job is reported with its log named and the tail asked for",
      ended[0]["state"] == "FAILED" and "did NOT end cleanly" in text
      and "logs/sweep-%s.out" % rec["jobid"] in text and "last 40 lines" in text)
check("and the log is named, never copied into the inbox",
      "Traceback" not in text)

rec, _ = jobs.submit(wholesale, "tripod", ["sbatch", "--array=1-2", "a.sbatch"],
                     run=slurm, cwd=wholesale)
jid = rec["jobid"]
slurm.states[jid] = [(jid + "_1", "COMPLETED", "0:0", "2026-10-01T11:00:00"),
                     (jid + "_2", "RUNNING", "0:0", "Unknown")]
check("an array with one task still running has not ended",
      jobs.poll(wholesale, run=slurm) == [])
slurm.states[jid] = [(jid + "_1", "COMPLETED", "0:0", "2026-10-01T11:00:00"),
                     (jid + "_2", "TIMEOUT", "0:0", "2026-10-01T12:00:00")]
ended = jobs.poll(wholesale, run=slurm)
check("and once every task has, it ended the worst way any of them did",
      len(ended) == 1 and ended[0]["state"] == "TIMEOUT"
      and ended[0]["ended"] == "2026-10-01T12:00:00")

rec, _ = jobs.submit(wholesale, "tripod", ["sbatch", "b.sbatch"], run=slurm,
                     cwd=wholesale, now=time.time() - 3600)
check("a job sacct has never heard of, an hour on, is LOST and reported",
      [e["state"] for e in jobs.poll(wholesale, run=slurm)] == ["LOST"])
rec, _ = jobs.submit(wholesale, "tripod", ["sbatch", "c.sbatch"], run=slurm,
                     cwd=wholesale)
check("but a minute on it is still out",
      jobs.poll(wholesale, run=slurm) == []
      and any(j["jobid"] == rec["jobid"] for j in jobs.running(wholesale)))

# --- an ending is never lost, and a record publishes nothing private -----------
spare = workspace(base, "spare", "live/\n")
s2 = Slurm()
xrec, _ = jobs.submit(spare, "knn", ["sbatch", "--export=ALL,DATA=/phi/x", "--export",
                                    "OUT=/phi/y", "e.sbatch"], cwd=spare, run=s2)
check("an --export value is kept out of the registry, its name kept",
      "/phi" not in xrec["cmd"] and "DATA=..." in xrec["cmd"]
      and "OUT=..." in xrec["cmd"])
check("a log outside the workspace is stored by its name alone",
      jobs._relative(spare, "/elsewhere/logs/a.out") == "a.out")


class Split(Slurm):
    def __call__(self, argv, **kw):
        if os.path.basename(argv[0]) == "scontrol":
            self.calls.append(list(argv))
            return Done(0, "JobId=%s StdOut=logs/run_%%A_%%a.out "
                           "StdErr=logs/run_%%A_%%a_err.txt\n" % argv[-1])
        return Slurm.__call__(self, argv, **kw)


s3 = Split()
arec, _ = jobs.submit(spare, "knn", ["sbatch", "--array=1-3", "r.sbatch"],
                     cwd=spare, run=s3)
jid = arec["jobid"]
check("a separate stderr file is registered beside the log, %a as a glob",
      arec["err"] == "logs/run_%s_*_err.txt" % jid
      and arec["log"] == "logs/run_%s_*.out" % jid)
s3.states[jid] = [(jid + "_1", "PENDING", "0:0", "Unknown"),
                  (jid + "_2", "CANCELLED+", "0:0", "x")]
check("a pending task beside a CANCELLED+ one has not ended",
      jobs.poll(spare, run=s3) == [])
s3.states[jid] = [(jid + "_1", "FAILED", "1:0", "y"),
                  (jid + "_2", "CANCELLED+", "0:0", "x")]
_drop = jobs.drop
jobs.drop = lambda *a, **k: (_ for _ in ()).throw(OSError("inbox full"))
check("an ending whose inbox line cannot be written is not reported",
      jobs.report(spare, run=s3) == [])
jobs.drop = _drop
threads._cache.clear()
check("but the job reads ended, not running",
      all(j["jobid"] != jid for j in jobs.running(spare)))
again = jobs.report(spare, run=s3)
check("and the next pass reports it, pointing at the errors file",
      [e["jobid"] for e in again] == [jid]
      and "errors file" in jobs.sense(spare, again[0])
      and "glob it" in jobs.sense(spare, again[0]))
check("once", jobs.report(spare, run=s3) == [])

# --- the daemon's pass ------------------------------------------------------------
_loader = importlib.machinery.SourceFileLoader("tutorcli_jobs", TUTOR)
_spec = importlib.util.spec_from_loader("tutorcli_jobs", _loader)
tutorcli = importlib.util.module_from_spec(_spec)
_loader.exec_module(tutorcli)

slurm.states[rec["jobid"]] = [(rec["jobid"], "CANCELLED by 1", "0:15", "x")]


class Log:
    def __init__(self):
        self.said = []

    def write(self, s):
        self.said.append(s)


log = Log()
got = tutorcli.job_pass(wholesale, log, run=slurm)
check("the daemon's pass reports the ending and says so in its log",
      [g["state"] for g in got] == ["CANCELLED"]
      and any("[job] line is in the inbox" in s for s in log.said))


def broken(*a, **k):
    raise RuntimeError("the filer went away")


jobs.submit(wholesale, "tripod", ["sbatch", "d.sbatch"], run=slurm,
            cwd=wholesale)
log = Log()
check("and a pass that throws is logged, not raised",
      tutorcli.job_pass(wholesale, log, run=broken) == []
      and any("job poll failed" in s for s in log.said))
check("the inbox line wakes a turn signalled `job`, the way [direction] does",
      tutorcli.turn_signal("[2026-10-01 10:00:00] " + said) == "job")
check("the daemon runs the pass on a beat of its own",
      "beat_jobs" in open(TUTOR, encoding="utf-8").read())

# --- the command ------------------------------------------------------------------
bin_dir = os.path.join(base, "bin")
os.makedirs(bin_dir)
for name, body in (("sbatch", 'echo "$@" > "%s/sbatch.args"; echo 4242\n' % base),
                   ("scontrol", 'echo "JobId=4242 StdOut=%s/out-%%j.log"\n'
                                % base)):
    p = os.path.join(bin_dir, name)
    write(p, "#!/bin/sh\n" + body)
    os.chmod(p, os.stat(p).st_mode | stat.S_IEXEC)
env = dict(os.environ, PATH=bin_dir + os.pathsep + os.environ.get("PATH", ""))


def board(cwd, *args):
    p = subprocess.run([sys.executable, BOARD] + list(args), cwd=cwd, env=env,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       timeout=120)
    return p.returncode, p.stdout.decode("utf-8", "replace")


code, out = board(allowed, "job", "knn", "--produces", "results/knn.csv", "--",
                  "sbatch", "--wrap", "true")
check("`board job` submits and registers", code == 0 and "4242" in out
      and jobs.records(allowed)["4242"]["produces"] == ["results/knn.csv"])
check("in live/jobs.jsonl, which that workspace's git can see",
      os.path.isfile(os.path.join(allowed, "live", "jobs.jsonl"))
      and not jobs.ignored(allowed, "live/jobs.jsonl"))
check("with the sbatch's own arguments passed through, --parsable first",
      open(os.path.join(base, "sbatch.args")).read().split()
      == ["--parsable", "--wrap", "true"])
code, out = board(allowed, "job", "ghost", "--", "sbatch", "x")
check("a thread the file does not declare is refused",
      code == 1 and "knn" in out and "4243" not in out)
code, out = board(allowed, "job", "knn", "--produces", "../x", "--", "sbatch", "x")
check("a --produces path outside the workspace is refused, nothing submitted",
      code == 1 and len(jobs.records(allowed)) == 1)
code, out = board(allowed, "job", "knn", "sbatch", "x")
check("and so is a command with no `--` before it", code == 1 and "--" in out)
code, out = board(allowed, "job", "--show")
check("`--show` lists what is registered", code == 0 and "4242" in out)
code, out = board(allowed, "thread", "--show", "knn")
check("and `board thread --show` says the thread is running",
      code == 0 and json.loads(out)["stage"]["status"] == "running")

# --- missions carry a thread too ---------------------------------------------------
rec = missions.dispatch(allowed, "do the thing", "t0007", thread="tripod")
check("a mission records the thread it was dispatched for",
      rec["thread"] == "tripod"
      and missions.stored(allowed)[0]["thread"] == "tripod")
_live = missions.live_mission
missions.live_mission = lambda root, now=None: rec
threads._cache.clear()
check("and while it is live its thread says running",
      threads.stages(allowed)["tripod"]["status"] == "running")
missions.live_mission = lambda root, now=None: None
threads._cache.clear()
check("and not once it has ended",
      threads.stages(allowed)["tripod"]["status"] == "open")
missions.live_mission = _live

# --- the real repository -----------------------------------------------------------
for ws in ("courses/Galois-Theory", "courses/Probability", "practice/Algo-Solutions",
           "practice/Lean-Theorem-Proving", "research/PSYCH-ASR",
           "projects/libr-local-llm", "research/TRD-EHR", "projects/Paper-Writer"):
    root = os.path.join(REPO, ws)
    if not os.path.isdir(root):
        continue
    where = jobs.registry(root, create=True)
    check("%s: the registry it would write (%s) is visible to git"
          % (ws, os.path.relpath(where, root)),
          not jobs.ignored(root, os.path.relpath(where, root)))
    with open(os.path.join(root, "AI_INSTRUCTIONS.md"), encoding="utf-8") as fh:
        contract = fh.read()
    check("%s: its contract says long work goes through `board job`" % ws,
          "**Long work goes through `board job`.**" in contract
          and "A bare `sbatch` is work the board cannot see." in contract)

print()
if fails:
    print("%d check(s) failed" % len(fails))
    sys.exit(1)
print("a job is registered to its thread, and reports itself once when it ends")
