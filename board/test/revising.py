#!/usr/bin/env python3
"""A revision is a turn, and it is not part of the lesson.

Feedback on a document comes off the library page, which is not a sitting. The
turn it wakes has to be able to edit a document and rebuild it without touching
the evening somebody else is having on the same board -- and the thing that makes
that hard is not the card, it is the CONVERSATION.

`turn_plan` resumes the agent's own session by default, which is what makes a
twelve-card lesson affordable. A revision resumed into a lesson drags the lesson
into the document and the document back into the lesson. The alternative was a
second daemon per workspace, which doubles the cost and the failure modes for a
turn that takes a minute.

So: a `[revise]` line runs fresh, writes no card, leaves `state.json` alone, and
puts its report beside the document. What is guarded here is each of those, plus
the one that only shows up a turn later -- that the lesson does not then resume
into the revision's session.

AN OVERHAUL IS THE SAME TURN WITH A WIDER LICENCE. `[rework]` is the other ask
on the library's own panel, and the ONE thing that separates it from a revision
is that the do-not-widen sentence is not in the prompt -- so that absence is
asserted here, because a prompt that grew the sentence back would look like a
working feature and behave like a correction.

A SHIP IS THE SAME TURN WITH A DIFFERENT JOB, and it is guarded here for that
reason: a mission told to ship itself wakes a `[ship]` line, which runs fresh,
writes no card and pushes what another assistant wrote. Everything about the
shape is the revision's; what is different is that the assistant running it is
never the one that did the work.
"""
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tutorboard import sense
from tutorboard.course import library
from tutorboard.course.repo import Repo
from tutorboard.server import spawn
from tutorboard.runner import service as runner_service  # noqa: E402
from tutorboard.server.routes import library as library_route

from tutorboard.runner import prompts  # noqa: E402
from tutorboard.runner import turn as runturn  # noqa: E402

fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


SPEC = {"headless": ["agent", "-p", "{prompt}", "--continue"],
        "headless_first": ["agent", "-p", "{prompt}"]}

# ---------------------------------------------------------------------------
# which turn a revision is
# ---------------------------------------------------------------------------
check("a revision line is read as the signal it carries",
      runturn.turn_signal("[2026-09-16 18:02:11] [revise] the document is x")
      == "revise")

use, template = runturn.turn_plan(SPEC, "revise")
check("a revision runs fresh with the revision's own prompt",
      use == SPEC["headless_first"] and template is prompts.HEADLESS_REVISE_PROMPT)
use, template = runturn.turn_plan(SPEC)
check("and so does an ordinary turn: every turn is a fresh process",
      use == SPEC["headless_first"] and template is prompts.HEADLESS_FIRST_PROMPT)

# ---------------------------------------------------------------------------
# what that turn is told
# ---------------------------------------------------------------------------
said = prompts.HEADLESS_REVISE_PROMPT
check("it is told this turn is not part of the lesson",
      "NOT PART OF THE LESSON" in said)
check("and to write no card, in as many words", "Write no card" in said)
for name in ("board write", "board open", "the session's state", "its cards",
             "HANDOFF.md"):
    check("and not to touch %s" % name, name in said)
check("it is told to revise the source rather than write a new document",
      "REVISE THE DOCUMENT" in said and "Do not start it again" in said)
check("and to leave its report beside the document, in the feedback file",
      "bottom of the feedback file" in said.lower()
      or "BOTTOM OF THE FEEDBACK FILE" in said)
check("it is not sent to read the contract or the cards, none of which is about "
      "this document",
      "Do not read" in said and "TEACHING.md" in said)

# ---------------------------------------------------------------------------
# AND THE WIDER ASK ON THE SAME PANEL: AN OVERHAUL
# ---------------------------------------------------------------------------
# "That presentation needs an overhaul now that we plan to use colibri" is not a
# correction. The revision prompt above says outright *do not start it again and
# do not widen it*, which is exactly right for "figure 3 is mislabelled" -- so
# until there was a second ask, the only route to an overhaul was a terminal.
check("an overhaul line is read as the signal it carries",
      runturn.turn_signal("[2026-09-17 20:10:00] [rework] the deck is for x")
      == "rework")
use, template = runturn.turn_plan(SPEC, "rework")
check("an overhaul runs fresh with its own prompt",
      use == SPEC["headless_first"] and template is prompts.HEADLESS_REWORK_PROMPT)

# A DOING TURN'S CLOCK, and a plain revision deliberately does not get one: a
# correction changes what a note names and is over in a minute, while an
# overhaul rewrites thirty-three pages and runs LaTeX at the end of it.
CLOCK = {"headless_timeout": 900, "doing_timeout": 3600}
_empty = tempfile.mkdtemp()
check("an overhaul gets a doing turn's time, whatever the sitting says",
      runturn.turn_timeout(CLOCK, _empty, None, "rework") == 3600)
