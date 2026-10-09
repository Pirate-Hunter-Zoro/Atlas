#!/usr/bin/env python3
"""The Mac hears the cluster inside the board server, and the server gives
way to committed code.

What the checks are about:

  * THE CLUSTER THREAD (`cluster.Ear`). One `git ls-remote` per pass. A pull
    only when origin's main is a commit HEAD lacks: with origin equal to HEAD
    there is none, and when it moves there is one. A failed pull or ls-remote
    is recorded in pull.json. The code refs are kept for T38b.
  * D16. A report wakes its open filing session, reopens an ended one, and
    is a home notice (`/notices.json`) where no session filed it. A notice
    starts no turn.
  * ONE WAKE. A report ends once: one `[job]` line, or `[repair]` for a
    failure the Mac repairs (board/test/repair.py). A fresh clone hears
    nothing of the reports it arrived with.
  * FRESHNESS. A server with TUTORBOARD_FRESH=1 exits 0 once committed board
    code changed and no turn runs: a commit mid-turn waits for the turn. An
    uncommitted edit triggers no exit.
  * ONE LAUNCHAGENT. The plist lints, renders with an absolute interpreter,
    KeepAlive and ThrottleInterval 10; ship.sh kickstarts it; the old
    restart commands refuse and name it.
  * ONE PATH ON BOTH MACHINES. A `results/` path the tree lacks is read from
    `exports/results/` by the thread check and the results library.

With TUTORBOARD_REHEARSE_LAUNCHD=1 it also rehearses the LaunchAgent for
real, under the label tutor-board.rehearsal on port 8779 against copies: a
committed change makes the server exit 0 and launchd start it again with the
same interpreter; then the job is booted out. The suite leaves it off.

Synthetic repositories only: a bare origin, a "Mac" clone and a "cluster"
clone, with `TUTOR_SLURM=0` standing in for the Mac.
"""
import json
import os
import plistlib
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
box = tempfile.mkdtemp(prefix="tutor-hearing-box-")
os.environ["TUTOR_SLURM"] = "0"
os.environ["BOARD_STATE_DIR"] = os.path.join(box, "state")
os.environ["XDG_CONFIG_HOME"] = os.path.join(box, "config")
os.environ["TUTORBOARD_TRASH"] = os.path.join(box, "trash")
os.environ["BOARD_NO_TAILNET"] = "1"
for name in ("TUTORBOARD_SESSION", "TUTORBOARD_TURN", "TUTORBOARD_PORT",
             "TUTORBOARD_CLUSTER", "TUTORBOARD_FRESH"):
    os.environ.pop(name, None)
from tutorboard import cluster, gitops, holds, jobs, paths, sessions, stamp  # noqa: E402
from tutorboard.course import results, threads                         # noqa: E402
from tutorboard.runner import service                                  # noqa: E402
from tutorboard.runner import turn as runturn                          # noqa: E402
from tutorboard.server import app                                      # noqa: E402

fails = []


def check(name, cond, detail=""):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name + (("\n       " + str(detail)[:1500]) if detail else ""))


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def git(cwd, *args):
    p = subprocess.run(["git"] + list(args), cwd=cwd, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, check=False)
    return p.stdout.decode("utf-8", "replace")


def until(cond, timeout=30.0, step=0.2):
    end = time.time() + timeout
    while time.time() < end:
        got = cond()
        if got:
            return got
        time.sleep(step)
    return cond()


