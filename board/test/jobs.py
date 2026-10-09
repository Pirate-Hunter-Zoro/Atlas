#!/usr/bin/env python3
"""Long work is labelled, and reports itself when it ends.

What the checks are about:

  * `board job` SUBMITS AND REGISTERS. The sbatch runs, the id is read, and one
    record lands in the registry, the subject's ignored `relay/state/jobs.jsonl`.
  * RUNTIME STATE LEAVES live/. `migrate_state` moves the registry, the claims
    and the Colibri queue into `relay/state/` once, and a second run changes
    nothing. A claim from before the move still holds, so hearing TRD-EHR's
    whole report history over its old claims wakes nothing.
  * THE POLL REPORTS EACH ENDING ONCE. squeue and the wrapper's exit file say;
    an ending is appended and becomes one `[job]` line in the inbox, which
    wakes a turn the way `[direction]` does.
  * RUNNING IS VISIBLE. The thread says `running` while a job is out, and the
    payload carries the job for the busy strip.
  * EVERY CONTRACT SAYS IT. A bare sbatch is work the board cannot see.
  * A REQUEST IS PINNED. It carries `commit`, HEAD when filed; a dirty
    subject files nothing, and HEAD lacking the commit refuses it.
  * A BATCH IS ONE COMMIT. `board job --batch <file.json>` files many
    requests in one commit and one push, and one bad entry files none.
"""
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
sys.path.insert(0, ROOT)
from tutorboard import cluster, exports, jobs                          # noqa: E402

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


def git_ok(cwd, *args):
    return subprocess.run(["git"] + list(args), cwd=cwd,
                          stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL).returncode == 0


class Done:
    def __init__(self, code=0, out="", err=""):
        self.returncode, self.stdout, self.stderr = code, out, err


class Slurm:
    """sbatch, scontrol and squeue, answering from a table."""

    def __init__(self):
        self.calls = []
        self.queue = {}            # squeue's %i -> %T, for jobs still held
        self.squeue_ok = True
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
        if name == "squeue":
            if not self.squeue_ok:
                return Done(1, "", "slurm_load_jobs error")
            return Done(0, "".join("%s|%s\n" % kv
                                   for kv in sorted(self.queue.items())))
        if name == "sacct":
            raise AssertionError("sacct is refused on this cluster")
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
    return ws

base = tempfile.mkdtemp(prefix="tutor-jobs-")

# --- where the registry lives -----------------------------------------------
wholesale = workspace(base, "wholesale", "live/\nrelay/state/\n")
allowed = workspace(base, "allowed", "live/*\n!live/jobs.jsonl\nrelay/state/\n")
check("the registry is relay/state/jobs.jsonl, whatever live/ says",
      jobs.registry(wholesale) == os.path.join(wholesale, "relay", "state",
                                               "jobs.jsonl")
      and jobs.registry(allowed) == os.path.join(allowed, "relay", "state",
                                                 "jobs.jsonl"))
check("a reader with no registry is handed a path that holds nothing, and git "
      "is not asked", exports.jobs_of(wholesale) == [])

# --- submitting ---------------------------------------------------------------
slurm = Slurm()
rec, why = jobs.submit(wholesale, "knn", ["sbatch", "sweep.sbatch"],
                       produces=["results/knn.csv"], cwd=wholesale, run=slurm,
                       now=time.time())
check("submit runs sbatch with --parsable added",
      slurm.calls[0] == ["sbatch", "--parsable", "sweep.sbatch"])
check("and registers {label, jobid, cmd, produces, submitted}",
      rec and rec["jobid"] == "1001" and rec["label"] == "knn"
      and "thread" not in rec
      and rec["cmd"] == "sbatch sweep.sbatch"
      and rec["produces"] == ["results/knn.csv"] and rec["submitted"] > 0)
check("with the log scontrol names, %j filled in, workspace-relative",
      rec["log"] == os.path.join("logs", "sweep-1001.out"))
check("in relay/state/jobs.jsonl, which git ignores",
      os.path.isfile(os.path.join(wholesale, "relay", "state", "jobs.jsonl"))
      and jobs.ignored(wholesale, "relay/state/jobs.jsonl"))
rec2, why2 = jobs.submit(wholesale, "knn", ["srun", "x"], run=slurm)
check("anything but sbatch is refused, and nothing is registered",
      rec2 is None and "sbatch" in why2 and len(jobs.records(wholesale)) == 1)

check("the payload carries it for the busy strip, titled by its label",
      jobs.running(wholesale)[0]["title"] == "knn"
      and jobs.running(wholesale)[0]["state"] == "PENDING")

# --- polling: squeue, and the wrapper's exit file ------------------------------
t0 = rec["submitted"]
slurm.queue["1001"] = "RUNNING"
check("a job still running ends nothing",
      jobs.poll(wholesale, run=slurm, now=t0 + 5) == [])
