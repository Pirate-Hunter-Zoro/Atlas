#!/usr/bin/env python3
"""What a session takes without changing its mode, and what a sitting is told
about the part of the map it is on.

  * A STEP HANDED OVER (`POST /handover`) is a doing turn inside a teach
    session: the session is unchanged, the turn is told it is doing, and it
    gets the doing clock. Refused in do mode.
  * A PAPER OR A DECK (`POST /writeup`) is an action, not a mode: no card, no
    transcript turn, the mode untouched; commissioned from the door against
    another workspace it lands there.
  * A SITTING IN A WORKSPACE MADE OF COMPONENTS says it has no box when it has
    none, a sitting on a box is told the boundary, and a MISSION replaces the
    sitting rather than wearing it.
  * Tapping the box whose sitting is open goes back into it.

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

from tutorboard import atlas, sense, writeups
from tutorboard.course import library
from tutorboard.course import repo as course_repo
from tutorboard.lesson import archive, turns
from tutorboard.runner import turn as runturn
from tutorboard.server import handler, hub, spawn, tikz

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
atlas.forget()

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
# A SITTING BELONGS TO ONE COMPONENT, AND A SITTING WITH NO COMPONENT SAYS SO
# ---------------------------------------------------------------------------
# The map tap is meant to be THE door and it is one door among several: `tutor
# galois`, `board open`, a chapter tapped in the contents drawer and a board
# resumed after a reboot all leave `node` unset. `node_sense` used to answer
# that with the empty string, so those sittings had no scope AND nothing said
# one was missing -- and a turn with no scope picks one.
#
# The answer is not the same everywhere, which is the whole decision here. A
# course is chapters and a project is components: a lecture on Chapter 4 of
# Galois Theory has no box to be scoped to, and asking it which one it is about
# is a question with no answer. `map.scoped` is the thing that knows.
from tutorboard.course import map as mapping                  # noqa: E402

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
with open(os.path.join(made, "PLAN.md"), "w", encoding="utf-8") as fh:
    fh.write("# Plan\n\n  STEP 1. Repair the typist.\n    It drops the last word."
             " Lives in typist/run.py.\n")
mapping._cache.clear()
parts = mapping.status(made, {})
BOXES = dict((n["name"].rstrip("/"), n) for n in (parts or {"nodes": []})["nodes"])
check("the fixture is a workspace made of components",
      mapping.scoped(made) and set(["typist", "grader", "grid"]).issubset(BOXES))

sitting(made, session="lecture")
said = sense.node_sense(course_repo.Repo(made), {"session": "lecture"})
check("a sitting in a component workspace that nobody opened from the map says "
      "it has no box, rather than silently having none",
      "ABOUT NO PART OF THE MAP" in said and "THE EXCEPTION" in said)
check("and is told not to pick one for itself",
      "DO NOT PICK A PART OF THE REPOSITORY TO WORK ON" in said)
check("and asks which box in its first card",
      "first card asks which box" in said)
check("and is handed the address of every box, so the answer is a tap",
      all("#/w/projects/Parts/node/" + b["id"] in said for b in BOXES.values()))

# BUT NOT A MISSION, AND THAT IS THE ONE EXCEPTION TO THE RULE ABOVE.
#
# A mission is dispatched into whatever workspace holds the work, and most of
# them are made of components. The turn arrives with its task in the inbox and
# was then handed this paragraph as well -- told to do the work, and in the same
# breath told *your first card asks which box the evening is about*. The
# question wins, because a question is cheaper than nine hours of work: the
# mission that prompted this had run five hours in a components workspace with
# nothing to show.
#
# So a mission replaces the sitting rather than wearing it. It has a scope; it
# does not need a box and must not stop to ask for one.
_mission = {"id": "t0056", "task": "repair the diarization", "agent": "colibri",
            "at": time.time()}
_sent = sense.session_sense(course_repo.Repo(made), doing=True,
                            mission=_mission)
check("a MISSION into that same workspace is not asked which box it is about, "
      "because it arrived with a task and a question is how it spends nine "
      "hours saying nothing",
      "DO NOT PICK A PART OF THE REPOSITORY TO WORK ON" not in _sent
      and "first card asks which box" not in _sent
      and "ABOUT NO PART OF THE MAP" not in _sent)
check("and it is told what it is instead, with the task named as the scope",
      "THIS TURN IS A MISSION" in _sent
      and "the task is the last thing in the inbox" in _sent)
check("and it is still a doing turn, so nothing about the order of a change "
      "is lost by replacing the sitting",
      "THIS IS A DOING TURN" in _sent and "FIX THE RULE" in _sent)
check("and an ordinary sitting in that workspace is unchanged, because this is "
      "an exception and not a repeal",
      "DO NOT PICK A PART OF THE REPOSITORY TO WORK ON"
      in sense.session_sense(course_repo.Repo(made)))
# AND IT COSTS LESS THAN WHAT IT REPLACES. This block rides in a preamble the
# local model prefills at a few tokens a second, and the sitting it stands in
# for is most of a thousand words of how to teach an exercise.
_was = sense.session_sense(course_repo.Repo(made), doing=True)
check("and it is SHORTER than the sitting it replaces (%d words against %d), "
      "because a preamble is prefilled at a few tokens a second"
      % (len(_sent.split()), len(_was.split())),
      len(_sent.split()) < len(_was.split()))

# THE SAME QUESTION, ASKED OF A BOOK, HAS NO ANSWER -- so it is not asked.
sitting(course, session="lecture")
check("a book course is not asked which component it is about",
      sense.node_sense(course_repo.Repo(course), {"session": "lecture"}) == "")

# The legacy sittings a box is not the scope of. An imported state may still
# say one, and each arrived with a scope the person already chose.
for _kind, _why in (
        ("review", "a review is held over the chapters it was opened on"),
        ("walk", "a walkthrough is held over the units it was opened on"),
        ("make", "a make sitting's scope may be the whole evening")):
    check("no box is demanded of a legacy sitting: " + _why,
          sense.node_sense(course_repo.Repo(made), {"session": _kind}) == "")

# --- and the sitting that HAS a box is told where the boundary is ------------
typist = BOXES["typist"]
said = sense.node_sense(course_repo.Repo(made),
                        {"session": "lecture", "node": typist["id"]})
check("a sitting opened on a box is still handed the box",
      typist["name"] in said and "Turns the waveform into words" in said)
check("and is told a component boundary is a stopping point",
      "A COMPONENT BOUNDARY IS A STOPPING POINT" in said
      and "DO NOT FOLLOW IT" in said)
check("and what to do instead of following the work out of the box",
      "saving point" in said and "which box the work continues in" in said)
check("and that reading another part is not the thing being forbidden",
      "not wandering" in said)
check("the hand-off is a tap rather than an errand",
      "A TAP, NOT AN ERRAND" in said and "markdown link" in said)
check("so the OTHER boxes arrive with the address that opens a sitting in each",
      "#/w/projects/Parts/node/" + BOXES["grader"]["id"] in said
      and "#/w/projects/Parts/node/" + BOXES["grid"]["id"] in said)
check("and the box it is already in is not offered as somewhere to hand over to",
      said.count("#/w/projects/Parts/node/" + typist["id"]) == 0)
check("each of them says whether any work is planned there, because the box "
      "with none is the one whose step has to be PROPOSED",
      "no step of the plan names it" in said and "PROPOSE THE STEP" in said)

# THE BOX IS STILL DESCRIBED TO A SITTING IT DOES NOT SCOPE. A walkthrough
# opened over a box wants to know what the box is; it is held over its own units
# and a boundary it is not working inside is a rule about nothing.
said = sense.node_sense(course_repo.Repo(made),
                        {"session": "walk", "node": typist["id"]})
check("a walkthrough over a box is still handed the box",
      "Turns the waveform into words" in said)
check("but is not told to stop at a boundary it is not working inside",
      "STOPPING POINT" not in said and "#/w/" not in said)

# A WORKSPACE WITH NO ADDRESS PROMISES NO LINKS. A directory sitting in no
# family cannot be reached by an address at all, and a line pointing at a list
# of them that is not there is worse than the plain question.
odd = os.path.join(fake, "loose-Parts")
os.makedirs(os.path.join(odd, "typist"), exist_ok=True)
with open(os.path.join(odd, "tutorboard.json"), "w", encoding="utf-8") as fh:
    json.dump({"name": "Loose"}, fh)
with open(os.path.join(odd, "typist", "run.py"), "w", encoding="utf-8") as fh:
    fh.write('"""Turns the waveform into words."""\n' + PAD)
mapping._cache.clear()
said = sense.node_sense(course_repo.Repo(odd), {"session": "lecture"})
check("a workspace with no address still says the sitting has no box",
      "ABOUT NO PART OF THE MAP" in said)
check("but does not promise addresses it has not got",
      "#/w/" not in said and "addresses below" not in said)

# --- AND THE SITTING'S BRIEFING CARRIES IT, not only `node_sense` ------------
# The two returns a project actually lands on had no `node_sense` on them at
# all: a sitting with no chapter label fell through to the last line of
# `session_sense`, which is exactly the sitting this item is about.
sitting(made, session="lecture")
brief = sense.session_sense(course_repo.Repo(made))
check("a project's unlabelled sitting carries the missing-box paragraph in the "
      "line a headless turn is woken with",
      "ABOUT NO PART OF THE MAP" in brief)
sitting(made, session="lecture", node=typist["id"], chapter=typist["name"])
brief = sense.session_sense(course_repo.Repo(made))
check("and a sitting opened on a box carries the boundary rule in it",
      "A COMPONENT BOUNDARY IS A STOPPING POINT" in brief)
sitting(made, session="lecture")
mapping._cache.clear()

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
spawn.fresh_tutor = lambda root, course_name: replaced.append((root, course_name))
woken = []
spawn.wake_tutor = lambda r: woken.append(r) or True

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

    status, body = post("/writeup", {"makes": "essay"})
    check("a product that is not one of the two is refused by name",
          status == 400 and "paper or slides" in (body.get("error") or ""))
    status, body = post("/writeup", {})
    check("and so is a request that does not say which",
          status == 400 and not body.get("ok"))
    check("neither of those asked for anything",
          len(turns.load_turns(repo)) == turns_before
          and not writeups.waiting(repo))

    woke_before = len(woken)
    status, body = post("/writeup", {"makes": "slides"})
    check("the board takes the ask",
          status == 200 and body.get("ok") is True
          and body.get("makes") == "slides" and body.get("id"))
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
    check("and the scope with nobody naming one is the evening",
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
    found = re.search(r"THE FILE FOR THIS ONE IS `(docs/([a-z0-9-]+)/[a-z0-9-]+\.tex)`",
                      line)
    check("the ask made its artifact first, and the line names the source and "
          "board build", found and os.path.isfile(os.path.join(
              tmp, found.group(1).rsplit("/", 1)[0], "doc.json"))
          and ("board build %s" % found.group(1)) in line)
    src = os.path.join(tmp, *found.group(1).split("/"))
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
          and said[0]["doc"] == found.group(2))

    status, body = post("/writeup/seen", {"id": said[0]["id"]})
    library.forget()
    writeups.forget()
    check("reading it takes the row away, and the server is what remembers",
          status == 200 and body.get("ok") is True
          and not board.build().get("writeups"))

    # ------------------------------------------- and commissioned from the door
    # A PAPER OR A DECK, ASKED FOR ABOUT A WORKSPACE NOBODY IS LOOKING AT.
    #
    # **The want, in the owner's words:** *"the ability to write a paper or a
    # slide deck should just be an option on the homescreen, and from there I
    # want to be able to specify which projects/course, and which
    # sections/results."*
    #
    # The front door has no sitting behind it, so the second half of that
    # sentence cannot come from a board. It comes from what discovery already
    # found in the workspace being named -- `POST /writeup/scopes` -- and the
    # key that comes back is resolved against that same list.
    fields = workspace("courses", "Fields", {"name": "Fields"})
    with open(os.path.join(fields, "chapters.tsv"), "w", encoding="utf-8") as fh:
        fh.write("1\t1\t20\tch01-groups\tGroups\n"
                 "2\t21\t44\tch02-rings\tRings\n")
    os.makedirs(os.path.join(fields, "homework", "hw01"), exist_ok=True)
    with open(os.path.join(fields, "homework", "hw01", "hw01.tex"), "w",
              encoding="utf-8") as fh:
        fh.write("\\begin{problem}{1}\\end{problem}\n")

    status, body = post("/writeup/scopes", {"repo": "Fields"})
    keys = [s["key"] for s in (body.get("scopes") or [])]
    check("the front door can ask what a document in another workspace could "
          "be about", status == 200 and body.get("ok") is True
          and body.get("repo") == "Fields" and body.get("id") == "courses/Fields")
    check("a course offers its own chapters, by the names the course gives them",
          "chapter:ch01-groups" in keys and "chapter:ch02-rings" in keys
          and any(s["label"] == "Ch 1 — Groups"
                  for s in body["scopes"]))
    check("and its problem sets", "set:hw01" in keys)
    check("THE WHOLE WORKSPACE IS LAST, because it is the widest scope",
          keys[-1] == "workspace")
    check("every row says what the button reads and what is under it",
          all(s.get("key") and s.get("label") and s.get("what")
              for s in body["scopes"]))
    # The sentence the assistant is given is not the browser's to hold: a page
    # that has it is a page that can edit it, and then the key is decoration.
    check("but not the sentence the assistant is handed",
          all("about" not in s for s in body["scopes"]))

    status, body = post("/writeup/scopes", {"repo": "Nowhere-At-All"})
    check("a workspace this machine has not got is a miss, not a path",
          status == 404 and (body.get("error") or "") == "unknown workspace")

    # `tutor agent start` over there, which is what `/elsewhere` does and is
    # what has to be ASKED FOR before anything is written.
    ran = []
    real_tutor_cli = spawn.tutor_cli
    spawn.tutor_cli = lambda args, timeout=30: (
        ran.append(list(args)) or (0, "claude starting in Fields"))
    # WHAT IS IN THAT WORKSPACE BEFORE ANY OF THIS, and no `Repo` is built for
    # it here: constructing one makes `live/` and its eight subdirectories, so
    # a test that builds one first cannot see the route doing the same thing on
    # a request it refused. The refusal must leave the directory as it found it.
    before = sorted(os.listdir(fields))
    try:
        status, body = post("/writeup", {"makes": "paper", "repo": "Nope"})
        check("and so is a workspace named on the ask itself",
              status == 404 and (body.get("error") or "") == "unknown workspace")

        status, body = post("/writeup", {"makes": "paper", "repo": "Fields",
                                         "scope": "chapter:ch99-invented"})
        check("a scope key that workspace does not offer is refused by name",
              status == 400 and (body.get("error") or "") == "no such scope")
        check("and NOTHING was written for it -- no record, no inbox line, no "
              "start asked for", not ran and sorted(os.listdir(fields)) == before)

        status, body = post("/writeup", {"makes": "slides", "repo": "Fields",
                                         "scope": "chapter:ch02-rings",
                                         "about": "whatever I typed instead"})
        check("a deck can be commissioned against a workspace this board is "
              "not serving", status == 200 and body.get("ok") is True)
        check("the reply says WHERE it went, because that is not where it was "
              "asked from",
              body.get("repo") == "Fields" and body.get("where") == "Fields"
              and "Fields" in (body.get("detail") or ""))
        over = course_repo.Repo(fields)
        check("the start over there is asked for the way `/elsewhere` asks, "
              "and says a machine asked so the one address stays on the board "
              "the person is looking at",
              ran and ran[-1] == ["agent", "start", "Fields", "--respawn"])

        with open(over.messages_path, encoding="utf-8") as fh:
            lines = [json.loads(l) for l in fh if l.strip()]
        line = lines[-1].get("text", "") if lines else ""
        check("the inbox line is in THAT workspace, which is what a headless "
              "turn there is woken with",
              line.startswith("[writeup]") and lines[-1].get("read") is False)
        check("and the scope it was picked from is what the turn is told it is "
              "about", "Ch 2 — Rings" in line and "as this course covers it" in line)
        check("A SCOPE PICKED OFF THE LIST BEATS FREE TEXT SOMEBODY TYPED",
              "whatever I typed instead" not in line)
        writeups.forget()
        check("the record is over there too, so that board says it is being "
              "written", (writeups.waiting(over) or [{}])[0].get("makes")
              == "slides")
        check("AND NOTHING LANDED IN THE WORKSPACE THIS BOARD IS SERVING",
              not [l for l in open(repo.messages_path, encoding="utf-8")
                   if "Ch 2 — Rings" in l])

        # The board's own workspace answers to its own name, whether or not the
        # walk can see it -- this one is a temporary directory in no family.
        here_before = len(open(repo.messages_path, encoding="utf-8").readlines())
        status, body = post("/writeup", {"makes": "paper",
                                         "repo": os.path.basename(tmp)})
        check("naming the workspace the board already serves is the ask it "
              "always was", status == 200 and body.get("ok") is True
              and body.get("repo") == os.path.basename(tmp))
        check("and it lands here rather than anywhere else",
              len(open(repo.messages_path, encoding="utf-8").readlines())
              == here_before + 1)
    finally:
        spawn.tutor_cli = real_tutor_cli
    writeups.forget()

    # In do mode as well: a document is not a mode.
    with open(repo.state_path, "w", encoding="utf-8") as fh:
        json.dump({"course": "Test Course", "session": "lecture",
                   "mode": "do"}, fh)
    was = dict(repo.state())
    status, body = post("/writeup", {"makes": "paper"})
    check("a paper can be asked for in do mode too",
          status == 200 and body.get("ok") is True)
    check("and the session is exactly as it was", repo.state() == was)
    writeups.forget()

    # TAPPING THE BOX WHOSE SITTING IS OPEN GOES BACK INTO IT. A reload lands on
    # the map, and the box you were in is the obvious way back -- which filed the
    # evening's lesson away and opened an empty one.
    mrepo = course_repo.Repo(made)
    os.makedirs(mrepo.cards, exist_ok=True)
    for n in (1, 2):
        with open(os.path.join(mrepo.cards, "000%d-lesson.md" % n), "w",
                  encoding="utf-8") as fh:
            fh.write("---\nkind: lesson\n---\nCard %d.\n" % n)
    sitting(made, session="lecture", node=typist["id"], chapter="New direction")
    mapping._cache.clear()
    httpd.repo = mrepo
    status, body = post("/session", {"session": "lecture", "node": typist["id"],
                                     "begin": True})
    check("a tap on the open sitting's box is a way back into it",
          status == 200 and body.get("resumed") is True)
    check("and files nothing away", not archive.list_archive(mrepo))
    check("and leaves its cards and its name where they were",
          len([n for n in os.listdir(mrepo.cards) if n.endswith(".md")]) == 2
          and mrepo.state().get("chapter") == "New direction")
    check("and does not ask the tutor to begin a lesson already going",
          body.get("begun") is False)
    status, body = post("/session", {"session": "lecture", "node": BOXES["grid"]["id"],
                                     "begin": True})
    check("a different box is still a new sitting",
          status == 200 and not body.get("resumed")
          and len(archive.list_archive(mrepo)) == 1)
    httpd.repo = repo
finally:
    httpd.shutdown()


print()
if fails:
    print("%d FAILURES" % len(fails))
    sys.exit(1)
print("a handed-over step, a document and a box each leave the session's mode alone")
