#!/usr/bin/env python3
"""THE FRONT DOOR SWITCHES PROVIDER, and the switch is one file on this machine.

    python3 test/provider.py

An evening ends when the provider says no more, and until this existed the
answer to that was a laptop, an account page and somebody editing a config file.
This is the route behind the tap: it writes `default_agent` into
`~/.config/tutor-board/config.json` and nothing else in that file.

`default_agent` is the MACHINE layer of `resolve_agent`'s precedence, and it is
the lowest one -- so writing it is not enough on its own. Every sitting opened
from the board names an assistant, and that name outranks the default for ever,
which meant this tap could not reach the one evening it is always tapped for:
the one where the provider it is running on has just run out. So the route
writes the file AND re-points every open sitting on this machine, and says
which ones it moved.

Two are left where they are, and each would be a worse answer than not
switching: a sitting on the `private` recipe, which is the fenced reader and
the only assistant allowed in the workspace holding `phi`; and a workspace with
no sitting open, where there is nothing to move.

Three refusals, and each one prevents a different silent failure:

  - an unknown name leaves the machine with no resolvable tutor at all;
  - an unkeyed or uninstalled one is a daemon that listens and then fails every
    turn into a log nobody opens;
  - and a `private` recipe is NEVER the machine default, because it is the
    fenced reader and a default is a decision about every workspace, including
    the ones whose `live/` is pushed to a public remote.
"""

import json
import os
import socket
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

os.environ.setdefault("BOARD_STATE_DIR", tempfile.mkdtemp(prefix="provider-state-"))
# A TREE OF OUR OWN, BEFORE ANYTHING IMPORTS. The route driven below re-points
# every OPEN SITTING on this machine at the chosen provider, and the real tree
# is where somebody's evening is. Pointed at an empty directory here and filled
# in by the cases that want workspaces in it.
os.environ["TUTORBOARD_COURSES"] = tempfile.mkdtemp(prefix="provider-tree-")
os.environ.setdefault("BOARD_NODE_NAME", "test-node")
os.environ.setdefault("BOARD_NO_TAILNET", "1")

from tutorboard import assistants, atlas, paths               # noqa: E402
from tutorboard.course import repo as course_repo            # noqa: E402
from tutorboard.server import handler, hub, tikz             # noqa: E402

fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


# A config file of our own. Writing the real one would change which assistant
# this machine teaches with, from a test.
box = tempfile.mkdtemp(prefix="provider-cfg-")
paths.CONFIG = os.path.join(box, "config.json")
with open(paths.CONFIG, "w", encoding="utf-8") as fh:
    json.dump({"default_agent": "claude", "quota_tokens": 28000000}, fh)

KEYS = "/nowhere/keys.env"
TABLE = {"default": "claude", "vision_agent": "deepseek", "agents": [
    {"name": "claude", "cmd": "claude", "missing": None, "unkeyed": None,
     "keys": KEYS, "private": None, "exclusive": None, "headless": True},
    {"name": "deepseek", "cmd": "claude", "missing": None, "unkeyed": None,
     "keys": KEYS, "private": None, "exclusive": None, "headless": True},
    {"name": "nokey", "cmd": "claude", "missing": None,
     "unkeyed": "A_KEY", "keys": KEYS, "private": None,
     "exclusive": None, "headless": True},
    {"name": "gone", "cmd": "nope", "missing": "nope", "unkeyed": None,
     "keys": KEYS, "private": None, "exclusive": None, "headless": True},
    {"name": "colibri", "cmd": "coli-code", "missing": None, "unkeyed": None,
     "keys": KEYS, "private": "it is the only assistant allowed to read `phi`",
     "exclusive": "one KV slot", "headless": True},
]}
assistants.listing = lambda: TABLE

tmp = tempfile.mkdtemp(prefix="provider-ws-")
with open(os.path.join(tmp, "tutorboard.json"), "w", encoding="utf-8") as fh:
    json.dump({"name": "Test Workspace"}, fh)
repo = course_repo.Repo(tmp)
worker = tikz.TikzWorker(repo)
worker.start()
board = hub.Hub(repo, worker)
board.payload = json.dumps(board.build())

sock = socket.socket()
sock.bind(("127.0.0.1", 0))
port = sock.getsockname()[1]
sock.close()
httpd = ThreadingHTTPServer(("127.0.0.1", port), handler.Handler)
httpd.daemon_threads = True
httpd.repo = repo
httpd.hub = board
threading.Thread(target=httpd.serve_forever, daemon=True).start()
BASE = "http://127.0.0.1:%d" % port


