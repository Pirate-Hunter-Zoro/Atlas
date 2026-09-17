#!/usr/bin/env python3
"""The style of a sitting, changed without losing the lesson -- and defaulted at all.

Two halves of one complaint.

**The aim could not be changed.** It reached `live/state.json` from exactly one
place -- a tap on the map, through `POST /session` -- and every path through
`/session` calls `board open`, which archives the lesson. So "wait, now teach me
how this works", said three hours into building something, cost the evening it
was said in.

**And a sitting nobody opened from the map had no style at all.** `tutor galois`,
`board open`, a chapter tapped in the contents drawer and a board resumed after a
reboot all left `aim` unset, so the sitting ran on stance alone -- which is
`teach` nearly everywhere and is the wrong answer for a project.

The route is driven over real HTTP, because what is guarded is the whole round
trip and the two things that must NOT happen in it: the lesson must not be filed
away, and the tutor must not be replaced.
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

from tutorboard import atlas, sense, writeups
from tutorboard.course import config
from tutorboard.course import library
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
# the vocabulary, and what is derived from it
# ---------------------------------------------------------------------------
check("every aim has a sentence the tutor is given",
      all(config.AIM_MEANS.get(a) for a in config.AIMS))
check("and every aim says who writes the code",
      all(config.AIM_STANCE.get(a) in ("teach", "do") for a in config.AIMS))
check("the three that produce a change are the three that write",
      [a for a in config.AIMS if config.AIM_STANCE[a] == "do"]
      == ["build", "paper", "slides"])
check("the two that are held over a scope are named, not guessed at",
      set(config.AIMS_OVER) == {"trace", "drill"})

# ---------------------------------------------------------------------------
# a family default, overridable at every level below it
# ---------------------------------------------------------------------------
fake = tempfile.mkdtemp(prefix="tutor-aiming-tree-")
with open(os.path.join(fake, "atlas.json"), "w", encoding="utf-8") as fh:
    json.dump({"families": [
        {"id": "courses", "name": "Courses", "aim": "teach"},
        {"id": "projects", "name": "Projects", "aim": "build"},
        {"id": "nowhere", "name": "Nowhere"},
    ]}, fh)


def workspace(family, name, cfg=None):
    where = os.path.join(fake, family, name)
    os.makedirs(where, exist_ok=True)
    with open(os.path.join(where, "tutorboard.json"), "w", encoding="utf-8") as fh:
        json.dump(dict({"name": name}, **(cfg or {})), fh)
    return where


os.environ["TUTORBOARD_COURSES"] = fake
atlas.forget()

course = workspace("courses", "Probability")
project = workspace("projects", "Harness")
# A workspace that answers for itself, over its family's default.
own = workspace("projects", "Lectures", {"aim": "teach"})
# And one whose family says nothing at all.
loose = workspace("nowhere", "Odd")

check("a course with nothing declared is taught", config.aim_for(course, {}) == "teach")
check("a workspace that names an aim beats its family",
      config.aim_for(own, {}) == "teach")
check("a sitting that names one beats its workspace",
      config.aim_for(own, {"aim": "build"}) == "build")
check("a family that declares nothing leaves the sitting with no aim",
      config.aim_for(loose, {}) == "")
check("and a word that is not an aim is dropped rather than obeyed",
      config.aim_for(course, {"aim": "whatever"}) == "teach")

# A FAMILY DEFAULT IS A STYLE, NEVER AN INSTRUCTION TO WRITE CODE.
#
# `projects` defaults to `build` in `atlas.json` and `libr-local-llm` declares
# only a name, so a plain lecture opened in it was a DOING turn: the tutor wrote
# code and reported. Being taught cost a tap on `teach` in the `for:` row first,
# which is one tap and is the wrong way round for a workspace somebody arrives
# at wanting to understand it.
#
# The rule it gives way to is one `read_config` already states about a stance:
# writing the code for somebody who wanted to learn it is the one failure here
# that cannot be undone by the next card, so it is only ever done because a
# repository asked for it IN WRITING. A sentence about a directory is not a
# repository asking. A teaching default still applies -- it takes nothing away,
# and it is what gives a bare `tutor galois` its style.
check("a family default that TEACHES still reaches a sitting nobody chose",
      config.aim_for(course, {}) == "teach")
check("but one that WRITES does not, so the sitting runs on stance",
      config.aim_for(project, {}) == "" and config.stance_for(project, {}) == "teach")
check("a workspace that asked for it in writing still gets it",
      config.aim_for(workspace("projects", "Written", {"aim": "build"}), {}) == "build")
check("and so does a sitting that tapped it",
      config.aim_for(project, {"aim": "build"}) == "build"
      and config.stance_for(project, {"aim": "build"}) == "do")
check("and `stance: do` in writing is untouched by any of it",
      config.stance_for(workspace("projects", "Doer", {"stance": "do"}), {}) == "do")

# STANCE IS DERIVED FROM THE AIM, not chosen beside it.
check("a course's default style means the tutor does not write the code",
      config.stance_for(course, {}) == "teach")
check("a repository that says `stance` in writing still wins over its family",
      config.stance_for(workspace("projects", "Taught", {"stance": "teach"}), {})
      == "teach")
check("and a sitting that chose one wins over everything",
      config.stance_for(project, {"stance": "teach"}) == "teach"
      and config.stance_for(course, {"stance": "do"}) == "do")
for aim in config.AIMS:
    want = "do" if aim in ("build", "paper", "slides") else "teach"
    check("an aim of %s resolves to a stance of %s" % (aim, want),
          config.stance_for(course, {"aim": aim}) == want)

# AND THE CLOCK AGREES WITH THE PROMPT. `bin/tutor` used to hold a third copy of
# the list of aims that write, and read `tutorboard.json` by hand as well -- so a
# family's default reached the prompt and not the timeout, and a doing turn ran
# on a teaching turn's clock.
import importlib.machinery                                   # noqa: E402
import importlib.util                                        # noqa: E402

_tl = importlib.machinery.SourceFileLoader("tutorcli", os.path.join(ROOT, "bin", "tutor"))
tutorcli = importlib.util.module_from_spec(
    importlib.util.spec_from_loader("tutorcli", _tl))
_tl.exec_module(tutorcli)

check("nothing in the launcher keeps its own list of the aims that write",
      not hasattr(tutorcli, "DOING_AIMS"))
os.makedirs(os.path.join(project, "live"), exist_ok=True)


def sitting(where, **kw):
    with open(os.path.join(where, "live", "state.json"), "w", encoding="utf-8") as fh:
        json.dump(kw, fh)


for aim in config.AIMS:
    sitting(project, session="lecture", aim=aim)
    check("the launcher and the board agree about %s" % aim,
          tutorcli.doing_now(project)
          == (config.stance_for(project, {"aim": aim}) == "do"))
sitting(project, session="lecture")
check("a project's plain lecture is a teaching turn, because nobody chose "
      "otherwise and a family default cannot choose it for them",
      not tutorcli.doing_now(project))
sitting(project, session="lecture", aim="build")
check("and it is a doing turn the moment somebody taps `build`",
      tutorcli.doing_now(project))
os.makedirs(os.path.join(course, "live"), exist_ok=True)
sitting(course, session="lecture")
check("and a course's plain lecture is not", not tutorcli.doing_now(course))

# A STEP HANDED OVER IS A DOING TURN INSIDE A COACHING SITTING, and the sitting
# is left saying `coach` on purpose. So the state is right about the evening and
# says the wrong thing about this one turn: only the signal it was woken with
# can say, and it has to reach the clock as well as the prompt. A doing turn on
# a teaching turn's fifteen minutes is a turn killed with files staged and
# nothing committed.
sitting(course, session="lecture", aim="coach")
check("a coaching sitting is a teaching turn, as it was",
      not tutorcli.doing_now(course))
check("but the step it hands over is a doing turn",
      tutorcli.doing_now(course, "handover"))
CLOCK = {"headless_timeout": 900, "doing_timeout": 3600}
check("so the handed-over step gets a doing turn's clock",
      tutorcli.turn_timeout(CLOCK, course) == 900
      and tutorcli.turn_timeout(CLOCK, course, None, "handover") == 3600)
check("and every other signal leaves the clock where it was",
      tutorcli.turn_timeout(CLOCK, course, None, "help") == 900)
sitting(course, session="lecture")            # as the checks below expect it

# ---------------------------------------------------------------------------
# what the tutor is told about a sitting nobody chose a style for
# ---------------------------------------------------------------------------
sitting(project, session="lecture")
said = sense.session_sense(course_repo.Repo(project))
check("a project's sitting nobody chose a style for is not told to write code",
      "DOING TURN" not in said and config.AIM_MEANS["build"] not in said)
sitting(project, session="lecture", aim="build")
said = sense.session_sense(course_repo.Repo(project))
check("and is, the moment somebody taps it",
      "DOING TURN" in said and config.AIM_MEANS["build"] in said)
sitting(project, session="lecture")
said = sense.session_sense(course_repo.Repo(course))
check("a course's is told to teach it",
      "DOING TURN" not in said and config.AIM_MEANS["teach"] in said)

# A review inherits nothing. Its family's default is `build`, and a review that
# was told to write code would be the one sitting whose whole point is that it
# asks.
sitting(project, session="review", review=[])
said = sense.session_sense(course_repo.Repo(project))
check("a review does not inherit a family's aim to write",
      config.AIM_MEANS["build"] not in said and "DOING TURN" not in said)

# And an aim of `paper` gets the METHOD for making a document, not just the one
# sentence. This is the whole of "change 3 lands and nothing reads it": the
# method was reached only through `session == "make"`.
sitting(project, session="lecture", aim="paper")
said = sense.session_sense(course_repo.Repo(project))
check("an aim of paper gets the make method, not only its one sentence",
      "MAKE SITTING" in said and "Work in sections" in said)
check("and is told the document is about the subject rather than the sitting",
      "NEVER A NARRATION OF THIS SITTING" in said)

# ---------------------------------------------------------------------------
# the route, over real HTTP
# ---------------------------------------------------------------------------
tmp = tempfile.mkdtemp(prefix="tutor-aiming-")
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
    # Three hours into building something, with cards on the board.
    for n, title in ((1, "lesson"), (2, "lesson"), (3, "lesson")):
        with open(os.path.join(repo.cards, "000%d-%s.md" % (n, title)), "w",
                  encoding="utf-8") as fh:
            fh.write("---\nkind: lesson\n---\nCard %d.\n" % n)
    with open(repo.state_path, "w", encoding="utf-8") as fh:
        json.dump({"course": "Test Course", "session": "lecture",
                   "chapter": "The serve harness", "aim": "build"}, fh)
    before = open(repo.state_path, encoding="utf-8").read()

    status, body = post("/aim", {"aim": "teach"})
    check("the board accepts a change of aim",
          status == 200 and body.get("ok") is True and body.get("changed") is True)
    check("it is written into the sitting", repo.state().get("aim") == "teach")
    check("THE LESSON IS NOT FILED AWAY", not archive.list_archive(repo))
    check("and the cards are all still on the board",
          len([n for n in os.listdir(repo.cards) if n.endswith(".md")]) == 3)
    check("the tutor is not replaced", not replaced)
    check("nothing else about the sitting moved",
          repo.state().get("chapter") == "The serve harness"
          and repo.state().get("session") == "lecture")

    sent = turns.load_turns(repo)
    check("their tap is in the transcript as a turn of theirs",
          len(sent) == 1 and sent[0].get("from") == "student")
    check("and it is marked as what it is", sent[0].get("signal") == "aim")

    with open(repo.messages_path, "r", encoding="utf-8") as fh:
        lines = [json.loads(l) for l in fh if l.strip()]
    line = lines[-1].get("text", "") if lines else ""
    check("the inbox carries it, which is what `board wait` watches", bool(lines))
    check("the line says what happened", line.startswith("[aim]"))
    check("it says what the new aim asks for", config.AIM_MEANS["teach"] in line)
    check("it says everything already on the board stands",
          "board stands" in line and "not a new tutor" in line.replace("you are ", ""))
    check("and it still says what this sitting is",
          "THE LESSON IS EXERCISES" in line)
    check("it arrives unread, or nothing wakes on it",
          lines[-1].get("read") is False)
    # THE TAP IS THE INSTRUCTION, the same way choosing a way to work on the map
    # is. A preference written down and applied later is not what "now teach me
    # how this works" means.
    check("a turn is woken on it", bool(woken))

    # Nothing to do, and a model call is what a second tap would cost.
    status, body = post("/aim", {"aim": "teach"})
    check("tapping the aim it already has wakes nothing",
          status == 200 and body.get("changed") is False and len(woken) == 1)

    status, body = post("/aim", {"aim": "trace"})
    check("an aim held over a scope is refused by name",
          status == 400 and "scope" in (body.get("error") or ""))
    status, body = post("/aim", {"aim": "whatever"})
    check("and so is a word that is not an aim at all", status == 400)
    check("neither of those changed the sitting", repo.state().get("aim") == "teach")

    # ----------------------------------------------------------------- one step
    # THE WAY OUT OF ONE STEP OF COACHING, WITHOUT LEAVING IT. Everything the
    # `/aim` block above guards has to hold here too, and one thing more: the
    # sitting must still be a coaching sitting afterwards, or this is the escape
    # it was built to replace wearing a smaller button.
    status, body = post("/aim", {"aim": "coach"})
    check("the sitting is a coaching one", repo.state().get("aim") == "coach")
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
    check("THE SITTING IS STILL A COACHING SITTING",
          repo.state().get("aim") == "coach")
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
    # The sitting says `coach`, so nothing about the STATE would produce this.
    check("THE TURN IS TOLD IT IS A DOING TURN, which the sitting does not say",
          "THIS IS A DOING TURN" in line
          and "DOING TURN" not in sense.session_sense(repo))
    check("it still says what this sitting is",
          config.AIM_MEANS["coach"] in line)
    check("it arrives unread, or nothing wakes on it",
          lines[-1].get("read") is False)
    check("a turn is woken on it", len(woken) == woke_before + 1)

    # Where the tutor is already writing the code there is nothing to hand over,
    # and waking a turn to be told so is a model call somebody pays for.
    post("/aim", {"aim": "build"})
    status, body = post("/handover", {"card": "0003"})
    check("a sitting that already writes the code has nothing to hand over",
          status == 400 and "already writing" in (body.get("error") or ""))
    post("/aim", {"aim": "teach"})

    # ------------------------------------------------------- and a document
    # A PAPER OR A DECK, ASKED FOR FROM ANY SITTING, WITHOUT CHANGING IT.
    #
    # **The want, and it was asked as a question:** *"at any point can I have a
    # presentation or paper written up going through the things we talked about
    # in that tutoring session? Can I do that in ANY tutoring session?"*
    #
    # It was refused twice over. Asking meant `POST /aim`, which makes the whole
    # sitting a make sitting and every card after it a make card -- and the aim
    # row is withheld from a review and a walkthrough, so in the two sittings
    # where a write-up is worth the most there was no route at all.
    #
    # So a document is a PRODUCT rather than an aim. Everything the `/aim` block
    # guards has to hold here as well, and two things more: the aim itself must
    # not move, and it has to work in the two sittings that have no aim row.
    post("/aim", {"aim": "coach"})
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
    check("THE AIM OF THE SITTING HAS NOT MOVED", repo.state() == before_state)
    check("the lesson is not filed away", not archive.list_archive(repo))
    check("the cards are all still on the board",
          len([n for n in os.listdir(repo.cards) if n.endswith(".md")]) == 3)
    check("the tutor is not replaced", not replaced)
    # `/aim` and `/handover` both put the tap in the transcript, because a card
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
          "Write no card" in line and "aim of it has not changed" in line)
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

    # AND WHEN IT IS THERE, which is derived from the library rather than
    # reported: nothing is alive to report it.
    where = os.path.join(tmp, "writeups", "how-the-harness-works")
    os.makedirs(where, exist_ok=True)
    with open(os.path.join(where, "how-the-harness-works.tex"), "w",
              encoding="utf-8") as fh:
        fh.write("\\title{How the harness works}\n" + "x" * 3000)
    library.forget()
    writeups.forget()
    said = board.build().get("writeups") or []
    check("and says when it is in the library, naming which document",
          len(said) == 1 and said[0]["state"] == "done"
          and "how-the-harness-works" in said[0]["doc"])

    status, body = post("/writeup/seen", {"id": said[0]["id"]})
    library.forget()
    writeups.forget()
    check("reading it takes the row away, and the server is what remembers",
          status == 200 and body.get("ok") is True
          and not board.build().get("writeups"))

    # THE TWO SITTINGS THE AIM ROW IS WITHHELD FROM, which is the whole point.
    for kind, extra in (("review", {"review": ["Ch 1"]}),
                        ("walk", {"walk": ["a.py"]})):
        with open(repo.state_path, "w", encoding="utf-8") as fh:
            json.dump(dict({"course": "Test Course", "session": kind}, **extra), fh)
        was = dict(repo.state())
        status, body = post("/writeup", {"makes": "paper"})
        check("a paper can be asked for in a %s, where no aim can be changed"
              % kind, status == 200 and body.get("ok") is True)
        check("and the %s is exactly as it was" % kind, repo.state() == was)
        status, body = post("/aim", {"aim": "trace"})
        check("while changing the aim there is still refused (%s)" % kind,
              status == 400)
    writeups.forget()

    # The board has to be able to SHOW which aim is in force, including when it
    # was never chosen -- resolved by the server, never re-derived in the client.
    with open(repo.state_path, "w", encoding="utf-8") as fh:
        json.dump({"course": "Test Course", "session": "lecture"}, fh)
    live = board.build()
    check("the payload says what the sitting is running under",
          live["state"].get("aim_now") == config.aim_for(tmp, live["state"]))
    check("and what its stance resolves to",
          live["state"].get("stance_now") == config.stance_for(tmp, live["state"]))
finally:
    httpd.shutdown()

# ---------------------------------------------------------------------------
# and the terminal can do it too
# ---------------------------------------------------------------------------
loader = importlib.machinery.SourceFileLoader("boardcli",
                                              os.path.join(ROOT, "bin", "board"))
boardcli = importlib.util.module_from_spec(
    importlib.util.spec_from_loader("boardcli", loader))
loader.exec_module(boardcli)

check("board aim is a command", "aim" in boardcli.COMMANDS)
live_cli = boardcli.Live(tmp)
check("it changes the sitting", boardcli.cmd_aim(live_cli, ["coach"]) == 0
      and live_cli.state().get("aim") == "coach")
check("it refuses an aim that is held over a scope",
      boardcli.cmd_aim(live_cli, ["drill"]) == 2
      and live_cli.state().get("aim") == "coach")
check("and it leaves the lesson alone", not archive.list_archive(repo))

print()
if fails:
    print("%d FAILURES" % len(fails))
    sys.exit(1)
print("the style of a sitting is theirs to change, and every sitting has one")