check("but the change to RUNNING is appended, once",
      jobs.records(wholesale)["1001"]["state"] == "RUNNING")
n = len(exports.jobs_of(wholesale))
jobs.poll(wholesale, run=slurm, now=t0 + 6)
check("and an unchanged state appends nothing", len(exports.jobs_of(wholesale)) == n)
check("squeue is asked, and sacct never",
      any(os.path.basename(c[0]) == "squeue" for c in slurm.calls)
      and not any(os.path.basename(c[0]) == "sacct" for c in slurm.calls))

slurm.squeue_ok = False
del slurm.queue["1001"]
check("squeue that cannot be asked reports nothing and ends nothing",
      jobs.poll(wholesale, run=slurm, now=t0 + 600) == []
      and jobs.records(wholesale)["1001"]["state"] == "RUNNING")
slurm.squeue_ok = True
check("a raw job gone from squeue within the grace is waited on",
      jobs.poll(wholesale, run=slurm, now=t0 + jobs.GRACE / 2) == [])

ended = jobs.report(wholesale, run=slurm, now=t0 + 600)
check("a raw sbatch gone from squeue is ENDED, exit unknown",
      len(ended) == 1 and ended[0]["state"] == "ENDED"
      and ended[0]["exit"] == "")
check("and a second pass does not report it again",
      jobs.report(wholesale, run=slurm, now=t0 + 700) == [])
check("and it is no longer running", jobs.running(wholesale) == [])

# No session filed it, so the line is a home notice (D16) and wakes no turn.
lines = cluster.notices(wholesale)
check("exactly one [job] line, signalled `job`, a notice since no session "
      "filed the job",
      len(lines) == 1 and lines[0]["signal"] == "job"
      and lines[0]["text"].startswith("[job] ")
      and not os.path.exists(os.path.join(wholesale, "live", "inbox")))
said = lines[0]["text"]
check("it names the label, the job, the exit and what it was to produce, "
      "and reads no thread file",
      "A job, knn, has ended" in said and "1001" in said
      and "MISSING results/knn.csv" in said and "board thread" not in said)
check("and says how a raw job ended is unknown, without calling it a failure",
      "unknown" in said and "did NOT end cleanly" not in said)

# --- a wrapped recipe writes its exit code as its last act ---------------------
write(os.path.join(wholesale, "slurm", "a.sbatch"),
      "#!/bin/bash\n#SBATCH --time=00:05:00\n#SBATCH -o logs/a-%j.out\n"
      "#RELAY-VAR N [0-9]\n\nset -e\necho RELAY: n=$N\nexit $N\n")
rec, why = jobs.submit_recipe(wholesale, "tripod", "slurm/a.sbatch",
                              env={"N": "3"}, run=slurm, now=time.time())
script = os.path.join(wholesale, "relay", "state", rec["key"] + ".sbatch")
with open(script, encoding="utf-8") as fh:
    body = fh.read()
sent = [c for c in slurm.calls if os.path.basename(c[0]) == "sbatch"][-1]
check("a recipe is submitted as a wrapper under relay/state/, its header kept",
      os.path.isfile(script) and "#SBATCH --time=00:05:00" in body
      and "#SBATCH -o logs/a-%j.out" in body and "--job-name=a" in body
      and sent[-1] == script and "--export=ALL,N=3" in sent)
check("registered under the recipe's name, with its exit file named",
      rec["cmd"] == "slurm/a.sbatch N=3"
      and rec["exitfile"] == "relay/state/%s.exit" % rec["key"])
check("and a raw sbatch gets no wrapper", "exitfile" not in
      jobs.records(wholesale)["1001"])
