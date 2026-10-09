#!/usr/bin/env python3
"""A session's mode: teach or do, and nothing else says who writes the code.

    python3 test/mode.py

Everything runs in a temp Atlas (`TUTORBOARD_COURSES`). Nothing here touches
the real `sessions/`.

  * The old axes are gone: no aim, kind or stance resolver anywhere in board/.
  * A session opens in teach. Its brief carries the TEACH paragraph and not the
    DO one, and no legacy key -- `stance: do`, `aim: build`, a make sitting, a
    `tutorboard.json` stance -- infers do.
  * POST /mode do changes session.json, leaves the cards untouched, archives
    nothing, wakes no turn, and appends one transcript turn and one inbox
    line. The next brief carries DO. A second tap writes nothing; a word that
    is not a mode is a 400.
  * `doing_now` is true in do mode and for a handover signal, and a do turn
    gets the doing timeout.
  * `board mode` prints and sets it; `board aim`, `board review`, `board walk`
    and `open --review/--walk/--make/--aim/--kind/--stance` are gone.
  * /session takes a lecture or a homework sitting only, and /handover is
    refused in do mode.
  * A chapter still opens as a labelled lecture, and a hold standing in the
    workspace is still on the brief.

test/asking.py keeps the handover, writeup and map-box checks, and
test/onthread.py the thread checks, that once sat beside the aim's.
"""

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD_DIR = os.path.dirname(HERE)
ATLAS = os.path.dirname(BOARD_DIR)
BOARD = os.path.join(BOARD_DIR, "bin", "board")
sys.path.insert(0, BOARD_DIR)

fails = []


def check(name, cond, detail=""):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name + (("\n       " + str(detail)) if detail else ""))


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def tree(root):
    out = {}
    for here, _, files in os.walk(root):
        for f in files:
            p = os.path.join(here, f)
            with open(p, "rb") as fh:
                out[os.path.relpath(p, root)] = fh.read()
    return out


base = os.path.realpath(tempfile.mkdtemp(prefix="tutor-mode-"))
trash = os.path.realpath(tempfile.mkdtemp(prefix="tutor-mode-trash-"))
os.environ["TUTORBOARD_COURSES"] = base
os.environ["TUTORBOARD_TRASH"] = trash
os.environ.pop("TUTORBOARD_SESSION", None)
os.environ.pop("TUTORBOARD_TURN", None)

from tutorboard import brief, sense, sessions                        # noqa: E402
from tutorboard import mode as session_mode                          # noqa: E402
from tutorboard.course import config                                 # noqa: E402
from tutorboard.course import repo as course_repo                    # noqa: E402
from tutorboard.lesson import archive, turns                         # noqa: E402
from tutorboard.runner import turn as runturn                        # noqa: E402
from tutorboard.server import handler, hub, spawn, tikz              # noqa: E402
from tutorboard.runner import service as runner_service  # noqa: E402


def board(args, session=None):
    env = dict(os.environ)
    env.pop("TUTORBOARD_SESSION", None)
    if session:
        env["TUTORBOARD_SESSION"] = session
    p = subprocess.run([sys.executable, BOARD] + list(args), cwd=base, env=env,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       universal_newlines=True, timeout=120)
    return p.returncode, p.stdout


def briefed(repo):
    return brief.briefing(repo, sense)


# ---------------------------------------------------------------------------
# the old axes are gone
# ---------------------------------------------------------------------------
# Spelled in pieces, so this file does not match its own pattern.
gone = ["AIM_" + "KIND", "KIND_" + "SENSE", "aim_" + "for", "kind_" + "for",
        "family_" + "aim", "stance_" + "for"]
p = subprocess.run(["git", "grep", "-n"] + sum([["-e", g] for g in gone], [])
                   + ["--", "board"], cwd=ATLAS, stdout=subprocess.PIPE,
                   universal_newlines=True)
check("no aim, kind or stance resolver is left in board/", p.stdout == "", p.stdout)
check("config has the two modes and nothing infers do",
      config.MODES == ("teach", "do")
      and config.mode_of({}) == "teach"
      and config.mode_of({"mode": "do"}) == "do"
      and config.mode_of({"mode": "DO "}) == "do"
      and config.mode_of({"mode": "sideways"}) == "teach"
      and config.mode_of({"stance": "do", "aim": "build", "kind": "build",
                          "session": "make"}) == "teach"
      and config.clean_mode("maybe") is None)