def lines_of(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return [json.loads(l) for l in fh if l.strip()]
    except OSError:
        return []


class FakeRunner(object):
    """Stands in for the server's runner: `cluster.wake` queues through it."""

    def __init__(self, atlas):
        self.atlas = atlas
        self.woken = []

    def wake(self, sid):
        self.woken.append(sid)
        return True


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
    git(mac, "config", "user.email", "t@example.com")
    git(mac, "config", "user.name", "t")
    ws = os.path.join(mac, "projects", "Proj")
    write(os.path.join(mac, ".gitignore"), "/sessions/\n")
    # Anchored: an unanchored `results/` would hide `exports/results/` too.
    write(os.path.join(ws, ".gitignore"), "/results/\nrelay/state/\n")
    write(os.path.join(ws, "tutorboard.json"), json.dumps({"name": "Proj"}))
    write(os.path.join(ws, "slurm", "sweep.sbatch"), RECIPE)
    write(threads.path(ws), json.dumps(SPINE))
    git(mac, "add", "-A")
    git(mac, "commit", "-q", "-m", "start")
    git(mac, "remote", "add", "origin", origin)
    git(mac, "push", "-q", "-u", "origin", "main")
    cluster_top = os.path.join(base, "cluster")
    git(base, "clone", "-q", origin, cluster_top)
    git(cluster_top, "config", "user.email", "c@example.com")
    git(cluster_top, "config", "user.name", "c")
    cws = os.path.join(cluster_top, "projects", "Proj")
    os.environ["TUTORBOARD_COURSES"] = mac
    state = os.path.join(base, "state")
    runner = service.install(FakeRunner(mac))

    def head(where):
        return git(where, "rev-parse", "HEAD").strip()

    def origin_main():
        return git(origin, "rev-parse", "main").strip()

    def cluster_commit(rel, text, msg="the cluster moves on"):
        git(cluster_top, "pull", "-q", "--ff-only")
        write(os.path.join(cluster_top, rel), text)
        git(cluster_top, "add", "-A")
        git(cluster_top, "commit", "-q", "-m", msg)
        git(cluster_top, "push", "-q")

    def pull_state():
        try:
            with open(os.path.join(state, cluster.PULL_STATE)) as fh:
                return json.load(fh)
        except (OSError, ValueError):
            return {}

    # --- the cluster thread: one ls-remote, a pull only on change -------------
    ear = cluster.Ear(mac, state_dir=state, say=lambda m: None)
    check("the ear's cadence is twenty seconds, and an ls-remote ten",
          cluster.EVERY == 20 and cluster.LS_TIMEOUT == 10
          and not hasattr(jobs, "PULL_EVERY") and not hasattr(jobs, "pull_due")
          and not hasattr(gitops, "hear_pass"))
    got = ear.once()
    check("with origin's main equal to HEAD there is no pull",
          got["pulled"] is False and ear.pulls == 0 and ear.main == head(mac))
    cluster_commit("notes/one.txt", "one\n")
    got = ear.once()
    check("when origin's main differs there is one pull, and HEAD is there",
          got["pulled"] is True and ear.pulls == 1
          and head(mac) == origin_main())
    check("pull.json says the pull went through",
          pull_state().get("ok") is True and pull_state().get("step") == "pull")
    got = ear.once()
    check("and the next pass pulls nothing", got["pulled"] is False
          and ear.pulls == 1)
    write(os.path.join(mac, "notes", "mac.txt"), "mine\n")
    git(mac, "add", "-A")
    git(mac, "commit", "-q", "-m", "a Mac commit not yet pushed")
    ear.once()
    check("a Mac ahead of origin is not pulled: HEAD contains origin's main",
          ear.pulls == 1)
    git(mac, "push", "-q")

    git(cluster_top, "pull", "-q", "--ff-only")
    git(cluster_top, "push", "-q", "origin", "HEAD:refs/heads/code/20261009-120000")
    ear.once()
    check("the code refs are kept on the ear, for T38b",
          ear.code == {"refs/heads/code/20261009-120000": head(cluster_top)}
          and ear.pulls == 1)
    git(cluster_top, "push", "-q", "origin", ":refs/heads/code/20261009-120000")
    ear.once()
    check("and a deleted one is gone", ear.code == {})

    # A pull that cannot fast-forward is recorded, and the next good pass clears it.
    write(os.path.join(mac, "notes", "diverge.txt"), "mac side\n")
    git(mac, "add", "-A")
    git(mac, "commit", "-q", "-m", "the Mac diverges")
    cluster_commit("notes/two.txt", "two\n")
    got = ear.once()
    rec = pull_state()
    check("a pull that fails is recorded in pull.json, with origin's sha",
          got["pulled"] is False and ear.pulls == 2 and rec.get("ok") is False
          and rec.get("step") == "pull" and rec.get("said")
          and rec.get("remote") == origin_main(), rec)
    git(mac, "reset", "-q", "--hard", "origin/main")
    git(mac, "pull", "-q", "--ff-only")
    ear.once()
    check("and once HEAD has origin's main the record says ok again",
          pull_state().get("ok") is True and ear.pulls == 2, pull_state())
    git(mac, "remote", "set-url", "origin", os.path.join(base, "nowhere.git"))
    got = ear.once()
    check("an ls-remote that fails pulls nothing and is recorded",
          got["pulled"] is None and pull_state().get("step") == "ls-remote"
          and pull_state().get("ok") is False and ear.pulls == 2)
    git(mac, "remote", "set-url", "origin", origin)
    ear.once()

    # --- sessions: one open, one ended -------------------------------------------
    s_open = sessions.new("open one", base=mac, now=time.time() - 60)["id"]
    sessions.bind(s_open, "projects/Proj", base=mac)
    s_ended = sessions.new("ended one", base=mac)["id"]
    sessions.bind(s_ended, "projects/Proj", base=mac)
    sessions.end(s_ended, base=mac)
    check("the fixture has an open session and an ended one",
          not sessions.get(s_open, mac)["ended"]
          and sessions.get(s_ended, mac)["ended"])

    def inbox(sid):
        return [m for m in lines_of(os.path.join(mac, "sessions", sid, "inbox",
                                                  "messages.jsonl"))
                if m.get("signal") != "bind"]

    def notices():
        return cluster.notices(mac)

    # --- a request filed from the open session -----------------------------------
    req = {"id": "2026-10-03-knn-sweep", "kind": "recipe", "label": "knn",
           "recipe": "slurm/sweep.sbatch", "env": {"EMBEDDER": "bge-small"},
           "produces": ["results/knn/best.json"],
           "export": ["results/knn/sweep.png"], "filed": 1100.0,
           "session": s_open}
    _, ok, said = jobs.file_request(ws, req, push=False)
    git(mac, "push", "-q")
    check("the request is committed", ok, said)
    check("filing records the heard baseline, in an ignored ledger",
          os.path.isfile(os.path.join(ws, "relay", "state", "reported",
                                      jobs.HEARD))
          and git(mac, "status", "--porcelain").strip() == "")
    threads._cache.clear()
    lines = jobs.thread_relay(ws, "knn")
    check("`board brief` lists the request still out",
          any("Waiting on the cluster" in l for l in lines)
          and any("2026-10-03-knn-sweep" in l and "requested" in l
                  for l in lines))

    def cluster_reports(rep):
        cluster_commit("projects/Proj/relay/reports/%s.json" % rep["id"],
                       json.dumps(rep), "relay report " + rep["id"])

    cluster_reports({"id": req["id"], "state": "running", "jobid": "88",
                     "submitted": 1200.0})
    got = ear.once()
    check("a running report pulled in wakes nothing", got["pulled"] is True
          and got["heard"] == [] and inbox(s_open) == [] and notices() == []
          and runner.woken == [])

    write(os.path.join(cws, "exports", "results", "knn", "sweep.png"),
          "\x89PNG" + "x" * 2000)
    cluster_reports({"id": req["id"], "state": "failed", "jobid": "88",
                     "exit": "1:0", "ended": "2026-10-03T10:00:00",
                     "submitted": 1200.0, "produced": [],
                     "exported": ["results/knn/sweep.png"],
                     "relay": ["RELAY: k=300 best", "RELAY: then it fell over"],
                     "note": "the sweep ran out of memory at k=500",
                     "session": s_open})
    got = ear.once()
    msgs = inbox(s_open)
    check("the ended report is heard on the pass that pulled it",
          got["pulled"] is True
          and [h.get("request") for h in got["heard"]] == [req["id"]])
    check("a report wakes its open filing session: one [repair] line in its "
          "inbox, unread, signalled repair, and a turn queued",
          len(msgs) == 1 and msgs[0]["signal"] == "repair"
          and msgs[0]["text"].startswith("[repair]") and not msgs[0]["read"]
          and msgs[0]["request"] == req["id"] and msgs[0]["session"] == s_open
          and runner.woken == [s_open] and notices() == [], (msgs, runner.woken))
    text = msgs[0]["text"] if msgs else ""
    check("it wakes a turn the way a local ending does, under its own signal",
          runturn.turn_signal("[2026-10-03 10:00:00] " + text) == "repair")
    check("it says what ended, the exit, what is missing and what landed",
          "failed" in text and "1:0" in text
          and "MISSING results/knn/best.json" in text
          and "landed   results/knn/sweep.png" in text)
    check("it carries the RELAY: lines and the note, and no log",
          "RELAY: k=300 best" in text and "out of memory" in text
          and "relay/reports/%s.json" % req["id"] in text)
    check("it tells the turn to repair it here, rerunning through "
          "`board job --fixes` or asking through `board diagnose`",
          "board job --label knn --fixes %s" % req["id"] in text
          and "board diagnose --fixes %s" % req["id"] in text
          and "board push" in text and "ask-cluster" not in text)

    got = ear.once()
    check("heard once: the next pass drops nothing",
          got["heard"] == [] and len(inbox(s_open)) == 1
          and runner.woken == [s_open])
    shutil.rmtree(os.path.join(ws, "relay", "state", "reported"))
    git(mac, "commit", "-q", "--allow-empty", "-m", "elsewhere")
    jobs.hear(ws)
    check("a lost ledger is a new baseline, not a second wake",
          len(inbox(s_open)) == 1 and notices() == [])

    lines = jobs.thread_relay(ws, "knn")
    check("`board brief` gives the last report, its RELAY lines and note",
          any(l.startswith("The last cluster report: 2026-10-03-knn-sweep, "
                           "failed, exit 1:0") for l in lines)
          and "  RELAY: k=300 best" in lines
          and any("out of memory" in l for l in lines)
          and not any("Waiting" in l for l in lines))

    # --- a request from the ended session reopens it ------------------------------
    req2 = dict(req, id="2026-10-03-knn-again", filed=1700.0, session=s_ended)
    jobs.file_request(ws, req2, push=False)
    git(mac, "push", "-q")
    cluster_reports({"id": req2["id"], "state": "completed", "jobid": "89",
                     "exit": "0:0", "ended": "2026-10-03T11:00:00",
                     "produced": ["results/knn/best.json"], "exported": []})
    ear.once()
    msgs = inbox(s_ended)
    check("a report for an ended session reopens it, lands in its inbox and "
          "queues a turn", sessions.get(s_ended, mac)["ended"] is None
          and len(msgs) == 1 and msgs[0]["signal"] == "job"
          and msgs[0]["text"].startswith("[job]")
          and runner.woken == [s_open, s_ended], (msgs, runner.woken))

    # --- a request with no session is a notice, and starts no turn -----------------
    req3 = dict(req, id="2026-10-03-knn-third", filed=1800.0)
    del req3["session"]
    jobs.file_request(ws, req3, push=False)
    req4 = dict(req, id="2026-10-03-knn-gone", filed=1801.0,
                session="20200101-000000")
    jobs.file_request(ws, req4, push=False)
    git(mac, "push", "-q")
    cluster_reports({"id": req3["id"], "state": "refused",
                     "problems": ["env DATA is not declared"]})
    cluster_reports({"id": req4["id"], "state": "refused",
                     "problems": ["env DATA is not declared"]})
    ear.once()
    got = notices()
    check("a refusal arriving in the first pull after filing is heard, and "
          "with no session it is a notice", len(got) == 2
          and set(n.get("request") for n in got) == {req3["id"], req4["id"]}
          and all("refused" in n["text"] and "env DATA is not declared"
                  in n["text"] for n in got), got)
    check("each notice names its subject, the session it named, and an id",
          all(n["subject"] == "projects/Proj" and n.get("id") for n in got)
          and set(n["session"] for n in got) == {None, "20200101-000000"})
    check("a notice starts no turn, and no session's inbox grows",
          runner.woken == [s_open, s_ended] and len(inbox(s_open)) == 1
          and len(inbox(s_ended)) == 1)
    check("sessions/.notices.jsonl is the notices' file, and git ignores it",
          os.path.isfile(os.path.join(mac, "sessions", ".notices.jsonl"))
          and git(mac, "status", "--porcelain").strip() == "")

    httpd = app.make_server(mac, 0, start=False)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        with urllib.request.urlopen("http://127.0.0.1:%d/notices.json"
                                    % httpd.server_port, timeout=30) as r:
            served = json.loads(r.read().decode())
    finally:
        httpd.shutdown()
    check("/notices.json serves them, newest first",
          served.get("ok") and sorted(n["request"] for n in served.get("notices", []))
          == sorted([req4["id"], req3["id"]])
          and served["notices"][0]["t"] >= served["notices"][-1]["t"], served)

    # --- a held step's check: one [coach] line, never a [job] one -----------------
    cluster_commit("projects/Proj/relay/holds/knn.json", json.dumps(
        {"thread": "knn", "files": ["src/knn.py"], "at": 1900.0}), "knn: hold")
    before = len(notices())
    cluster_reports({"id": "check-knn-1", "thread": "knn", "step": 1,
                     "state": "completed", "check": "src/knn.py", "exit": 0,
                     "relay": ["n=120 mean=0.42"]})
    ear.once()
    new = notices()[:len(notices()) - before]
    check("a pulled check report drops exactly one [coach] line, no [job] line",
          len(new) == 1 and new[0]["signal"] == "coach"
          and new[0]["text"].startswith("[coach] Step 1 of thread knn")
          and not any(m["text"].startswith("[job]") for m in new), new)
    ear.once()
    check("and the next pass drops nothing more", len(notices()) == before + 1)
    check("holds keeps no cadence of its own",
          not hasattr(holds, "POLL_SECONDS") and not hasattr(holds, "poll_seconds"))

    # --- the pass clones nothing but ai-config ---------------------------------
    # A fake `git` and `gh` on PATH log every call (git delegates the rest to
    # the real one), and the pass runs the real bootstrap.sh when ai-config is
    # missing.
    os.makedirs(os.path.join(mac, "board"))
    shutil.copy(os.path.join(ROOT, "bootstrap.sh"),
                os.path.join(mac, "board", "bootstrap.sh"))
    write(os.path.join(mac, "courses", "Topology", "tutorboard.json"),
          json.dumps({"name": "Topology", "phi": False}))
    fakes = os.path.join(base, "fakebin")
    calls_log = os.path.join(base, "calls.log")
    write(os.path.join(fakes, "git"),
          '#!/bin/bash\necho "git $*" >> "%s"\n'
          'case "$1" in clone) exit 1 ;; esac\nexec "%s" "$@"\n'
          % (calls_log, shutil.which("git")))
    write(os.path.join(fakes, "gh"),
          '#!/bin/bash\necho "gh $*" >> "%s"\nexit 1\n' % calls_log)
    os.chmod(os.path.join(fakes, "git"), 0o755)
    os.chmod(os.path.join(fakes, "gh"), 0o755)

    def clones():
        try:
            with open(calls_log, encoding="utf-8") as fh:
                return [l.split() for l in fh
                        if l.split()[1:2] == ["clone"]
                        or l.split()[1:3] == ["repo", "clone"]]
        except OSError:
            return []

    saved_path = os.environ["PATH"]
    os.environ["PATH"] = fakes + os.pathsep + saved_path
    try:
        ear.once()
        tried = clones()
        check("with ai-config missing, the pass tries to clone ai-config and "
              "nothing else",
              len(tried) >= 1
              and all(gitops.AI_CONFIG_URL in l
                      or "Pirate-Hunter-Zoro/ai-config" in l for l in tried)
              and not any("Topology" in " ".join(l) for l in tried), tried)
        os.makedirs(os.path.join(mac, "ai-config", ".git"))
        os.remove(calls_log)
        ear.once()
        check("with ai-config there, a pass records no clone attempt",
              clones() == [])
    finally:
        os.environ["PATH"] = saved_path
    shutil.rmtree(os.path.join(mac, "ai-config"))
    shutil.rmtree(os.path.join(mac, "board"))
    shutil.rmtree(os.path.join(mac, "courses"))

    # --- a nested repository is refused, generically ---------------------------
    nested = os.path.join(ws, "vendored", "thing")
    os.makedirs(os.path.join(nested, ".git"))
    req5 = dict(req, id="2026-10-03-nested-sweep", filed=2300.0)
    said5 = jobs.file_request(ws, req5, push=False)
    check("a request filed in a subject holding a nested .git is refused, "
          "naming where", said5[1] is False and "own .git" in said5[2]
          and "vendored" in said5[2])
    check("and nothing is written", not os.path.exists(said5[0]))
    shutil.rmtree(os.path.join(ws, "vendored"))
    check("jobs.nested_git finds nothing in a plain subject",
          jobs.nested_git(ws) == "")

    # --- a fresh clone -----------------------------------------------------------
    fresh = os.path.join(base, "fresh")
    git(base, "clone", "-q", origin, fresh)
    fws = os.path.join(fresh, "projects", "Proj")
    check("a fresh clone hears nothing of the reports it arrived with",
          jobs.hear(fws) == [] and jobs.hear(fws) == []
          and cluster.notices(fresh) == []
          and not os.path.exists(os.path.join(fresh, "sessions")))

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
    service.install(None)
    os.environ.pop("TUTORBOARD_COURSES", None)
    shutil.rmtree(base, ignore_errors=True)

# --- one malformed request does not stop a reader ---------------------------------
ORIGIN = "2026-10-02-knn-sweep"
FIRST = {"id": ORIGIN, "kind": "recipe", "thread": "knn",
         "recipe": "slurm/sweep.sbatch", "env": {"EMBEDDER": "bge-small"},
         "produces": ["results/knn/best.json"], "export": [], "filed": 100.0}
scenes = tempfile.mkdtemp(prefix="tutor-fixing-")


def scene(reqs):
    """A workspace on disk holding these requests. `{id: rec}`."""
    ws = tempfile.mkdtemp(dir=scenes)
    write(threads.path(ws), json.dumps(SPINE))
    for r in reqs:
        write(os.path.join(ws, "relay", "requests", r["id"] + ".json"),
              json.dumps(r))
    threads._cache.clear()
    return ws, dict((r["request"], r) for r in jobs.relayed(ws))


try:
    ws, recs = scene([dict(FIRST, filed="soon")])
    check("a malformed `filed` reads as 0 in the registry, and every reader "
          "still reads it", recs[ORIGIN]["submitted"] == 0.0
          and jobs.open_fix(ws, "slurm/sweep.sbatch") == ""
          and jobs.context(ws)["failed"] == set())

    ws, recs = scene([dict(FIRST, env=["EMBEDDER", "x"], produces="out.csv",
                           export=7)])
    check("and so do a malformed `env`, `produces` and `export`",
          recs[ORIGIN]["produces"] == [] and recs[ORIGIN]["export"] == []
          and recs[ORIGIN]["cmd"].startswith("slurm/sweep.sbatch")
          and jobs.context(ws)["failed"] == set()
          and jobs.open_fix(ws, "slurm/sweep.sbatch") == "")
finally:
    shutil.rmtree(scenes, ignore_errors=True)


# ===========================================================================
# one LaunchAgent, and the commands it replaces
# ===========================================================================
TEMPLATE = os.path.join(ROOT, "scripts", "launchd", "tutor-board.plist")
check("scripts/launchd holds the one agent, tutor-board, and no other",
      sorted(os.listdir(os.path.dirname(TEMPLATE))) == ["tutor-board.plist"]
      and not os.path.exists(os.path.join(ROOT, "scripts", "tutor-pull")))
lint = subprocess.run(["plutil", "-lint", TEMPLATE], stdout=subprocess.PIPE,
                      stderr=subprocess.STDOUT, universal_newlines=True)
check("`plutil -lint` passes on the template", lint.returncode == 0, lint.stdout)
rendered = os.path.join(box, "tutor-board.plist")
p = subprocess.run(["bash", os.path.join(ROOT, "install.sh"), "--plist"],
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
with open(rendered, "wb") as fh:
    fh.write(p.stdout)
lint = subprocess.run(["plutil", "-lint", rendered], stdout=subprocess.PIPE,
                      stderr=subprocess.STDOUT, universal_newlines=True)
check("`install.sh --plist` renders it, and `plutil -lint` passes on that too",
      p.returncode == 0 and lint.returncode == 0,
      p.stderr.decode("utf-8", "replace") + lint.stdout)
try:
    job = plistlib.loads(p.stdout)
except Exception:                                            # noqa: BLE001
    job = {}
args = job.get("ProgramArguments") or [""]
envs = job.get("EnvironmentVariables") or {}
home = os.path.expanduser("~")
check("label tutor-board, KeepAlive true, ThrottleInterval 10",
      job.get("Label") == "tutor-board" and job.get("KeepAlive") is True
      and job.get("ThrottleInterval") == 10, job)
check("an absolute interpreter that exists, running this tree's serve.py",
      os.path.isabs(args[0]) and os.access(args[0], os.X_OK)
      and args[1:] == [os.path.join(ROOT, "serve.py")], args)
check("TUTORBOARD_CLUSTER=1 and a PATH holding /opt/homebrew/bin",
      envs.get("TUTORBOARD_CLUSTER") == "1" and envs.get("TUTORBOARD_FRESH") == "1"
      and "/opt/homebrew/bin" in envs.get("PATH", "").split(":"), envs)
log = os.path.join(home, ".local", "state", "tutor-board", "server.log")
check("stdout and stderr go to ~/.local/state/tutor-board/server.log",
      job.get("StandardOutPath") == log and job.get("StandardErrorPath") == log)
inst = open(os.path.join(ROOT, "install.sh"), encoding="utf-8").read()
check("install.sh boots out tutor-board.tutor-watch and tutor-board.tutor-pull, "
      "and installs only tutor-board",
      "tutor-board.tutor-pull tutor-board.tutor-watch" in inst
      and 'launchctl bootout "$DOMAIN/$old"' in inst
      and 'LABEL="tutor-board"' in inst and "scripts/launchd/*.plist" not in inst)
ship = open(os.path.join(ROOT, "scripts", "ship.sh"), encoding="utf-8").read()
check("ship.sh restarts with launchctl kickstart -k gui/$(id -u)/tutor-board",
      'TARGET="gui/$(id -u)/tutor-board"' in ship
      and 'launchctl kickstart -k "$TARGET"' in ship
      and "tutor restart" not in ship and "ssh" not in ship)
TUTOR = os.path.join(ROOT, "bin", "tutor")
for argv in (["restart"], ["restart", "--tutors", "--stale"], ["watch"],
             ["pull", "--hear"]):
    p = subprocess.run([sys.executable, TUTOR] + argv, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, universal_newlines=True,
                       timeout=60)
    check("`tutor %s` refuses and names the LaunchAgent" % " ".join(argv),
          p.returncode != 0 and "LaunchAgent tutor-board" in p.stdout, p.stdout)
from tutorboard.runner import daemon  # noqa: E402
refused = daemon.agent_start({}, {"dir": "Proj"}, "fake")
check("`tutor agent start` refuses and names the LaunchAgent",
      refused[0] == 1 and "LaunchAgent tutor-board" in refused[1], refused)


# ===========================================================================
# freshness: a real server on a copy of this tree
# ===========================================================================
CTL = os.path.join(box, "ctl")
CALLS = os.path.join(box, "calls.jsonl")
FAKE = os.path.join(box, "bin", "fake-provider")
write(FAKE, r'''#!/usr/bin/env python3
import json, os, subprocess, sys, time
sid = os.path.basename(os.environ.get("TUTORBOARD_SESSION", ""))
try:
    with open(os.path.join(%(ctl)r, sid)) as fh:
        wait = float(fh.read().strip() or 0)
except (OSError, ValueError):
    wait = 0
with open(%(calls)r, "a") as fh:
    fh.write(json.dumps({"sid": sid, "t": time.time(), "kind": "start"}) + "\n")
time.sleep(wait)
p = subprocess.run(["board", "write", "lesson", "reply"], input="An answer.\n",
                   universal_newlines=True, stdout=subprocess.PIPE,
                   stderr=subprocess.STDOUT)
with open(%(calls)r, "a") as fh:
    fh.write(json.dumps({"sid": sid, "t": time.time(), "kind": "card",
                         "rc": p.returncode, "out": p.stdout}) + "\n")
''' % {"ctl": CTL, "calls": CALLS})
os.chmod(FAKE, 0o755)
write(os.path.join(os.environ["XDG_CONFIG_HOME"], "tutor-board", "config.json"),
      json.dumps({"provider": "fake", "vision_agent": "fake",
                  "concurrency": 2, "headless_timeout": 120,
                  "doing_timeout": 180, "handoff_timeout": 60,
                  "agents": {"fake": {"cmd": [FAKE], "label": "Fake",
                                      "headless_first": [FAKE, "{prompt}"],
                                      "usage": "none"}}}))


def calls(sid, kind):
    return [r for r in lines_of(CALLS) if r["sid"] == sid and r["kind"] == kind]


def copy_tool(top):
    """This tree's board/, as it is on disk, committed in a repository of
    its own at `top`. Its board directory."""
    listed = subprocess.run(
        ["git", "-C", ROOT, "ls-files", "-z", "--cached", "--others",
         "--exclude-standard", "--", "."], stdout=subprocess.PIPE,
        check=True).stdout.decode("utf-8").split("\0")
    board = os.path.join(top, "board")
    for rel in listed:
        if not rel or rel.startswith("test/"):
            continue
        src = os.path.join(ROOT, rel)
        if not os.path.isfile(src) or os.path.islink(src):
            continue
        dst = os.path.join(board, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
    git(top, "init", "-q", "-b", "main")
    write(os.path.join(top, ".gitignore"), "__pycache__/\n*.pyc\n")
    git(top, "add", "-A")
    git(top, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q",
        "-m", "the board")
    return board


def a_fixture_atlas(where):
    write(os.path.join(where, "courses", "Demo", "tutorboard.json"),
          json.dumps({"name": "Demo", "phi": False}))
    write(os.path.join(where, ".gitignore"), "/sessions/\n")
    git(where, "init", "-q", "-b", "main")
    git(where, "add", "-A")
    git(where, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q",
        "-m", "fixture")
    return where


def commit_tool(top, msg):
    git(top, "add", "-A")
    git(top, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q",
        "-m", msg)


tooltop = os.path.join(box, "tool")
tool = copy_tool(tooltop)
fixture = a_fixture_atlas(os.path.join(box, "atlas"))
EDITED = os.path.join(tool, "tutorboard", "news.py")
server = None
try:
    env = dict(os.environ, TUTORBOARD_FRESH="1")
    env.pop("TUTORBOARD_COURSES", None)
    server = subprocess.Popen(
        [sys.executable, os.path.join(tool, "serve.py"), "--port", "0",
         "--atlas", fixture], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        universal_newlines=True, start_new_session=True, env=env)
    said = []
    port = None
    for line in server.stderr:
        said.append(line)
        if "listening on http://" in line:
            port = int(line.split("http://", 1)[1].split("/")[0].split(":")[1])
            break
    threading.Thread(target=lambda: [said.append(l) for l in server.stderr],
                     daemon=True).start()
    stamp.forget()
    first = stamp.tree(tool)
    check("the server logs the code stamp it loaded at boot",
          port and ("code %s;" % first) in "".join(said)
          and "threads: fresh" in "".join(said), "".join(said))

    with open(EDITED, "a", encoding="utf-8") as fh:
        fh.write("\n# an edit in progress\n")
    time.sleep(2 * app.FRESH_EVERY + 1)
    check("an uncommitted edit under board/ triggers no exit",
          server.poll() is None, "".join(said))

    sid = sessions.new("fresh", base=fixture)["id"]
    sessions.bind(sid, "courses/Demo", base=fixture)
    write(os.path.join(CTL, sid), "8")
    req = urllib.request.Request(
        "http://127.0.0.1:%d/s/%s/say" % (port, sid),
        data=json.dumps({"text": "a long one"}).encode(), method="POST",
        headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=30).read()
    check("a turn starts", until(lambda: calls(sid, "start"), 30))
    commit_tool(tooltop, "tutorboard: a committed change, mid-turn")
    time.sleep(app.FRESH_EVERY + 2)
    check("committing board code mid-turn: the server keeps running while "
          "the turn does", server.poll() is None and not calls(sid, "card"))
    code = None
    try:
        code = server.wait(60)
    except subprocess.TimeoutExpired:
        pass
    done = calls(sid, "card")
    check("the turn finishes, with its card, then the server exits 0",
          code == 0 and done and done[0]["rc"] == 0, (code, done, "".join(said)[-1500:]))
    check("saying why, after the turn ended",
          any("committed board code moved" in l for l in said)
          and len([n for n in os.listdir(os.path.join(fixture, "sessions", sid,
                                                      "cards"))
                   if n[:4].isdigit()]) == 1, "".join(said)[-1500:])
finally:
    if server is not None and server.poll() is None:
        os.killpg(server.pid, signal.SIGTERM)
        try:
            server.wait(20)
        except subprocess.TimeoutExpired:
            os.killpg(server.pid, signal.SIGKILL)


# ===========================================================================
# the rehearsal: a real LaunchAgent, under a test label (opt-in)
# ===========================================================================
LABEL = "tutor-board.rehearsal"
if os.environ.get("TUTORBOARD_REHEARSE_LAUNCHD") != "1" \
        or not shutil.which("launchctl"):
    print("ok   (skipped: the launchd rehearsal runs only with "
          "TUTORBOARD_REHEARSE_LAUNCHD=1)")
else:
    domain = "gui/%d" % os.getuid()
    rlog = os.path.join(box, "rehearsal.log")
    plist = os.path.join(box, LABEL + ".plist")
    p = subprocess.run(["bash", os.path.join(tool, "install.sh"), "--plist",
                        "--port", "8779", "--atlas", fixture],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       env=dict(os.environ, TUTORBOARD_LABEL=LABEL,
                                TUTORBOARD_LOG=rlog))
    job = plistlib.loads(p.stdout)
    job["EnvironmentVariables"].update({
        "XDG_CONFIG_HOME": os.environ["XDG_CONFIG_HOME"],
        "BOARD_STATE_DIR": os.environ["BOARD_STATE_DIR"],
        "TUTORBOARD_TRASH": os.environ["TUTORBOARD_TRASH"],
        "BOARD_NO_TAILNET": "1", "TUTOR_SLURM": "0"})
    with open(plist, "wb") as fh:
        plistlib.dump(job, fh)

    def booted(pid_after=None):
        """The pid of the newest `listening` line, once it is not
        `pid_after`."""
        try:
            text = open(rlog, encoding="utf-8").read()
        except OSError:
            return None
        pids = [int(l.split("; pid ", 1)[1].split(";")[0]) for l in
                text.splitlines() if "listening on http://" in l and "; pid " in l]
        if pids and pids[-1] != pid_after:
            return pids[-1]
        return None

    def command(pid):
        return subprocess.run(["ps", "-o", "command=", "-p", str(pid)],
                              stdout=subprocess.PIPE,
                              universal_newlines=True).stdout.strip()

    try:
        import socket
        probe = socket.socket()
        # A listener, not a connection still in TIME_WAIT, is what is busy.
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind(("127.0.0.1", 8779))
            free = True
        except OSError:
            free = False
        finally:
            probe.close()
        check("port 8779 is free for the rehearsal", free)
        boot = subprocess.run(["launchctl", "bootstrap", domain, plist],
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              universal_newlines=True)
        p1 = until(booted, 60)
        cmd1 = command(p1) if p1 else ""
        check("the rehearsal job boots on port 8779", boot.returncode == 0 and p1
              and ":8779/" in open(rlog).read(), boot.stdout)
        with urllib.request.urlopen("http://127.0.0.1:8779/health", timeout=30) as r:
            check("and answers", json.loads(r.read().decode()).get("ok") is True)
        with open(EDITED, "a", encoding="utf-8") as fh:
            fh.write("\n# a second change, shipped\n")
        commit_tool(tooltop, "tutorboard: a second committed change")
        p2 = until(lambda: booted(p1), 90, 1.0)
        cmd2 = command(p2) if p2 else ""
        printed = subprocess.run(["launchctl", "print", "%s/%s" % (domain, LABEL)],
                                 stdout=subprocess.PIPE,
                                 universal_newlines=True).stdout
        print("     (pid %s -> %s; %s)" % (p1, p2, cmd2))
        check("after a clean exit launchd starts it again, as a new process",
              p2 and p2 != p1 and "last exit code = 0" in printed
              and "committed board code moved" in open(rlog).read(),
              open(rlog).read()[-2000:] + printed[-1500:])
        check("with the same interpreter", cmd1 and cmd1 == cmd2, (cmd1, cmd2))
    finally:
        subprocess.run(["launchctl", "bootout", "%s/%s" % (domain, LABEL)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        gone = until(lambda: subprocess.run(
            ["launchctl", "print", "%s/%s" % (domain, LABEL)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 0,
            20, 0.5)
        check("then it is booted out", gone)

shutil.rmtree(box, ignore_errors=True)
print()
if fails:
    print("%d check(s) failed" % len(fails))
    sys.exit(1)
print("the server hears the cluster, a report wakes its session or is a notice, "
      "and committed code restarts the one LaunchAgent")