ran = subprocess.run(["bash", script], cwd=wholesale, env=dict(os.environ, N="3"),
                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
check("the wrapper runs the recipe and exits with its code",
      ran.returncode == 3 and b"RELAY: n=3" in ran.stdout)
slurm.queue[rec["jobid"]] = "RUNNING"
check("the exit file alone does not end a job squeue still holds",
      jobs.poll(wholesale, run=slurm) == [])
del slurm.queue[rec["jobid"]]
ended = jobs.poll(wholesale, run=slurm)
text = jobs.sense(wholesale, ended[0])
check("gone from squeue with exit 3 written: FAILED, 3:0, no grace needed",
      ended[0]["state"] == "FAILED" and ended[0]["exit"] == "3:0")
check("a failed job is reported with its log named and the tail asked for",
      "did NOT end cleanly" in text and "last 40 lines" in text)
check("and the log is named, never copied into the inbox",
      "RELAY: n=3" not in text)

rec, _ = jobs.submit_recipe(wholesale, "tripod", "slurm/a.sbatch",
                            env={"N": "0"}, run=slurm, now=time.time() - 3600)
check("a wrapped job gone from squeue without its exit file is not called "
      "on the first look: another node's NFS view may lag the exit file",
      jobs.poll(wholesale, run=slurm) == []
      and jobs.records(wholesale)[rec["jobid"]].get("gone_at"))
check("a wrapped job still gone a minute later, without its exit file, DIED",
      [(e["state"], e["exit"]) for e in jobs.poll(
          wholesale, run=slurm, now=time.time() + jobs.GONE_GRACE + 1)]
      == [("DIED", "")])
check("and its [job] line says a time limit, a node failure or a cancel",
      "time limit" in jobs.sense(wholesale, dict(rec, state="DIED")))
rec, _ = jobs.submit_recipe(wholesale, "tripod", "slurm/a.sbatch",
                            env={"N": "0"}, run=slurm)
check("but a minute on it is still out",
      jobs.poll(wholesale, run=slurm) == []
      and any(j["jobid"] == rec["jobid"] for j in jobs.running(wholesale)))
write(os.path.join(wholesale, rec["exitfile"]), "0\n")
check("and once its file says 0 it COMPLETED",
      [(e["state"], e["exit"]) for e in jobs.poll(wholesale, run=slurm)]
      == [("COMPLETED", "0:0")])

# An array writes one exit file per task, and ends the worst way any did.
rec, _ = jobs.submit_recipe(wholesale, "tripod", "slurm/a.sbatch",
                            env={"N": "0"}, run=slurm)
stem = os.path.join(wholesale, rec["exitfile"])[:-len(".exit")]
write(stem + "_1.exit", "0\n")
slurm.queue[rec["jobid"] + "_2"] = "RUNNING"
check("an array with one task still in squeue has not ended",
      jobs.poll(wholesale, run=slurm) == [])
del slurm.queue[rec["jobid"] + "_2"]
write(stem + "_2.exit", "137\n")
ended = jobs.poll(wholesale, run=slurm)
check("and once every task has left, it ended the worst way any of them did",
      len(ended) == 1 and ended[0]["state"] == "FAILED"
      and ended[0]["exit"] == "137:0")
env_task = dict(os.environ, N="0", SLURM_ARRAY_TASK_ID="4")
subprocess.run(["bash", os.path.join(wholesale, "relay", "state",
                                     rec["key"] + ".sbatch")],
               cwd=wholesale, env=env_task, stdout=subprocess.DEVNULL)
check("a task's wrapper writes <key>_<task>.exit",
      open(stem + "_4.exit").read().strip() == "0")
check("relay/state/ is the relay's, and the root .gitignore keeps it out",
      "relay/state/" in open(os.path.join(REPO, ".gitignore")).read())

# --- an ending is never lost, and a record publishes nothing private -----------
spare = workspace(base, "spare", "live/\nrelay/state/\n")
s2 = Slurm()
xrec, _ = jobs.submit(spare, "knn", ["sbatch", "--export=ALL,DATA=/secret/x",
                                    "--export", "OUT=/secret/y", "e.sbatch"],
                      cwd=spare, run=s2)
check("an --export value is kept out of the registry, its name kept",
      "/secret" not in xrec["cmd"] and "DATA=..." in xrec["cmd"]
      and "OUT=..." in xrec["cmd"])
check("a log outside the workspace is stored by its name alone",
      jobs._relative(spare, "/elsewhere/logs/a.out") == "a.out")
check("and its real path only in the registry, which git ignores",
      xrec.get("log_path") is not None
      and jobs.ignored(spare, "relay/state/jobs.jsonl"))


class Split(Slurm):
    def __call__(self, argv, **kw):
        if os.path.basename(argv[0]) == "scontrol":
            self.calls.append(list(argv))
            return Done(0, "JobId=%s StdOut=logs/run_%%A_%%a.out "
                           "StdErr=logs/run_%%A_%%a_err.txt\n" % argv[-1])
        return Slurm.__call__(self, argv, **kw)


s3 = Split()
arec, _ = jobs.submit(spare, "knn", ["sbatch", "--array=1-3", "r.sbatch"],
                      cwd=spare, run=s3, now=time.time() - 3600)
jid = arec["jobid"]
check("a separate stderr file is registered beside the log, %a as a glob",
      arec["err"] == "logs/run_%s_*_err.txt" % jid
      and arec["log"] == "logs/run_%s_*.out" % jid)
s3.queue[jid + "_[2-3]"] = "PENDING"
check("a pending task holds the array open",
      jobs.poll(spare, run=s3) == [])
del s3.queue[jid + "_[2-3]"]
_drop = jobs.drop
jobs.drop = lambda *a, **k: (_ for _ in ()).throw(OSError("inbox full"))
check("an ending whose inbox line cannot be written is not reported",
      jobs.report(spare, run=s3) == [])
jobs.drop = _drop
check("but the job reads ended, not running",
      all(j["jobid"] != jid for j in jobs.running(spare)))
again = jobs.report(spare, run=s3)
check("and the next pass reports it, pointing at the log as a glob",
      [e["jobid"] for e in again] == [jid]
      and "glob it" in jobs.sense(spare, again[0]))
check("once", jobs.report(spare, run=s3) == [])

# --- the poll is the relay's now ---------------------------------------------------
from tutorboard.runner import turn as runturn  # noqa: E402
check("the inbox line wakes a turn signalled `job`, the way [direction] does",
      runturn.turn_signal("[2026-10-01 10:00:00] " + said) == "job")
source = "".join(open(p, encoding="utf-8").read() for p in (
    TUTOR, os.path.join(ROOT, "tutorboard", "runner", "loop.py")))
check("the board daemon no longer polls jobs; the relay's pass does",
      "beat_jobs" not in source and "def job_pass" not in source
      and "jobs.report(ws" in open(os.path.join(ROOT, "tutorboard", "relay.py"),
                                   encoding="utf-8").read())

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


code, out = board(allowed, "job", "--label", "knn", "--produces",
                  "results/knn.csv", "--", "sbatch", "--wrap", "true")
check("`board job` submits and registers", code == 0 and "4242" in out
      and jobs.records(allowed)["4242"]["produces"] == ["results/knn.csv"])
check("in relay/state/jobs.jsonl, which git ignores",
      os.path.isfile(os.path.join(allowed, "relay", "state", "jobs.jsonl"))
      and jobs.ignored(allowed, "relay/state/jobs.jsonl"))
check("with the sbatch's own arguments passed through, --parsable first",
      open(os.path.join(base, "sbatch.args")).read().split()
      == ["--parsable", "--wrap", "true"])
code, out = board(allowed, "job", "--label", "Not A Slug", "--", "sbatch", "x")
check("a label that is not a slug is refused, nothing submitted",
      code == 1 and "--label" in out and len(jobs.records(allowed)) == 1)
code, out = board(allowed, "job", "--label", "knn", "--produces", "../x", "--",
                  "sbatch", "x")
check("a --produces path outside the workspace is refused, nothing submitted",
      code == 1 and len(jobs.records(allowed)) == 1)
code, out = board(allowed, "job", "--label", "knn", "sbatch", "x")
check("and so is a command with no `--` before it", code == 1 and "--" in out)
code, out = board(allowed, "job", "--show")
check("`--show` lists what is registered", code == 0 and "4242" in out)

# --- the real repository -----------------------------------------------------------
for ws in ("courses/Galois-Theory", "courses/Probability", "projects/Algo-Solutions",
           "projects/Lean-Theorem-Proving", "projects/PSYCH-ASR",
           "projects/libr-local-llm", "projects/TRD-EHR", "projects/Paper-Writer"):
    root = os.path.join(REPO, ws)
    if not os.path.isdir(root):
        continue
    # Asked of git by path: `registry` would migrate a real live/.
    where = os.path.join(jobs.STATE, jobs.NAME)
    check("%s: the registry it would write (%s) is ignored by git"
          % (ws, where), jobs.ignored(root, where))
    with open(os.path.join(root, "AI_INSTRUCTIONS.md"), encoding="utf-8") as fh:
        contract = fh.read()
    check("%s: its contract says long work goes through `board job`" % ws,
          "**Long work goes through `board job`.**" in contract
          and "A bare `sbatch` is work the board cannot see." in contract)
    check("%s: its contract says ink on a document is answered in its ledger" % ws,
          "**Ink on a document is answered in its ledger.**" in contract
          and "`board round <document>`" in contract)
    check("%s: its contract says code is checked before it is pushed" % ws,
          "**Code is checked before it is pushed.**" in contract
          and "`check` in `tutorboard.json`" in contract)
    # A workspace with code names its check, and one with a pyproject.toml has the
    # lockfile `scripts/setup.sh` builds from (`uv sync --locked`).
    has_code = [m for m in ("pyproject.toml", "lean-toolchain", "go.mod")
                if os.path.isfile(os.path.join(root, m))]
    if has_code:
        try:
            with open(os.path.join(root, "tutorboard.json"), encoding="utf-8") as fh:
                named = json.load(fh).get("check")
        except (OSError, ValueError):
            named = None
        check("%s: it holds %s, and its tutorboard.json names its check"
              % (ws, has_code[0]), bool(named))
    if "pyproject.toml" in has_code:
        check("%s: its pyproject.toml has a uv.lock beside it" % ws,
              os.path.isfile(os.path.join(root, "uv.lock")))

# --- an array: a task that wrote no exit file died --------------------------
check("an array's task count is read off its header",
      jobs.array_tasks(["#SBATCH --array=0-9%2"]) == 10
      and jobs.array_tasks(["#SBATCH --array=1,3,5-7"]) == 5
      and jobs.array_tasks(["#SBATCH -a 0-15:4"]) == 4
      and jobs.array_tasks(["#SBATCH --time=1:00"]) is None
      and jobs.array_tasks(["#SBATCH --array=weird"]) == 0)
arr = tempfile.mkdtemp(prefix="tutor-array-")
try:
    write(os.path.join(arr, "relay", "state", "a_0.exit"), "0\n")
    write(os.path.join(arr, "relay", "state", "a_1.exit"), "0\n")
    one = {"exitfile": "relay/state/a.exit", "array_tasks": 3}
    check("an array with a task file missing has no exit: it DIED",
          jobs.exit_of(arr, one) is None
          and jobs.ending(arr, dict(one, submitted=1), time.time())[0]
          == "DIED")
    write(os.path.join(arr, "relay", "state", "a_2.exit"), "0\n")
    check("and with every task's file, the worst code is the job's",
          jobs.exit_of(arr, one)[0] == 0)
finally:
    shutil.rmtree(arr, ignore_errors=True)

# --- runtime state out of live/ ------------------------------------------------
def snapshot(root):
    """Every file under `root` (less .git) with its bytes."""
    out = {}
    for here, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d != ".git"]
        for f in files:
            full = os.path.join(here, f)
            with open(full, "rb") as fh:
                out[os.path.relpath(full, root)] = fh.read()
    return out