check("one TEACH paragraph and one DO paragraph",
      sense.mode_sense("teach") == sense.TEACH_SENSE
      and sense.mode_sense("do") == sense.DO_SENSE
      and "board mode do" in sense.TEACH_SENSE
      and all(w in sense.TEACH_SENSE
              for w in ("lesson", "homework set", "walkthrough", "drill", "review")))

replaced = []
woken = []
runner_service.wake = lambda r: woken.append(r) or True

httpd = None
try:
    # A project that once said `"stance": "do"`, as TRD-EHR and Paper-Writer did.
    proj = os.path.join(base, "projects", "Doer")
    write(os.path.join(proj, "tutorboard.json"),
          json.dumps({"name": "Doer", "stance": "do", "aim": "build"}))

    rec = sessions.new(base=base)
    where = sessions.path(rec["id"], base)
    check("a session opens in teach", rec["mode"] == "teach")
    repo = sessions.repo(rec["id"], base, create=True)
    said = briefed(repo)
    check("and its brief carries TEACH, not DO",
          sense.TEACH_SENSE in said and sense.DO_SENSE not in said
          and sense.DOING_SENSE not in said and "mode: teach" in said)

    # Legacy sitting keys in the state infer nothing.
    repo.set_state(stance="do", aim="build", kind="build", session="make")
    said = briefed(repo)
    check("legacy stance, aim, kind and a make sitting do not infer do",
          sense.TEACH_SENSE in said and sense.DO_SENSE not in said
          and config.mode_of(repo.state()) == "teach")
    repo.set_state(stance=None, aim=None, kind=None, session=None)

    # Bound to the project whose tutorboard.json says do: still teach.
    repo.set_state(subject="projects/Doer")
    bound = sessions.repo(rec["id"], base)
    check("a tutorboard.json stance infers nothing either",
          bound.root == proj and sense.DO_SENSE not in briefed(bound))

    # doing_now and the clock, through the resolver a turn uses.
    os.environ["TUTORBOARD_SESSION"] = where
    live = course_repo.resolve(create=False)
    cfg = {"headless_timeout": 900, "doing_timeout": 3600}
    check("doing_now is false in teach, and a teach turn gets the teaching clock",
          not runturn.doing_now(live.root)
          and runturn.turn_timeout(cfg, live.root) == 900)
    check("doing_now is true for the handover signal in teach",
          runturn.doing_now(live.root, "handover")
          and runturn.turn_timeout(cfg, live.root, signal="handover") == 3600)

    # ---- POST /mode, over real HTTP ----------------------------------------
    for n in (1, 2, 3):
        write(os.path.join(repo.cards, "000%d-lesson.md" % n),
              "---\nkind: lesson\n---\nCard %d.\n" % n)
    cards_before = tree(repo.cards)
    turns_before = len(turns.load_turns(repo))

    worker = tikz.TikzWorker(bound)
    worker.start()
    the_hub = hub.Hub(bound, worker)
    the_hub.payload = json.dumps(the_hub.build())
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), handler.Handler)
    httpd.daemon_threads = True
    httpd.repo = bound
    httpd.hub = the_hub
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    url = "http://127.0.0.1:%d" % port

    def post(path, body):
        req = urllib.request.Request(url + path, method="POST",
                                     data=json.dumps(body).encode("utf-8"),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.status, json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8")
            try:
                return exc.code, json.loads(raw)
            except ValueError:
                return exc.code, raw

    status, body = post("/mode", {"mode": "do"})
    on_disk = json.load(open(os.path.join(where, "session.json")))
    check("POST /mode do is accepted",
          status == 200 and body.get("mode") == "do" and body.get("changed") is True,
          body)
    check("and changes session.json", on_disk.get("mode") == "do", on_disk)
    check("and leaves every card untouched", tree(repo.cards) == cards_before)
    check("and archives nothing, replaces no tutor, wakes no turn",
          not archive.list_archive(bound) and not replaced and not woken)
    got = turns.load_turns(bound)
    check("one transcript turn",
          len(got) == turns_before + 1 and got[-1].get("signal") == "mode"
          and got[-1].get("text") == "Mode: do.")
    lines = [json.loads(x) for x in open(bound.messages_path, encoding="utf-8")]
    check("one inbox line, written wake:false so it wakes nothing, and unread "
          "so the next turn reads it",
          len(lines) == 1 and lines[0]["text"].startswith("[mode]")
          and lines[0].get("wake") is False and lines[0].get("read") is False)
    said = briefed(sessions.repo(rec["id"], base))
    check("the next brief carries DO and the doing order",
          sense.DO_SENSE in said and sense.DOING_SENSE in said
          and sense.TEACH_SENSE not in said and "mode: do" in said)
    check("doing_now is true in do, and a do turn gets the doing clock",
          runturn.doing_now(live.root)
          and runturn.turn_timeout(cfg, live.root) == 3600)
    check("the board's payload says the mode",
          the_hub.build()["state"].get("mode") == "do")

    status, body = post("/mode", {"mode": "do"})
    check("a second tap writes nothing",
          status == 200 and body.get("changed") is False
          and len(turns.load_turns(bound)) == turns_before + 1)
    status, body = post("/mode", {"mode": "build"})
    check("a word that is not a mode is refused",
          status == 400 and json.load(open(os.path.join(where, "session.json")))
          .get("mode") == "do")
    status, body = post("/handover", {"card": "0001"})
    check("a step cannot be handed over in do mode", status == 400, body)
    status, _ = post("/aim", {"aim": "build"})
    check("POST /aim is gone", status == 404)
    for kind in ("review", "walk", "make"):
        status, _ = post("/session", {"session": kind, "over": ["x"]})
        check("/session refuses a %s sitting" % kind, status == 400)

    status, body = post("/mode", {"mode": "teach"})
    check("POST /mode teach puts it back",
          status == 200 and body.get("changed") is True
          and config.mode_of(sessions.get(rec["id"], base)) == "teach")
    status, body = post("/handover", {"card": "0001"})
    check("and a step can be handed over again in teach",
          status == 200 and body.get("card") == "0001", body)

    # ---- the CLI -----------------------------------------------------------
    code, out = board(["mode"], session=where)
    check("board mode prints it", code == 0 and "mode: teach" in out, out)
    code, out = board(["mode", "do"], session=where)
    check("board mode do sets it",
          code == 0 and sessions.get(rec["id"], base)["mode"] == "do", out)
    code, out = board(["mode", "sideways"], session=where)
    check("board mode refuses a word that is not a mode",
          code == 2 and sessions.get(rec["id"], base)["mode"] == "do", out)
    code, out = board(["status"], session=where)
    check("board status says the mode", code == 0 and "mode:    do" in out, out)
    for gone_cmd in ("aim", "review", "walk", "open", "archive", "thread"):
        code, out = board([gone_cmd], session=where)
        check("board %s is gone" % gone_cmd, code != 0, out)

    # A tutor obeying "do it" runs the same command inside its turn.
    session_mode.set_mode(repo, "teach")
    env_turn = dict(os.environ, TUTORBOARD_TURN="1", TUTORBOARD_SESSION=where)
    p = subprocess.run([sys.executable, BOARD, "mode", "do"], cwd=base,
                       env=env_turn, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, universal_newlines=True,
                       timeout=120)
    got = turns.load_turns(sessions.repo(rec["id"], base))
    check("a turn's board mode do is recorded as the tutor's",
          p.returncode == 0 and got[-1].get("from") == "tutor"
          and got[-1].get("text") == "Mode: do.", p.stdout)

    # ---- a hold is still on the brief ----------------------------------------
    os.environ.pop("TUTORBOARD_SESSION", None)
    course = os.path.join(base, "courses", "Course")
    write(os.path.join(course, "tutorboard.json"), json.dumps({"name": "Course"}))
    write(os.path.join(course, "chapters.tsv"), "01\t1\t9\tgroups\tGroups\n")
    write(os.path.join(course, "live", "state.json"), json.dumps(
        {"course": "Course", "chapter": "Ch 01 — Groups", "session": "lecture"}))
    write(os.path.join(course, "relay", "holds", "groups.json"), json.dumps({
        "id": "groups", "label": "groups", "files": ["chapters"],
        "check": None, "held": 0}))
    crepo = course_repo.Repo(course, create=False)
    check("a hold standing in the workspace is on the brief, files named",
          "HELD AT THE CLUSTER: groups (`groups`)"
          in brief.sitting_sense(crepo, crepo.state())
          and "HELD AT THE CLUSTER" in briefed(crepo))
finally:
    os.environ.pop("TUTORBOARD_SESSION", None)
    if httpd is not None:
        httpd.shutdown()
    shutil.rmtree(base, ignore_errors=True)
    shutil.rmtree(trash, ignore_errors=True)

print()
if fails:
    print("%d failed" % len(fails))
    sys.exit(1)
print("a session is taught or done, and only the owner's word says which")
