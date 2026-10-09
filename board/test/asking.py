#!/usr/bin/env python3
"""What a session takes without changing its mode.

  * A STEP HANDED OVER (`POST /handover`) is a doing turn inside a teach
    session: the session is unchanged, the turn is told it is doing, and it
    gets the doing clock. Refused in do mode.
  * A DECK OR A PAPER (`POST /artifact`) is an action, not a mode: no card, no
    transcript turn, the mode untouched. Asked for from a subject's row it
    lands in a session on that subject (`test/making.py`).
  * NO SITTING IS ABOUT A BOX: the map is gone, and a MISSION replaces the
    sitting rather than wearing it.

The routes are driven over real HTTP: what is guarded is the whole round trip
and the two things that must NOT happen in it -- the lesson filed away, or the
tutor replaced.
"""

import json
import os
import re
import socket
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tutorboard import sense, sessions, writeups
from tutorboard.course import library
from tutorboard.course import repo as course_repo
from tutorboard.lesson import archive, turns
from tutorboard.runner import turn as runturn
from tutorboard.server import handler, hub, spawn, tikz
from tutorboard.runner import service as runner_service  # noqa: E402

fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


fake = tempfile.mkdtemp(prefix="tutor-asking-tree-")


def workspace(family, name, cfg=None):
    where = os.path.join(fake, family, name)
    os.makedirs(where, exist_ok=True)
    with open(os.path.join(where, "tutorboard.json"), "w", encoding="utf-8") as fh:
        json.dump(dict({"name": name}, **(cfg or {})), fh)
    return where


os.environ["TUTORBOARD_COURSES"] = fake

course = workspace("courses", "Probability")


def sitting(where, **kw):
    os.makedirs(os.path.join(where, "live"), exist_ok=True)
    with open(os.path.join(where, "live", "state.json"), "w", encoding="utf-8") as fh:
        json.dump(kw, fh)


# A STEP HANDED OVER IS A DOING TURN INSIDE A TEACH SESSION, and the session is
# left in teach on purpose. Only the signal the turn was woken with can say so,
# and it has to reach the clock as well as the prompt.
sitting(course, session="lecture")
check("a teach session's turn is a teaching turn",
      not runturn.doing_now(course))
check("but the step it hands over is a doing turn",
      runturn.doing_now(course, "handover"))
CLOCK = {"headless_timeout": 900, "doing_timeout": 3600}
check("so the handed-over step gets a doing turn's clock",
      runturn.turn_timeout(CLOCK, course) == 900
      and runturn.turn_timeout(CLOCK, course, None, "handover") == 3600)
check("and every other signal leaves the clock where it was",
      runturn.turn_timeout(CLOCK, course, None, "help") == 900)

# ---------------------------------------------------------------------------
# A MISSION REPLACES THE SITTING; NO SITTING IS ABOUT A BOX
# ---------------------------------------------------------------------------
# The map and its boxes are gone (T50): no sitting is asked which part of the
# repository it is about, and none is told a boundary.
made = os.path.join(fake, "projects", "Parts")
os.makedirs(os.path.join(made, "live"), exist_ok=True)
with open(os.path.join(made, "tutorboard.json"), "w", encoding="utf-8") as fh:
    json.dump({"name": "Parts"}, fh)
PAD = "\n".join("# %d" % i for i in range(60)) + "\n"
for where, text in (
        (("typist", "run.py"), '"""Turns the waveform into words."""\n'),
        (("grader", "score.py"), '"""Scores a transcript against the reference."""\n'),
        (("grid", "sweep.py"), '"""Runs the parameter sweep."""\n')):
    os.makedirs(os.path.join(made, where[0]), exist_ok=True)
    with open(os.path.join(made, *where), "w", encoding="utf-8") as fh:
        fh.write(text + PAD)

sitting(made, session="lecture")
said = sense.session_sense(course_repo.Repo(made))
check("a sitting in a project made of parts is told nothing about boxes",
      "PART OF THE MAP" not in said and "COMPONENT BOUNDARY" not in said
      and "#/w/" not in said)
sitting(made, session="lecture", node="typist", chapter="typist")
check("and a legacy state naming a box changes nothing",
      "COMPONENT BOUNDARY" not in sense.session_sense(course_repo.Repo(made)))
sitting(made, session="lecture")

# A MISSION REPLACES THE SITTING RATHER THAN WEARING IT. It has a scope, the
# task, and a question in its first card is how it spends nine hours saying
# nothing.
_mission = {"id": "t0056", "task": "repair the diarization", "agent": "colibri",
            "at": time.time()}
_sent = sense.session_sense(course_repo.Repo(made), doing=True,
                            mission=_mission)
check("a MISSION is told what it is, with the task named as the scope",
      "THIS TURN IS A MISSION" in _sent
      and "the task is the last thing in the inbox" in _sent)
check("and it is still a doing turn, so nothing about the order of a change "
      "is lost by replacing the sitting",
      "THIS IS A DOING TURN" in _sent and "FIX THE RULE" in _sent)