def post(path, body):
    req = urllib.request.Request(BASE + path, method="POST",
                                 data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def cfg():
    with open(paths.CONFIG, encoding="utf-8") as fh:
        return json.load(fh)


try:
    status, got = post("/default-agent", {"agent": "deepseek"})
    check("the tap writes the machine default", status == 200 and got.get("ok"))
    check("and the file says so", cfg().get("default_agent") == "deepseek")
    check("AND NOTHING ELSE IN THAT FILE MOVED. It is read by every `tutor` on "
          "this machine; a route that rewrote it from defaults would silently "
          "undo whatever somebody had set by hand",
          cfg().get("quota_tokens") == 28000000 and len(cfg()) == 2)

    for name, why in (("nonesuch", "an unknown name"),
                      ("gone", "one this machine has not got"),
                      ("nokey", "one whose key is not here"),
                      ("colibri", "the fenced reader, which is never a "
                                  "machine default")):
        status, got = post("/default-agent", {"agent": name})
        check("%s is refused, with the reason on the glass" % why,
              status == 400 and not got.get("ok") and bool(got.get("detail")))
    check("and none of the refusals changed the file",
          cfg().get("default_agent") == "deepseek")

    status, got = post("/default-agent", {})
    check("a request naming nobody is a refusal rather than a crash",
          status == 400)

    # ---- AND THE SITTINGS ALREADY OPEN --------------------------------------
    #
    # `default_agent` is the LOWEST layer of `resolve_agent`'s precedence, and
    # every sitting opened from the board names an assistant -- so this tap
    # could not reach the one evening it is always tapped for. Reported from
    # the iPad: "when I tried to switch to codex on the homescreen, it wouldn't
    # switch and I was stuck on claude, which I had used up my limit on."
    tree = os.environ["TUTORBOARD_COURSES"]
    with open(os.path.join(tree, "atlas.json"), "w", encoding="utf-8") as fh:
        json.dump({"families": [{"id": "courses", "name": "Courses"}]}, fh)

    def workspace(name, state):
        root = os.path.join(tree, "courses", name)
        os.makedirs(os.path.join(root, "live"), exist_ok=True)
        with open(os.path.join(root, "tutorboard.json"), "w",
                  encoding="utf-8") as fh:
            json.dump({"name": name}, fh)
        with open(os.path.join(root, "live", "state.json"), "w",
                  encoding="utf-8") as fh:
            json.dump(state, fh)
        return root

    stuck = workspace("Stuck", {"session": "lecture", "agent": "claude"})
    fenced = workspace("Fenced", {"session": "lecture", "agent": "colibri"})
    unopened = workspace("Unopened", {"agent": "claude"})
    free = workspace("Free", {"session": "lecture"})
    atlas.forget()

    def agent_of(root):
        with open(os.path.join(root, "live", "state.json"), encoding="utf-8") as fh:
            return (json.load(fh) or {}).get("agent")

    status, got = post("/default-agent", {"agent": "deepseek"})
    check("the tap moves a sitting that had named an assistant, which is the "
          "whole of what an evening out of allowance needs",
          status == 200 and agent_of(stuck) == "deepseek")
    check("and says which ones it moved, because the sentence that named only "
          "the machine layer is what read as a tap doing nothing",
          got.get("moved") == ["Stuck"])
    check("THE FENCED READER IS LEFT WHERE IT IS. `private` is what says an "
          "assistant may open the workspace holding `phi`, and moving that "
          "sitting to a hosted provider from a tap about an allowance puts "
          "identifiable audio in front of a remote",
          agent_of(fenced) == "colibri")
    check("a workspace with no sitting open is not pinned by this: there is "
          "nothing to move, and writing one in would pin an evening nobody "
          "has started", agent_of(unopened) == "claude")
    check("and a sitting that never named one is left alone too -- the "
          "machine default already reaches it",
          agent_of(free) is None)
    check("the file still says the same thing it would have",
          cfg().get("default_agent") == "deepseek")

    # A second tap on the same provider moves nothing: it is already there, and
    # a report naming a workspace that did not change is a report nobody trusts.
    status, got = post("/default-agent", {"agent": "deepseek"})
    check("tapping the provider a sitting is already on moves nothing",
          status == 200 and got.get("moved") == [])

    src = open(os.path.join(ROOT, "tutorboard", "server", "routes",
                            "machines.py"), encoding="utf-8").read()
    check("the file is written atomically, the way a limit record is -- every "
          "`tutor` invocation reads it and a half-written one takes the tool out",
          "os.replace(tmp, paths.CONFIG)" in src)
    check("and the 900-second cache is dropped, or the tap appears to do "
          "nothing for a quarter of an hour", "assistants.forget()" in src)

    # ONE COPY OF THE CHOOSER'S RULES. Two go out of step the first time a
    # recipe grows a flag, and a flag on a recipe is how a provider is added.
    who = open(os.path.join(ROOT, "web", "who.js"), encoding="utf-8").read()
    for page in ("board.js", "home.js"):
        js = open(os.path.join(ROOT, "web", page), encoding="utf-8").read()
        check("%s draws the chooser through the shared rules" % page,
              "WhoChoice" in js)
    for page in ("board.html", "home.html"):
        markup = open(os.path.join(ROOT, "web", page), encoding="utf-8").read()
        check("and %s loads them" % page, "/static/who.js" in markup)
    check("an unkeyed recipe is drawn dimmed with the key and the file in its "
          "title, because that sentence is the whole of a provider's setup",
          "a.unkeyed" in who and "keys" in who)
finally:
    httpd.shutdown()
    worker.stop() if hasattr(worker, "stop") else None

print("%d FAILURES" % len(fails) if fails
      else "the provider is a tap, and the machine's own file is where it lands")
sys.exit(1 if fails else 0)