old = tempfile.mkdtemp(prefix="tutor-oldstate-")
try:
    git(old, "init", "-q", "-b", "main")
    write(os.path.join(old, ".gitignore"), "live/\nrelay/state/\n")
    git(old, "add", "-A")
    git(old, "-c", "user.email=t@example.com", "-c", "user.name=t", "commit",
        "-q", "-m", "seed")
    write(os.path.join(old, "live", "jobs.jsonl"),
          json.dumps({"jobid": "1001", "label": "knn", "submitted": 1.0})
          + "\n" + json.dumps({"jobid": "1001", "state": "COMPLETED",
                               "exit": "0:0", "reported": 2.0}) + "\n")
    write(os.path.join(old, "relay", "state", "jobs.jsonl"),
          json.dumps({"jobid": "2002", "request": "r1", "label": "sweep",
                      "submitted": 3.0}) + "\n")
    write(os.path.join(old, "live", "jobs.reported", "1001"), "")
    write(os.path.join(old, "live", "jobs.reported", "relay-r0.completed"), "")
    write(os.path.join(old, "live", "jobs.reported", jobs.HEARD), "abc123\n")
    write(os.path.join(old, "relay", "state", "jobs.reported", "1999"), "")
    write(os.path.join(old, "live", "coach.woken", "r9"), "")
    write(os.path.join(old, "live", "missions", "coli-a.json"),
          json.dumps({"id": "coli-a", "kind": "task", "queue": "queued",
                      "brief": "count", "at": 5.0}))
    write(os.path.join(old, "live", "missions", "coli-a.task.1"), "101 5.0\n")
    write(os.path.join(old, "live", "missions", "t0007.json"),
          json.dumps({"id": "t0007", "task": "a mission", "at": 6.0}))
    moved = jobs.migrate_state(old)
    st = os.path.join(old, "relay", "state")
    check("a fixture with old-location records migrates", moved == 8)
    check("the old registry joins the relay's, and each kind is polled by its "
          "own reader", sorted(jobs.records(old)) == ["1001", "2002"]
          and list(jobs.records(old, relay=False)) == ["1001"]
          and list(jobs.records(old, relay=True)) == ["2002"]
          and not os.path.exists(os.path.join(old, "live", "jobs.jsonl")))
    check("every claim lands in relay/state/reported/, the heard commit kept",
          sorted(os.listdir(os.path.join(st, "reported")))
          == sorted(["1001", "1999", "coach-r9", jobs.HEARD,
                     "relay-r0.completed"])
          and open(os.path.join(st, "reported", jobs.HEARD)).read()
          == "abc123\n"
          and not os.path.exists(os.path.join(old, "live", "jobs.reported"))
          and not os.path.exists(os.path.join(st, "jobs.reported"))
          and not os.path.exists(os.path.join(old, "live", "coach.woken")))
    check("a Colibri task and its claim flag land in relay/state/colibri/, and "
          "a mission that is not a task stays in live/missions/",
          sorted(os.listdir(os.path.join(st, "colibri")))
          == ["coli-a.json", "coli-a.task.1"]
          and os.listdir(os.path.join(old, "live", "missions"))
          == ["t0007.json"])
    before = snapshot(old)
    check("and a second run changes nothing",
          jobs.migrate_state(old) == 0 and snapshot(old) == before)
    check("the new paths are ignored by git",
          all(git_ok(old, "check-ignore", "-q", rel) for rel in (
              "relay/state/jobs.jsonl", "relay/state/reported/1001",
              "relay/state/colibri/coli-a.json"))
          and subprocess.run(["git", "status", "--porcelain",
                              "--untracked-files=all"], cwd=old,
                             stdout=subprocess.PIPE).stdout.strip() == b"")

    # A claim an old writer left behind after the move is still a claim.
    write(os.path.join(old, "live", "jobs.reported", "relay-r2.failed"), "")
    check("hearing reads a claim from the old place too",
          jobs._claim_once(old, "relay-r2.failed") is False
          and os.path.isfile(os.path.join(st, "reported", "relay-r2.failed")))
    write(os.path.join(st, "jobs.reported", "3003"), "")
    check("and so does the poll's claim on a job's ending",
          jobs._claim(old, "3003", now=time.time()) is False
          and jobs._claim(old, "3004", now=time.time()) is True)

    # A job submitted before the move ends after it: reported exactly once.
    write(os.path.join(old, "live", "jobs.jsonl"), json.dumps(
        {"jobid": "4004", "label": "knn", "submitted": 10.0,
         "exitfile": "relay/state/k.exit"}) + "\n")
    write(os.path.join(st, "k.exit"), "0\n")
    s4 = Slurm()
    got = jobs.report(old, run=s4, now=1000.0)
    again = jobs.report(old, run=s4, now=1100.0)
    woke = cluster.notices(old)
    check("a job registered before the move is reported exactly once",
          [r["jobid"] for r in got] == ["4004"] and again == []
          and len(woke) == 1 and "4004" in woke[0]["text"])
