#!/usr/bin/env python3
"""The plan was wrong, and saying so is one tap.

Three hours into an evening somebody realises the whole shape of the work is
wrong. Until the button, saying so meant a terminal: edit the plan by hand,
redraw the map, stop the assistant, start another one, and hope the one that
came back had not kept the old idea in its own conversation.

Four things have to happen for that tap to mean anything, and doing three of
them is worse than doing none -- a direction written down that the assistant
never reads is a direction the person believes is in force while nothing acts on
it. This drives the real HTTP handler, because what is guarded is the whole round
trip: the file, the archived lesson, the line the next turn is woken with, and
the assistant being REPLACED rather than asked nicely.
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

from tutorboard import brief, carry, direction, sense
from tutorboard.course import repo as course_repo
from tutorboard.lesson import archive, turns
from tutorboard.server import handler, hub, spawn, tikz

fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


# ---------------------------------------------------------------------------
# the file itself
# ---------------------------------------------------------------------------
tmp = tempfile.mkdtemp(prefix="tutor-direction-")
with open(os.path.join(tmp, "tutorboard.json"), "w", encoding="utf-8") as fh:
    json.dump({"name": "Test Course"}, fh)

SAID = ("Drop the model bake-off. This is now about calibrating the clinician "
        "ratings, and nothing else.")

check("nothing is in force in a workspace nobody has redirected",
      direction.read(tmp) == ("", ""))
check("and the briefing says nothing at all about it",
      direction.standing(tmp) == "")

kept, when = direction.write(tmp, SAID)
check("what they said is written at the root, where it crosses machines",
      os.path.isfile(os.path.join(tmp, "DIRECTION.md")))
check("it comes back as they wrote it", direction.read(tmp)[0] == SAID)
check("and stamped with when, because a direction is a thing they did on a day",
      bool(direction.read(tmp)[1]) and direction.read(tmp)[1] == when)
# The stamp is machinery and must never be part of what the tutor is handed.
check("the stamp is not part of their words", "<!--" not in direction.read(tmp)[0])

label = direction.label(SAID)
check("the sitting is named after the first thing they said",
      label.startswith("New direction") and "bake-off" in label)
check("and it fits the title bar", len(label) <= len("New direction — ") + 61)
check("a direction with no sentence-ending punctuation still gets a name",
      direction.label("rebuild the whole thing around consent").startswith("New direction"))

# ---------------------------------------------------------------------------
# what a turn is told
# ---------------------------------------------------------------------------
# This is the half that decides whether the tap did anything: a plan, a map and a
# handoff all written for the direction it replaced are worse than nothing, and a
# turn that reads the new direction LAST has already believed three of them.
said = direction.standing(tmp)
check("the standing direction quotes them rather than paraphrasing", SAID in said)
check("and says outright that it outranks the other documents",
      "outranks" in said)
check("and that bringing them true is the work rather than a separate job",
      "out of date" in said and "part of the work" in said)
check("and that the change is not to be argued with",
      "Do not argue" in said)

text = brief.briefing(course_repo.Repo(tmp), sense)
check("every briefing carries it", SAID in text)
# ABOVE THE METHOD, THE CONTRACT AND THE HANDOFF. Order is the feature here.
check("and carries it above everything it outranks",
      text.index(SAID) < text.index("the method, and what this sitting is"))

check("the turn woken by the change is told to rewrite the plan, not to ask",
      "REWRITE THE PLAN" in direction.CHANGED
      and "Do not ask permission" in direction.CHANGED)
check("and to redraw the map with the command that draws it",
      "board map" in direction.CHANGED)
check("and to put a sentence on the board before it starts, so it is not blank",
      "board write" in direction.CHANGED)
check("and to report over that sentence rather than writing a second card",
      "board write --over" in direction.CHANGED)
check("a plan handed back instead of the work is named as the failure",
      "hand back a plan" in direction.CHANGED)

# ---------------------------------------------------------------------------
# the whole round trip
# ---------------------------------------------------------------------------
direction.clear(tmp)
repo = course_repo.Repo(tmp)

# The one thing that must not actually happen in a test: starting a daemon. What
# is checked is that it is ASKED for, which is the half no prompt can do.
replaced = []
spawn.fresh_tutor = lambda root, course: replaced.append((root, course))

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
    # A lesson in progress, and a note from the turn before -- both of which are
    # about the direction that is being replaced.
    with open(os.path.join(repo.cards, "0001-lesson.md"), "w", encoding="utf-8") as fh:
        fh.write("---\nkind: lesson\n---\nThe old direction's first card.\n")
    carry.write_note(tmp, "They are halfway through the bake-off grid.")
    with open(repo.state_path, "w", encoding="utf-8") as fh:
        json.dump({"course": "Test Course", "session": "lecture",
                   "chapter": "Ch 1 — the bake-off"}, fh)

    status, body = post("/direction", {"text": SAID})
    check("the board accepts a change of direction",
          status == 200 and body.get("ok") is True)
    check("it is written down", direction.read(tmp)[0] == SAID)
    check("the sitting is renamed after it",
          (repo.state().get("chapter") or "").startswith("New direction"))
    check("the lesson they were in is filed away, not thrown away",
          len(archive.list_archive(repo)) == 1)
    check("and the board in front of them is clear",
          not [n for n in os.listdir(repo.cards) if n.endswith(".md")])
    # The note is one turn's word to the next about a lesson that no longer
    # exists. Left in place it is the first thing the new tutor reads.
    check("what the last turn was aiming at is forgotten",
          carry.read_note(tmp) == "")

    sent = turns.load_turns(repo)
    check("their words are in the transcript as a turn of theirs",
          len(sent) == 1 and sent[0].get("from") == "student"
          and SAID in (sent[0].get("text") or ""))
    check("and it is marked as what it is", sent[0].get("signal") == "direction")

    with open(repo.messages_path, "r", encoding="utf-8") as fh:
        lines = [json.loads(l) for l in fh if l.strip()]
    line = lines[-1].get("text", "") if lines else ""
    check("the inbox carries it, which is what `board wait` watches", bool(lines))
    check("the line says what happened", "[direction]" in line)
    check("carries their own words, not a summary of them", SAID in line)
    check("tells the turn to rewrite the plan", "REWRITE THE PLAN" in line)
    check("and still says what kind of sitting this is",
          "THE LESSON IS EXERCISES" in line or "lesson is" in line.lower())
    check("it arrives unread, or nothing wakes on it",
          lines[-1].get("read") is False)

    # THE HALF NO PROMPT CAN DO. A running tutor holds the old direction in its
    # own conversation, and no file on disk can contradict that.
    check("the assistant is replaced rather than asked to change its mind",
          len(replaced) == 1)

    # The panel opens showing what it is about to replace, on a device that has
    # been closed since it was set.
    live = board.build()
    check("the board is told what is in force",
          (live.get("direction") or {}).get("text") == SAID)

    status, body = post("/direction", {"text": "   "})
    check("a direction with nothing in it is refused",
          status == 400 and body.get("ok") is False)
    check("and nothing was archived on the way",
          len(archive.list_archive(repo)) == 1)
finally:
    httpd.shutdown()

print()
if fails:
    print("%d FAILURES" % len(fails))
    sys.exit(1)
print("the direction is theirs to change, and everything under it is redone")
