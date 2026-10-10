#!/usr/bin/env python3
"""The cluster's health on the Mac, and Colibri from relay/status.json only.

What the checks are about:

  * RELAY DOWN. A request whose commit origin has, with no report 15 minutes
    later, makes the payload read down; one filed a minute ago, one with a
    report, and one never pushed do not.
  * COLIBRI ON THE MAC reads only relay/status.json (D27): loading there is
    loading in /relay.json and /subject.json, never off, and no squeue is
    asked.
  * THE PANEL. POST /colibri files a `colibri` request in libr-local-llm,
    committed and pushed, and answers with a cold-start estimate from the
    load the relay timed. No brief is a 400. The filed task then shows
    queued, working and done as the relay's reports and status.json say.
  * THE BRIEF names a relay that looks down.

Synthetic repositories only: a bare origin and a "Mac" clone.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
box = tempfile.mkdtemp(prefix="tutor-health-box-")
os.environ["TUTOR_SLURM"] = "0"
os.environ["BOARD_STATE_DIR"] = os.path.join(box, "state")
os.environ["XDG_CONFIG_HOME"] = os.path.join(box, "config")
os.environ["TUTORBOARD_TRASH"] = os.path.join(box, "trash")
os.environ["BOARD_NO_TAILNET"] = "1"
for name in ("TUTORBOARD_SESSION", "TUTORBOARD_TURN", "TUTORBOARD_PORT",
             "TUTORBOARD_CLUSTER", "TUTORBOARD_FRESH", "COLI_QUEUE_ROOT"):
    os.environ.pop(name, None)

from tutorboard import brief, colibri, relay, sessions               # noqa: E402
from tutorboard.server import app, hub                                # noqa: E402

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


def git(cwd, *args, **env):
    p = subprocess.run(["git"] + list(args), cwd=cwd, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, check=False,
                       env=dict(os.environ, **env))
    return p.stdout.decode("utf-8", "replace").strip()


class Worker(object):
    dirty = threading.Event()

    def submit(self, jobs):
        pass


base = tempfile.mkdtemp(prefix="tutor-health-")
httpd = None
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
    llm = os.path.join(mac, "projects", "libr-local-llm")
    write(os.path.join(mac, ".gitignore"), "/sessions/\n**/relay/state/\n")
    write(os.path.join(ws, "tutorboard.json"), json.dumps({"name": "Proj"}))
    write(os.path.join(llm, "tutorboard.json"), json.dumps(
        {"name": "libr-local-llm", "phi": True, "relay": {"colibri": True}}))
    git(mac, "add", "-A")
    git(mac, "commit", "-q", "-m", "start")
    git(mac, "remote", "add", "origin", origin)
    git(mac, "push", "-q", "-u", "origin", "main")
    os.environ["TUTORBOARD_COURSES"] = mac

    def request(rid, ago, push=True, report=None):
        """A request committed `ago` seconds back, pushed or not."""
        path = os.path.join(ws, "relay", "requests", rid + ".json")
        write(path, json.dumps({"id": rid, "kind": "recipe",
                                "recipe": "slurm/x.sbatch"}))
        when = "@%d +0000" % int(time.time() - ago)
        git(mac, "add", "-A")
        git(mac, "commit", "-q", "-m", "relay request " + rid,
            GIT_COMMITTER_DATE=when, GIT_AUTHOR_DATE=when)
        if report:
            write(os.path.join(ws, "relay", "reports", rid + ".json"),
                  json.dumps(dict(report, id=rid)))
            git(mac, "add", "-A")
            git(mac, "commit", "-q", "-m", "relay report " + rid)
        if push:
            git(mac, "push", "-q")

    # --- relay down ---------------------------------------------------------
    request("2026-10-09-fresh", 60)
    request("2026-10-09-heard", 3600, report={"state": "submitted"})
    got = relay.health(mac, fresh=True)
    check("a request filed a minute ago, and one with a report, are not down",
          got["down"] is False and got["lines"] == [], got)
    request("2026-10-09-stale", 20 * 60)
    got = relay.health(mac, fresh=True)
    check("a pushed request with no report 15 minutes after its commit reads "
          "down", got["down"] is True
          and [r["id"] for r in got["stale"]] == ["2026-10-09-stale"]
          and got["lines"][0].startswith("relay looks down: projects/Proj "
                                         "2026-10-09-stale"), got)
    sid = sessions.new("one", base=mac)["id"]
    sessions.bind(sid, "projects/Proj", base=mac)
    relay.forget()
    data = hub.Hub(sessions.repo(sid, mac), Worker()).build()
    check("and the session's payload reads down",
          (data.get("relay") or {}).get("down") is True
          and "relay looks down" in data["relay"]["lines"][0], data.get("relay"))
    said = brief.relay_sense(ws)
    check("the brief says so too", "HEALTH: relay looks down" in said, said)

    # A stale request the Mac never pushed is not the relay's to have seen.
    git(mac, "rm", "-q", os.path.join(ws, "relay", "requests",
                                      "2026-10-09-stale.json"))
    git(mac, "commit", "-q", "-m", "withdrawn")
    git(mac, "push", "-q")
    request("2026-10-09-unpushed", 30 * 60, push=False)
    got = relay.health(mac, fresh=True)
    check("a request committed and not pushed does not read down",
          got["down"] is False, got)
    git(mac, "push", "-q")

    # --- Colibri from status.json only ----------------------------------------
    asked = []
    colibri._run = lambda args, timeout=10: asked.append(args) or ""
    write(os.path.join(mac, "relay", "status.json"), json.dumps({
        "skipped": "", "last_error": "", "push_pending": False,
        "outstanding": {}, "at": 1,
        "colibri": {"state": "loading", "ends": int(time.time()) + 7200,
                    "queue": 1, "task": "coli-20261009-120000-abcd",
                    "load_s": 4080, "reason": ""}}))
    git(mac, "add", "-A")
    git(mac, "commit", "-q", "-m", "relay: status")
    git(mac, "push", "-q")
    relay.forget()

    httpd = app.make_server(mac, 0, start=False)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    url = "http://127.0.0.1:%d" % httpd.server_port

    def ask(method, path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url + path, data=data, method=method,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status, json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode() or "{}")

    code, got = ask("GET", "/relay.json")
    check("/relay.json carries Colibri loading from status.json",
          code == 200 and got["colibri"]["state"] == "loading"
          and got["colibri"]["queue"] == 1 and "68 min" in got["colibri"]["detail"]
          and got["colibri_subject"] == "projects/libr-local-llm", got)
    code, sub = ask("GET", "/s/%s/subject.json" % sid)
    check("and /subject.json the same, and \"off\" never shows while status "
          "says loading", code == 200 and sub["colibri"]["state"] == "loading"
          and "off" != sub["colibri"]["state"], sub.get("colibri"))
    check("no squeue was asked on the Mac", asked == [], asked)

    # --- the panel: POST /colibri ---------------------------------------------
    code, got = ask("POST", "/colibri", {})
    check("no brief is a 400", code == 400 and not got["ok"])
    write(os.path.join(mac, "relay", "status.json"), json.dumps({
        "skipped": "", "last_error": "", "push_pending": False,
        "outstanding": {}, "at": 2,
        "colibri": {"state": "off", "ends": None, "queue": 0, "task": None,
                    "load_s": 4080, "reason": ""}}))
    git(mac, "add", "-A")
    git(mac, "commit", "-q", "-m", "relay: status")
    git(mac, "push", "-q")
    code, got = ask("POST", "/colibri", {"brief": "count the rows per site",
                                         "label": "rows"})
    filed = [n for n in os.listdir(os.path.join(llm, "relay", "requests"))]
    check("a task is filed as a colibri request in libr-local-llm, committed "
          "and pushed", code == 200 and got["ok"] and len(filed) == 1
          and json.load(open(os.path.join(llm, "relay", "requests",
                                          filed[0])))["kind"] == "colibri"
          and git(mac, "rev-parse", "HEAD") == git(origin, "rev-parse", "main"),
          got)
    check("and the answer carries the cold-start estimate the relay timed",
          "cold start" in got.get("estimate", "")
          and "68 min" in got["estimate"], got)
    code, got = ask("GET", "/relay.json")
    check("and the panel lists it, filed and waiting for the relay",
          [t["state"] for t in got["colibri_tasks"]] == ["filed"]
          and got["colibri_tasks"][0]["label"] == "rows", got)

    # --- the filed task through the relay: queued, working, done ---------------
    # The cluster's side, by its own functions: `colibri.relay_report` turns
    # the task record into the report the relay commits, and status.json's
    # Colibri block names the task a generation is running. The Mac hears
    # both by a pull and the panel words each as queued, working and done.
    rid = filed[0][:-len(".json")]
    tid = "coli-20261009-130000-beef"
    cluster = os.path.join(base, "cluster")
    git(base, "clone", "-q", origin, cluster)
    git(cluster, "config", "user.email", "t@example.com")
    git(cluster, "config", "user.name", "t")
    cllm = os.path.join(cluster, "projects", "libr-local-llm")

    def relay_says(queue, colibri_block, n, **rec):
        """One relay pass on the cluster: the task's report and status.json,
        committed and pushed; then the Mac pulls."""
        task = dict({"id": tid, "request": rid, "queue": queue,
                     "attempts": 1 if queue != "queued" else 0,
                     "at": time.time()}, **rec)
        relay.write_report(cllm, rid, colibri.relay_report(task))
        write(os.path.join(cluster, "relay", "status.json"), json.dumps({
            "skipped": "", "last_error": "", "push_pending": False,
            "outstanding": {}, "at": 10 + n,
            "colibri": relay._colibri_status(colibri_block)}))
        git(cluster, "add", "-A")
        git(cluster, "commit", "-q", "-m", "relay: pass %d" % n)
        git(cluster, "push", "-q")
        git(mac, "pull", "-q", "--ff-only")
        relay.forget()
        code, got = ask("GET", "/relay.json")
        return got

    def mine(got):
        return [t for t in got["colibri_tasks"] if t["id"] == rid]

    got = relay_says("queued", {"state": "queued", "ends": None, "queue": 1,
                                "task": None, "load_s": 4080,
                                "reason": "Priority"}, 1)
    check("a filed task the relay queued shows queued in the panel, with "
          "status.json's queue", [t["phase"] for t in mine(got)] == ["queued"]
          and got["colibri"]["queue"] == 1
          and "queued (Priority)" in got["colibri"]["detail"], got)
    got = relay_says("running", {"state": "warm",
                                 "ends": int(time.time()) + 3600, "queue": 0,
                                 "task": tid, "load_s": 4080, "reason": ""}, 2)
    check("once a generation claims it, working, with status.json naming it",
          [t["phase"] for t in mine(got)] == ["working"]
          and got["colibri"]["task"] == tid
          and got["colibri"]["state"] == "warm", got)
    got = relay_says("done", {"state": "warm",
                              "ends": int(time.time()) + 3000, "queue": 0,
                              "task": None, "load_s": 4080, "reason": ""}, 3,
                     checked=time.time(), changed=0,
                     relay=["rows per site: 12"], ended_at=time.time())
    check("and done once its report says completed, with its RELAY lines",
          [t["phase"] for t in mine(got)] == ["done"]
          and mine(got)[0]["relay"] == ["rows per site: 12"]
          and got["colibri"]["task"] is None, got)
finally:
    if httpd is not None:
        httpd.shutdown()
    shutil.rmtree(base, ignore_errors=True)
    shutil.rmtree(box, ignore_errors=True)

print()
if fails:
    print("%d check(s) failed" % len(fails))
    sys.exit(1)
print("the Mac says when the relay looks down, and reads Colibri from status.json")