finally:
    shutil.rmtree(old, ignore_errors=True)

# Every reader calls it first: a bare read finds the old records.
first = tempfile.mkdtemp(prefix="tutor-firstread-")
try:
    write(os.path.join(first, "live", "jobs.jsonl"),
          json.dumps({"jobid": "5005", "label": "x", "submitted": 1.0}) + "\n")
    check("a reader migrates first: `records` sees the old registry, moved",
          list(jobs.records(first)) == ["5005"]
          and os.path.isfile(os.path.join(first, "relay", "state",
                                          "jobs.jsonl"))
          and not os.path.exists(os.path.join(first, "live", "jobs.jsonl")))
finally:
    shutil.rmtree(first, ignore_errors=True)


# --- TRD-EHR's whole report history over its old claims wakes nothing ------------
ARCHIVE = os.path.expanduser(
    "~/Archive/atlas-migration/2026-10-07/live-dirs.tgz")
TRD = [rel for rel in ("projects/TRD-EHR",)
       if os.path.isdir(os.path.join(REPO, rel, "relay", "reports"))]
if not os.path.isfile(ARCHIVE) or not TRD:
    print("ok   (skipped: no %s here, so TRD-EHR's old claims cannot be "
          "read)" % ("live-dirs.tgz" if TRD else "TRD-EHR"))
