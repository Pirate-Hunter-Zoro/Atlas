#!/usr/bin/env python3
"""The Mac's sync health: GET /sync.json, home's #health and the board's
#healthbar.

What the checks are about:

  * NOT SYNCED. With no pull.json, or one whose last step went through, there
    is nothing to say. A failed or skipped pull, merge or ls-remote is one
    "not synced: <git's words>" line, and the payload reads down.
  * ONE SOURCE. `sync.health` reads pull.json, which the sync thread writes.
    The session's payload carries it as `sync`, and GET /sync.json serves it.
  * BREW. brew.json's failures, and tools.json's, join /sync.json's lines, so
    home shows them; the session's payload never carries them.
  * NOTHING OF THE CLUSTER. GET /relay.json and POST /colibri are gone, and
    neither the payload nor /subject.json carries jobs or Colibri.

Synthetic repositories only.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
box = tempfile.mkdtemp(prefix="tutor-health-box-")
STATE = os.path.join(box, "state")
os.environ["BOARD_STATE_DIR"] = STATE
os.environ["XDG_CONFIG_HOME"] = os.path.join(box, "config")
os.environ["TUTORBOARD_TRASH"] = os.path.join(box, "trash")
os.environ["BOARD_NO_TAILNET"] = "1"
for name in ("TUTORBOARD_SESSION", "TUTORBOARD_TURN", "TUTORBOARD_PORT",
             "TUTORBOARD_SYNC", "TUTORBOARD_FRESH"):
    os.environ.pop(name, None)

from tutorboard import brief, sense, sessions, sync                   # noqa: E402
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


def git(cwd, *args):
    p = subprocess.run(["git"] + list(args), cwd=cwd, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, check=False)
    return p.stdout.decode("utf-8", "replace").strip()


class Worker(object):
    dirty = threading.Event()

    def submit(self, jobs):
        pass


PULL = os.path.join(STATE, sync.PULL_STATE)
base = tempfile.mkdtemp(prefix="tutor-health-")
httpd = None
try:
    mac = os.path.join(base, "mac")
    os.makedirs(mac)
    git(mac, "init", "-q", "-b", "main")
    git(mac, "config", "user.email", "t@example.com")
    git(mac, "config", "user.name", "t")
    ws = os.path.join(mac, "projects", "Proj")
    write(os.path.join(mac, ".gitignore"), "/sessions/\n")
    write(os.path.join(ws, "tutorboard.json"), json.dumps({"name": "Proj"}))
    git(mac, "add", "-A")
    git(mac, "commit", "-q", "-m", "start")
    os.environ["TUTORBOARD_COURSES"] = mac

    # --- not synced ---------------------------------------------------------
    got = sync.health(mac, fresh=True)
    check("with no pull.json there is nothing to say",
          got["synced"] is True and got["down"] is False and got["lines"] == []
          and got["pull"] is None, got)
    write(PULL, json.dumps({"ok": True, "step": "pull", "said": ""}))
    got = sync.health(mac, fresh=True)
    check("nor after a pull that went through",
          got["synced"] is True and got["lines"] == [], got)
    write(PULL, json.dumps({"ok": False, "step": "pull",
                            "said": "fatal: Not possible to fast-forward, aborting.",
                            "at": "2026-10-23 09:00:00"}))
    got = sync.health(mac, fresh=True)
    check("a failed pull is one not-synced line, in git's words, and reads down",
          got["synced"] is False and got["down"] is True
          and got["lines"] == ["not synced: fatal: Not possible to fast-forward, "
                               "aborting."], got)
    write(PULL, json.dumps({"ok": False, "step": "merge",
                            "said": "skipped: staged changes"}))
    check("a skipped merge says so the same way",
          sync.health(mac, fresh=True)["lines"]
          == ["not synced: skipped: staged changes"])
    check("and the answer is cached until a pass forgets it",
          sync.health(mac)["lines"] == ["not synced: skipped: staged changes"])

    sid = sessions.new("one", base=mac)["id"]
    sessions.bind(sid, "projects/Proj", base=mac)
    sync.forget()
    data = hub.Hub(sessions.repo(sid, mac), Worker()).build()
    check("the session's payload carries it as `sync`, and no `relay`",
          (data.get("sync") or {}).get("down") is True
          and "not synced" in data["sync"]["lines"][0] and "relay" not in data,
          data.get("sync"))
    said = brief.briefing(sessions.repo(sid, mac), sense)
    check("the brief carries no health or cluster section",
          "HEALTH:" not in said and "out on the cluster" not in said)

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
            try:
                return e.code, json.loads(e.read().decode() or "{}")
            except ValueError:
                return e.code, {}

    sync.forget()
    code, got = ask("GET", "/sync.json")
    check("GET /sync.json serves it",
          code == 200 and got["ok"] and got["synced"] is False
          and got["lines"] == ["not synced: skipped: staged changes"], got)

    # --- brew upkeep: /sync.json only -----------------------------------------
    write(os.path.join(STATE, "brew.json"), json.dumps({
        "mode": "own", "last_attempt": "2026-10-12T03:30:00",
        "last_success": "2026-10-11T03:30:00", "last_result": "partial",
        "failed": {"ffmpeg": "Error: a download failed"}, "held": {},
        "problems": []}))
    sync.forget()
    code, got = ask("GET", "/sync.json")
    check("a brew failure joins /sync.json's lines, after the not-synced one",
          code == 200 and got["lines"][0].startswith("not synced")
          and "brew: ffmpeg did not upgrade: Error: a download failed"
          in got["lines"], got.get("lines"))
    sync.forget()
    data = hub.Hub(sessions.repo(sid, mac), Worker()).build()
    check("and the session's payload stays without it",
          not any(l.startswith("brew:") for l in data["sync"]["lines"]),
          data["sync"])
    os.remove(os.path.join(STATE, "brew.json"))
    write(os.path.join(STATE, "tools.json"), json.dumps({
        "tools": {"widget": {"failed": "T_UPDATE exited 3"}},
        "pins": [{"subject": "projects/S", "tool": "node", "pinned": "20.0.0",
                  "latest": "22.1.0"}]}))
    sync.forget()
    code, got = ask("GET", "/sync.json")
    check("tools.json's failures and pins behind join them too, so home shows them",
          code == 200 and "tools: widget failed: T_UPDATE exited 3" in got["lines"]
          and "tools: pin behind: projects/S node 20.0.0 -> 22.1.0" in got["lines"],
          got.get("lines"))
    os.remove(os.path.join(STATE, "tools.json"))

    # --- nothing of the cluster ---------------------------------------------
    check("GET /relay.json is gone", ask("GET", "/relay.json")[0] == 404)
    check("and POST /colibri", ask("POST", "/colibri", {"brief": "x"})[0] == 404)
    code, sub = ask("GET", "/s/%s/subject.json" % sid)
    check("/subject.json carries no jobs or Colibri",
          code == 200 and "jobs" not in sub and "colibri" not in sub, sub)
finally:
    if httpd is not None:
        httpd.shutdown()
    shutil.rmtree(base, ignore_errors=True)
    shutil.rmtree(box, ignore_errors=True)

print()
if fails:
    print("%d check(s) failed" % len(fails))
    sys.exit(1)
print("the Mac says when it is not synced, and home adds the machine's brew lines")