# AND IT COSTS LESS THAN WHAT IT REPLACES. This block rides in a preamble the
# local model prefills at a few tokens a second.
_was = sense.session_sense(course_repo.Repo(made), doing=True)
check("and it is SHORTER than the sitting it replaces (%d words against %d), "
      "because a preamble is prefilled at a few tokens a second"
      % (len(_sent.split()), len(_was.split())),
      len(_sent.split()) < len(_was.split()))

# ---------------------------------------------------------------------------
# the route, over real HTTP
# ---------------------------------------------------------------------------
tmp = tempfile.mkdtemp(prefix="tutor-asking-")
with open(os.path.join(tmp, "tutorboard.json"), "w", encoding="utf-8") as fh:
    json.dump({"name": "Test Course"}, fh)
repo = course_repo.Repo(tmp)

# The two things that must not happen. What is checked is that neither is ASKED
# for -- a test does not start a daemon, and it must not archive a lesson either.
replaced = []
woken = []
runner_service.wake = lambda r: woken.append(r) or True

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


try:
    # Three hours into a teach session, with cards on the board.
    for n, title in ((1, "lesson"), (2, "lesson"), (3, "lesson")):
        with open(os.path.join(repo.cards, "000%d-%s.md" % (n, title)), "w",
                  encoding="utf-8") as fh:
            fh.write("---\nkind: lesson\n---\nCard %d.\n" % n)
    with open(repo.state_path, "w", encoding="utf-8") as fh:
        json.dump({"course": "Test Course", "session": "lecture",
                   "chapter": "The serve harness", "mode": "teach"}, fh)

    # ----------------------------------------------------------------- one step
    # THE WAY OUT OF ONE STEP OF COACHING, WITHOUT LEAVING IT: the session
    # must still be in teach afterwards.
    turns_before = len(turns.load_turns(repo))
    woke_before = len(woken)

    status, body = post("/handover", {"card": "0009"})
    check("a card that is not on the board is a miss, not a path",
          status == 404 and not body.get("ok"))
    status, body = post("/handover", {"card": "../../etc/passwd"})
    check("and neither is anything shaped like a path", status == 404)
    check("nothing was said to the tutor about either",
          len(turns.load_turns(repo)) == turns_before)

    status, body = post("/handover", {"card": "0003"})
    check("the board takes the step",
          status == 200 and body.get("ok") is True and body.get("card") == "0003")
    check("THE SESSION IS STILL IN TEACH MODE",
          repo.state().get("mode") == "teach")
    check("the lesson is not filed away", not archive.list_archive(repo))
    check("the cards are all still on the board",
          len([n for n in os.listdir(repo.cards) if n.endswith(".md")]) == 3)
    check("the tutor is not replaced", not replaced)
    check("and nothing else about the sitting moved",
          repo.state().get("chapter") == "The serve harness"
          and repo.state().get("session") == "lecture")

    sent = turns.load_turns(repo)[-1]
    check("their tap is in the transcript as a turn of theirs",
          sent.get("from") == "student" and sent.get("signal") == "handover")
    check("and it names the card it handed over", sent.get("card") == "0003")
    # `answers` means "the student answered that card", which is what gives a
    # card a writing surface of its own. A step handed over is not an answer.
    check("without claiming to be an answer to it", not sent.get("answers"))

    with open(repo.messages_path, "r", encoding="utf-8") as fh:
        lines = [json.loads(l) for l in fh if l.strip()]
    line = lines[-1].get("text", "")
    check("the line says what happened", line.startswith("[handover]"))
    check("it says the step is theirs to write and no more",
          "CARD 0003" in line and "ONLY ONE YOU WRITE" in line)
    check("it says the sitting has not changed",
          "carry on coaching" in line and "not a new tutor" in line)
    check("it refuses the card that explains how the step was done",
          "NOT A COACH CARD ABOUT THE STEP YOU JUST DID" in line)
    check("and asks for the next step under the report", "THE NEXT STEP" in line)
    # The session says teach, so nothing about the STATE would produce this.
    check("THE TURN IS TOLD IT IS A DOING TURN, which the sitting does not say",
          "THIS IS A DOING TURN" in line
          and "DOING TURN" not in sense.session_sense(repo))
    check("it still says what this session is",
          sense.TEACH_SENSE in line)
    check("it arrives unread, or nothing wakes on it",
          lines[-1].get("read") is False)
    check("a turn is woken on it", len(woken) == woke_before + 1)

    # Where the tutor is already writing the code there is nothing to hand over,
    # and waking a turn to be told so is a model call somebody pays for.
    post("/mode", {"mode": "do"})
    status, body = post("/handover", {"card": "0003"})
    check("a session that already writes the code has nothing to hand over",
          status == 400 and "already writing" in (body.get("error") or ""))
    post("/mode", {"mode": "teach"})

    # ------------------------------------------------------- and a document
    # A PAPER OR A DECK, ASKED FOR FROM ANY SITTING, WITHOUT CHANGING IT.
    #
    # **The want, and it was asked as a question:** *"at any point can I have a
    # presentation or paper written up going through the things we talked about
    # in that tutoring session? Can I do that in ANY tutoring session?"*
    #
    # A document is a PRODUCT rather than a mode: the mode must not move, and
    # the lesson must not be filed away.
    before_state = dict(repo.state())
    turns_before = len(turns.load_turns(repo))

    status, body = post("/artifact", {"make": "essay"})
    check("a product that is not one of the two is refused by name",
          status == 400 and "deck or paper" in (body.get("error") or ""))
    status, body = post("/artifact", {})
    check("and so is a request that does not say which",
          status == 400 and not body.get("ok"))
    check("neither of those asked for anything",
          len(turns.load_turns(repo)) == turns_before
          and not writeups.waiting(repo))

    woke_before = len(woken)
    status, body = post("/artifact", {"make": "deck"})
    check("the board takes the ask",
          status == 200 and body.get("ok") is True
          and body.get("make") == "deck" and body.get("id"))
    asked = body
    check("THE SESSION'S STATE HAS NOT MOVED", repo.state() == before_state)
    check("the lesson is not filed away", not archive.list_archive(repo))
    check("the cards are all still on the board",
          len([n for n in os.listdir(repo.cards) if n.endswith(".md")]) == 3)
    check("the tutor is not replaced", not replaced)
    # `/mode` and `/handover` both put the tap in the transcript, because a card
    # is coming back. Here no card is coming: the turn is told to write none, and
    # a student turn with nothing answering it is what leaves the board waiting
    # for a card that never arrives.
    check("NOTHING GOES IN THE TRANSCRIPT, because no card is coming",
          len(turns.load_turns(repo)) == turns_before)

    with open(repo.messages_path, "r", encoding="utf-8") as fh:
        lines = [json.loads(l) for l in fh if l.strip()]
    line = lines[-1].get("text", "")
    check("the line says what happened", line.startswith("[writeup]"))
    check("it says which product", "a DECK of slides" in line)
    check("it says the turn writes no card and leaves the sitting alone",
          "Write no card" in line and "its mode has not changed" in line)
    check("it carries the method for a document rather than restating it",
          sense.MAKE_SENSE in line)
    check("and the scope with nobody naming one is the session",
          "THE CONCEPTS THIS SITTING COVERED" in line)
    check("it arrives unread, or nothing wakes on it",
          lines[-1].get("read") is False)
    check("a turn is woken on it", len(woken) == woke_before + 1)

    # WHAT THE BOARD SAYS WHILE IT IS BEING WRITTEN. The turn writes no card, so
    # it is invisible on the board by construction -- which leaves "I asked for
    # a deck and nothing happened" with nowhere to be answered.
    writeups.forget()
    said = board.build().get("writeups") or []
    check("the board says a document is being written",
          len(said) == 1 and said[0]["state"] == "writing"
          and said[0]["makes"] == "slides")

    # AND WHEN IT IS THERE, which is derived from the artifact's doc.json and
    # mtimes rather than reported: nothing is alive to report it. The ask made
    # the artifact first, and the line names its exact source.
    source = asked.get("source") or ""
    src = source if os.path.isabs(source) else os.path.join(fake, *source.split("/"))
    check("the ask made its artifact first, and the line names the source and "
          "board build", source.endswith(".tex")
          and os.path.isfile(os.path.join(os.path.dirname(src), "doc.json"))
          and ("THE FILE IS `%s`" % source) in line
          and ("board build %s" % source) in line)
    later = time.time() + 5
    with open(src, "w", encoding="utf-8") as fh:
        fh.write("\\documentclass{beamer}\\title{How the harness works}\n")
    with open(src[:-4] + ".pdf", "wb") as fh:
        fh.write(b"%PDF-1.4\n" + b"%" * 3000)
    os.utime(src, (later, later))
    os.utime(src[:-4] + ".pdf", (later, later))
    library.forget()
    writeups.forget()
    said = board.build().get("writeups") or []
    check("and says when it is in the library, naming which document",
          len(said) == 1 and said[0]["state"] == "done"
          and said[0]["doc"] == asked.get("doc"))

    status, body = post("/writeup/seen", {"id": said[0]["id"]})
    library.forget()
    writeups.forget()
    check("reading it takes the row away, and the server is what remembers",
          status == 200 and body.get("ok") is True
          and not board.build().get("writeups"))

    # In do mode as well: a document is not a mode.
    with open(repo.state_path, "w", encoding="utf-8") as fh:
        json.dump({"course": "Test Course", "session": "lecture",
                   "mode": "do"}, fh)
    was = dict(repo.state())
    status, body = post("/artifact", {"make": "paper"})
    check("a paper can be asked for in do mode too",
          status == 200 and body.get("ok") is True)
    check("and the session is exactly as it was", repo.state() == was)
    writeups.forget()

finally:
    httpd.shutdown()


print()
if fails:
    print("%d FAILURES" % len(fails))
    sys.exit(1)
print("a handed-over step and a document each leave the session's mode alone")