else:
    import tarfile
    trd_rel = TRD[0]
    hist = tempfile.mkdtemp(prefix="tutor-trdhear-")
    try:
        def subject_copy(name):
            """A repository holding TRD-EHR's requests and reports, committed
            over an empty base, and the base's sha."""
            top = os.path.join(hist, name)
            ws = os.path.join(top, trd_rel)
            os.makedirs(ws)
            git(top, "init", "-q", "-b", "main")
            git(top, "config", "user.email", "t@example.com")
            git(top, "config", "user.name", "t")
            write(os.path.join(top, ".gitignore"), "**/relay/state/\nlive/\n")
            git(top, "add", "-A")
            git(top, "commit", "-q", "-m", "base")
            base_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=top,
                                      stdout=subprocess.PIPE,
                                      universal_newlines=True).stdout.strip()
            for part in ("requests", "reports"):
                shutil.copytree(os.path.join(REPO, trd_rel, "relay", part),
                                os.path.join(ws, "relay", part))
            for f in ("tutorboard.json",):
                if os.path.isfile(os.path.join(REPO, trd_rel, f)):
                    shutil.copy(os.path.join(REPO, trd_rel, f),
                                os.path.join(ws, f))
            git(top, "add", "-A")
            git(top, "commit", "-q", "-m", "TRD-EHR's report history")
            return ws, base_sha

        def woken(ws):
            # Every line hearing dropped: none of these requests names a
            # live session, so each is a notice under the copy's root.
            return cluster.notices(cluster.atlas_of(ws), limit=0)

        ended = [n for n in os.listdir(os.path.join(REPO, trd_rel, "relay",
                                                    "reports"))
                 if n.endswith(".json") and json.load(open(os.path.join(
                     REPO, trd_rel, "relay", "reports", n))).get("state")
                 in jobs.ENDED_REPORTS]

        # The control: with no claims, every ended report in the range wakes.
        bare, base_sha = subject_copy("bare")
        write(os.path.join(bare, "relay", "state", "reported", jobs.HEARD),
              base_sha + "\n")
        jobs.hear(bare, now=1.0)
        check("with no claims, hearing the whole history wakes every ended "
              "report (%d)" % len(ended), len(woken(bare)) == len(ended) > 0)

        # The real thing: the archive's old claims, in live/jobs.reported/.
        ws, base_sha = subject_copy("claimed")
        with tarfile.open(ARCHIVE, "r:gz") as tar:
            want = [m for m in tar.getmembers() if m.isfile()
                    and m.name.endswith("/TRD-EHR/live/jobs.reported/"
                                        + os.path.basename(m.name))]
            for m in want:
                data = tar.extractfile(m).read()
                write(os.path.join(ws, "live", "jobs.reported",
                                   os.path.basename(m.name)),
                      data.decode("utf-8"))
        # Heard from before the first report, so every report is in range.
        write(os.path.join(ws, "live", "jobs.reported", jobs.HEARD),
              base_sha + "\n")
        check("the archive holds a claim for every ended TRD-EHR report",
              sorted(os.path.basename(m.name) for m in want
                     if not m.name.endswith(jobs.HEARD))
              == sorted("relay-%s.%s" % (n[:-len(".json")], json.load(open(
                  os.path.join(REPO, trd_rel, "relay", "reports", n)))
                  ["state"]) for n in ended))
        heard = jobs.hear(ws, now=1.0)
        check("jobs.hear over TRD-EHR's full report history and its old "
              "live/jobs.reported wakes nothing",
              heard == [] and woken(ws) == []
              and not os.path.exists(os.path.join(ws, "live",
                                                  "jobs.reported")))
        check("and the claims now sit in relay/state/reported/",
              len(os.listdir(os.path.join(ws, "relay", "state", "reported")))
              == len(want))
        check("and a second hearing wakes nothing either",
              jobs.hear(ws, now=2.0) == [] and woken(ws) == [])
    finally:
        shutil.rmtree(hist, ignore_errors=True)