check("while a correction is left on the sitting's own clock",
      runturn.turn_timeout(CLOCK, _empty, None, "revise") == 900)

worked = prompts.HEADLESS_REWORK_PROMPT
check("an overhaul is told this turn is not part of the lesson",
      "NOT PART OF THE LESSON" in worked)
check("and to write no card", "Write no card" in worked)
for name in ("board write", "board open", "the session's state", "its cards",
             "HANDOFF.md"):
    check("and an overhaul is not to touch %s" % name, name in worked)
check("THE DO-NOT-WIDEN SENTENCE IS NOT IN IT, which is the whole difference "
      "between the two asks",
      "do not widen" not in worked.lower()
      and "do not start it again" not in worked.lower())
check("while it IS still in the correction's prompt, where it belongs",
      "Do not start it again and do not widen it" in said)
check("an overhaul is told it may restructure, cut, reorder and rewrite",
      "restructure" in worked and "reorder" in worked and "cut what" in worked)
check("and told where the brief is, because the purpose outranks the shape",
      "What this document is FOR now" in worked and "brief" in worked)
check("it is told the source is committed, so it works rather than hedging",
      "committed" in worked and "one diff" in worked)
check("and to leave its record in the feedback file like a correction does",
      "BOTTOM OF THE FEEDBACK FILE" in worked)
check("a deck stays a deck: the KIND is the one thing an overhaul may not "
      "change", "same KIND of document" in worked)
check("and the file stays where it is, because the library names a document by "
      "its path and the ink on its pages is anchored to that name",
      "LEAVE THE FILE WHERE IT IS" in worked)

line = sense.rework_sense("writeups/deck/deck.tex",
                          "writeups/deck/feedback/2026-09-17-v1.md",
                          "a fifteen-minute briefing for the lab meeting")
check("the line an overhaul is woken with names the source it edits",
      "writeups/deck/deck.tex" in line)
check("and the feedback file",
      "writeups/deck/feedback/2026-09-17-v1.md" in line)
check("and the purpose, so the board can say what is being written while the "
      "turn runs", "a fifteen-minute briefing for the lab meeting" in line)
check("and says outright that this is not a correction",
      "OVERHAUL" in line and "not a correction" in line)
check("and that the lesson on the board is somebody else's",
      "NOT PART OF THE LESSON" in line and "its cards" in line)

# ---------------------------------------------------------------------------
# AND THE OTHER TURN OF THE SAME SHAPE: A MISSION SHIPPING ITSELF
# ---------------------------------------------------------------------------
# "when I put anything on a mission, I should have the option to tell it to ship
#  its changes once it is done."
#
# A ship is a revision's twin. It is not part of the lesson, it runs fresh, it
# writes no card, and the lesson must not resume into it -- a tutor whose next
# card resumes a session about a git diff thinks the evening was about git. What
# it does differently is who runs it: never the assistant that did the work.
check("a ship line is read as the signal it carries",
      runturn.turn_signal("[2026-09-17 21:40:02] [ship] a mission finished")
      == "ship")
use, template = runturn.turn_plan(SPEC, "ship")
check("a ship runs fresh with its own prompt",
      use == SPEC["headless_first"] and template is prompts.HEADLESS_SHIP_PROMPT)

shipped = prompts.HEADLESS_SHIP_PROMPT
check("a ship is told this turn is not part of the lesson",
      "NOT PART OF THE LESSON" in shipped)
check("and to write no card", "Write no card" in shipped)
for name in ("board write", "board open", "the session's state", "its cards",
             "HANDOFF.md"):
    check("and a ship is not to touch %s" % name, name in shipped)
check("it is told to READ the diff rather than trust it, because it is another "
      "assistant's work",
      "git diff" in shipped and "rather than trusting it" in shipped)
check("and that session content in it is the one thing that stops the push",
      "session content" in shipped and "STOP" in shipped)
check("and that the refusal underneath it is not to be worked around",
      "--anyway" in shipped and "do not work around it" in shipped)
check("and it pushes with the one push there is",
      "board push" in shipped)

# A DOING TURN'S CLOCK. A ship reads a diff, judges it and pushes over a tailnet;
# a teaching turn's fifteen minutes is a turn killed with the work half done.
CFG = {"headless_timeout": 900, "doing_timeout": 3600}
check("a ship gets a doing turn's time, whatever the sitting says",
      runturn.turn_timeout(CFG, tempfile.mkdtemp(), None, "ship") == 3600)