# --- a request is pinned to the commit it was filed after --------------------
pin = tempfile.mkdtemp(prefix="tutor-pin-")
try:
    git(pin, "init", "-q", "-b", "main")
    git(pin, "config", "user.email", "t@example.com")
    git(pin, "config", "user.name", "t")
    subj = os.path.join(pin, "projects", "P")
    write(os.path.join(subj, "fit.py"), "x = 1\n")
    write(os.path.join(pin, "elsewhere.md"), "a\n")
    git(pin, "add", "-A")
    git(pin, "commit", "-q", "-m", "start")
    req = {"id": "2026-10-08-pin", "kind": "colibri", "brief": "count rows"}
    write(os.path.join(subj, "fit.py"), "x = 2\n")
    target, done, said = jobs.file_request(subj, req, push=False)
    check("a tracked file under the subject differing from HEAD files "
          "nothing, saying board push first",
          not done and "board push first" in said and "fit.py" in said
          and not os.path.exists(target) and jobs.dirty(subj) == ["fit.py"])
    git(pin, "checkout", "--", "projects/P/fit.py")
    write(os.path.join(pin, "elsewhere.md"), "b\n")
    at = subprocess.run(["git", "rev-parse", "HEAD"], cwd=pin,
                        stdout=subprocess.PIPE,
                        universal_newlines=True).stdout.strip()
    target, done, said = jobs.file_request(subj, req, push=False)
    filed = jobs.requests(subj)
    check("an edit outside the subject does not stop it, and the request is "
          "stamped with HEAD before its own commit",
          done and len(filed) == 1 and filed[0]["commit"] == at
          and jobs.head(subj) != at)
    check("which HEAD contains, so the pin passes",
          jobs.pin_problems(subj, filed[0]) == [])
    check("a commit HEAD lacks is refused, naming it",
          "does not contain commit 0123456789ab" in " ".join(
              jobs.pin_problems(subj, dict(filed[0], commit="0123456789ab"
                                           + "c" * 28))))
    check("an unpinned request is not refused for it",
          jobs.pin_problems(subj, req) == [])
    check("`commit` is a known key, and a sha",
          "commit" in jobs.REQUEST_KEYS["recipe"]
          and "commit" in jobs.REQUEST_KEYS["colibri"]
          and jobs.validate(dict(req, commit="nope"), [], [], {},
                            colibri=True)[1] == ["`commit` is a commit's hex "
                                                 "sha"]
          and jobs.validate(dict(req, commit=at), [], [], {},
                            colibri=True)[0]["commit"] == at)
finally:
    shutil.rmtree(pin, ignore_errors=True)

# --- `board job --batch`: many requests, one commit, one push -----------------
bat = tempfile.mkdtemp(prefix="tutor-batch-")
try:
    origin = os.path.join(bat, "origin.git")
    subprocess.run(["git", "init", "-q", "--bare", origin], check=True)
    top = os.path.join(bat, "repo")
    os.makedirs(top)
    git(top, "init", "-q", "-b", "main")
    git(top, "config", "user.email", "t@example.com")
    git(top, "config", "user.name", "t")
    subj = os.path.join(top, "projects", "P")
    write(os.path.join(subj, ".gitignore"), "relay/state/\nresults/\n")
    write(os.path.join(subj, "tutorboard.json"), json.dumps(
        {"name": "P", "relay": {"exports": [{"glob": "results/*.png"}]}}))
    write(os.path.join(subj, "slurm", "sweep.sbatch"),
          "#!/bin/bash\n#SBATCH --job-name=sweep\n"
          "#RELAY-VAR K [0-9]{1,3}\n\necho \"RELAY: done $K\"\n")
    git(top, "add", "-A")
    git(top, "commit", "-q", "-m", "start")
    git(top, "remote", "add", "origin", origin)
    git(top, "push", "-q", "-u", "origin", "main")
    benv = dict(os.environ, TUTOR_SLURM="0",
                TUTORBOARD_SESSION=os.path.join(bat, "sessions",
                                                "20261009-120000"))

    def bboard(*args, **extra):
        p = subprocess.run([sys.executable, BOARD] + list(args), cwd=subj,
                           env=dict(benv, **extra), stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=180)
        return p.returncode, p.stdout.decode("utf-8", "replace")

    def count():
        return int(subprocess.run(["git", "rev-list", "--count", "HEAD"],
                                  cwd=top, stdout=subprocess.PIPE,
                                  universal_newlines=True).stdout.strip())

    before, start_head = count(), jobs.head(subj)
    spec = os.path.join(bat, "batch.json")
    bad = [{"recipe": "slurm/sweep.sbatch", "env": {"K": str(k)},
            "label": "sweep"} for k in range(4)]
    bad.append({"recipe": "slurm/sweep.sbatch", "env": {"K": "x"},
                "thread": "t"})
    write(spec, json.dumps(bad))
    code, out = bboard("job", "--batch", spec)
    check("a batch with one bad entry files nothing, naming the entry and "
          "what it may not say", code == 1 and "entry 5" in out
          and "`thread`" in out and count() == before
          and not os.path.isdir(os.path.join(subj, "relay", "requests")))
    write(spec, json.dumps(bad[:4] + [{"recipe": "slurm/sweep.sbatch",
                                       "env": {"K": "x"}}]))
    code, out = bboard("job", "--batch", spec)
    check("and so does an entry `board job` would refuse",
          code == 1 and "entry 5" in out and "K" in out
          and count() == before)
    code, out = bboard("job", "--batch", spec, TUTOR_SLURM="1")
    check("with Slurm a batch is refused: `board job` submits directly",
          code == 1 and "Slurm" in out and count() == before)
    good = bad[:4] + [{"recipe": "slurm/sweep.sbatch", "env": {"K": "9"},
                       "label": "last", "export": ["results/k.png"],
                       "produces": ["results/k.csv"]}]
    write(spec, json.dumps(good))
    code, out = bboard("job", "--batch", spec)
    files = subprocess.run(["git", "show", "--name-only", "--format=",
                            "HEAD"], cwd=top, stdout=subprocess.PIPE,
                           universal_newlines=True).stdout.split()
    filed = jobs.requests(subj)
    check("a batch of 5 requests is one commit with 5 request files",
          code == 0 and "5 requests filed" in out and count() == before + 1
          and len(files) == 5 and all(
              f.startswith("projects/P/relay/requests/") for f in files))
    check("and one push: origin is at that commit",
          jobs.head(subj) == subprocess.run(
              ["git", "rev-parse", "main"], cwd=origin,
              stdout=subprocess.PIPE, universal_newlines=True).stdout.strip())
    check("each a recipe request pinned to HEAD before the batch, with its "
          "own id, values and the session",
          len(filed) == 5 and len(set(r["id"] for r in filed)) == 5
          and all(r["commit"] == start_head for r in filed)
          and sorted(r["env"]["K"] for r in filed)
          == ["0", "1", "2", "3", "9"]
          and all(r.get("session") == "20261009-120000" for r in filed)
          and [r for r in filed if r.get("label") == "last"][0]["export"]
          == ["results/k.png"]
          and all(jobs.check(subj, r, mine=True)[1] == [] for r in filed))
    code, out = bboard("job", "--batch", spec)
    check("a second batch takes fresh ids rather than colliding",
          code == 0 and len(jobs.requests(subj)) == 10
          and count() == before + 2)
finally:
    shutil.rmtree(bat, ignore_errors=True)

print()
if fails:
    print("%d check(s) failed" % len(fails))
    sys.exit(1)
print("a job is labelled, and reports itself once when it ends")