said = sense.ship_sense("colibri", "reproduce the corrected transcript")
check("the line a ship is woken with names what the mission was asked to do",
      "reproduce the corrected transcript" in said)
check("and who did the work, which is the whole reason it is not them pushing",
      "colibri" in said and "not the assistant that made them" in said)
check("and says the lesson on the board is somebody else's",
      "NOT PART OF THE LESSON" in said and "its cards" in said)

line = sense.revise_sense("writeups/serve/serve.tex",
                          "writeups/serve/feedback/2026-09-16-v1.md")
check("the line it is woken with names the document",
      "writeups/serve/serve.tex" in line)
check("and the feedback file", "writeups/serve/feedback/2026-09-16-v1.md" in line)
check("and says the lesson on the board is somebody else's",
      "NOT PART OF THE LESSON" in line and "its cards" in line)

# ---------------------------------------------------------------------------
# A MANUSCRIPT IS REVISED LIKE ANY OTHER DOCUMENT, and rebuilt by `board build`
# ---------------------------------------------------------------------------
# TRD-EHR's shape: `paper1-trd-prediction/manuscript.md` is the source, and the
# .pdf and .docx beside it are built from it. A note from the library wakes a
# `[revise]` turn, and that turn is told the one builder there is. The provider
# is a fake script that records the prompt it was handed.
tmp = os.path.realpath(tempfile.mkdtemp(prefix="tutor-revising-"))
work = os.path.join(tmp, "projects", "TRD-EHR")
paper = os.path.join(work, "paper1-trd-prediction")
os.makedirs(paper)
with open(os.path.join(work, "tutorboard.json"), "w", encoding="utf-8") as fh:
    json.dump({"name": "TRD-EHR"}, fh)
with open(os.path.join(paper, "manuscript.md"), "w", encoding="utf-8") as fh:
    fh.write("# TRD prediction from EHR text\n\nSection 3 reports a split.\n")
for ext in (".pdf", ".docx"):
    with open(os.path.join(paper, "manuscript" + ext), "wb") as fh:
        fh.write(b"x" * 30000)
library.forget()
doc = [d for d in library.documents(work) if d["stem"] == "manuscript"][0]
check("TRD-EHR's manuscript is a library document with its Markdown as source",
      doc["source"] == "paper1-trd-prediction/manuscript.md")

repo = Repo(work)
note = library.write_note(repo, doc["id"], "Section 3 reports the wrong split.",
                          hand_over=False)
check("the note is filed beside the manuscript", note.get("ok") is True
      and note["rel"].startswith("paper1-trd-prediction/feedback/"))


class _Hub(object):
    def __init__(self):
        import threading
        self.worker = type("W", (), {"dirty": threading.Event()})()


class _H(object):
    def __init__(self):
        self.hub = _Hub()

    def note(self, _msg):
        pass


runner_service.wake = lambda r: True
asked = library_route._revise(_H(), repo, doc, note["rel"],
                              ledger_rel=note.get("ledger") or "",
                              ids=note.get("ids") or [])
check("the board takes the revision itself", asked.get("revise") == "board"
      and asked.get("asked") is True)

from tutorboard.lesson import inbox                            # noqa: E402
out, _taken = inbox.take(repo)
signal, _ = runturn.woken_for(work, out)
check("the inbox hands the turn a [revise] line", out and signal == "revise")

seen = os.path.join(tmp, "prompt.txt")
fake = os.path.join(tmp, "fake-provider")
with open(fake, "w", encoding="utf-8") as fh:
    fh.write("#!/bin/sh\nprintf '%s' \"$2\" > " + seen + "\n")
os.chmod(fake, 0o755)
spec = {"headless": [fake, "-p", "{prompt}", "--continue"],
        "headless_first": [fake, "-p", "{prompt}"]}
use, template = runturn.turn_plan(spec, signal)
prompt = template % {"inbox": out.strip(), "handoff": ""}
with open(os.path.join(tmp, "turn.log"), "a") as log:
    rc, timed_out = runturn.run_turn(
        [a.replace("{prompt}", prompt) for a in use], work, log, 30)
got = open(seen, encoding="utf-8").read() if os.path.isfile(seen) else ""
check("the fake provider ran one fresh turn", rc == 0 and not timed_out
      and use == spec["headless_first"])
check("and that turn is the revision, not the lesson",
      "[revise]" in got and "NOT PART OF THE LESSON" in got)
check("and it is told to rebuild the manuscript with board build",
      "`board build paper1-trd-prediction/manuscript.md`" in got)

print()
if fails:
    print("%d FAILURES" % len(fails))
    sys.exit(1)
print("a revision changes the document and a ship pushes one, and neither is "
      "part of the lesson")
