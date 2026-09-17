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

import importlib.machinery
import importlib.util
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tutorboard import atlas, manuscript, sense
from tutorboard.course import library

_tl = importlib.machinery.SourceFileLoader("tutorcli", os.path.join(ROOT, "bin", "tutor"))
tutorcli = importlib.util.module_from_spec(
    importlib.util.spec_from_loader("tutorcli", _tl))
_tl.exec_module(tutorcli)

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
      tutorcli.turn_signal("[2026-09-16 18:02:11] [revise] the document is x")
      == "revise")

for carried in (0, 1, 7, 40):
    use, template, fresh = tutorcli.turn_plan(SPEC, carried, 12, "revise")
    check("a revision runs fresh with %d turn(s) there to resume" % carried,
          fresh is True and use == SPEC["headless_first"]
          and template is tutorcli.HEADLESS_REVISE_PROMPT)

use, template, fresh = tutorcli.turn_plan(SPEC, 3, 12)
check("while an ordinary turn still resumes the lesson",
      fresh is False and use == SPEC["headless"]
      and template is tutorcli.HEADLESS_RESUME_PROMPT)

# THE ONE THAT ONLY SHOWS UP A TURN LATER. The revision's session is now the
# agent's current conversation, and `--continue` would put the next card of the
# lesson inside it.
check("the lesson does not resume into the revision's session",
      tutorcli.carry_after("revise", True, 6) == 0)
check("and an ordinary turn still carries what it carried",
      tutorcli.carry_after("", False, 6) == 7
      and tutorcli.carry_after("", True, 6) == 1)

# ---------------------------------------------------------------------------
# what that turn is told
# ---------------------------------------------------------------------------
said = tutorcli.HEADLESS_REVISE_PROMPT
check("it is told this turn is not part of the lesson",
      "NOT PART OF THE LESSON" in said)
check("and to write no card, in as many words", "Write no card" in said)
for name in ("board write", "board open", "live/state.json", "live/cards/",
             "HANDOFF.md", "board wait"):
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
      tutorcli.turn_signal("[2026-09-17 20:10:00] [rework] the deck is for x")
      == "rework")
for carried in (0, 1, 7, 40):
    use, template, fresh = tutorcli.turn_plan(SPEC, carried, 12, "rework")
    check("an overhaul runs fresh with %d turn(s) there to resume" % carried,
          fresh is True and use == SPEC["headless_first"]
          and template is tutorcli.HEADLESS_REWORK_PROMPT)
check("and the lesson does not resume into the overhaul's session",
      tutorcli.carry_after("rework", True, 6) == 0)

# A DOING TURN'S CLOCK, and a plain revision deliberately does not get one: a
# correction changes what a note names and is over in a minute, while an
# overhaul rewrites thirty-three pages and runs LaTeX at the end of it.
CLOCK = {"headless_timeout": 900, "doing_timeout": 3600}
_empty = tempfile.mkdtemp()
check("an overhaul gets a doing turn's time, whatever the sitting says",
      tutorcli.turn_timeout(CLOCK, _empty, None, "rework") == 3600)
check("while a correction is left on the sitting's own clock",
      tutorcli.turn_timeout(CLOCK, _empty, None, "revise") == 900)

worked = tutorcli.HEADLESS_REWORK_PROMPT
check("an overhaul is told this turn is not part of the lesson",
      "NOT PART OF THE LESSON" in worked)
check("and to write no card", "Write no card" in worked)
for name in ("board write", "board open", "live/state.json", "live/cards/",
             "HANDOFF.md", "board wait"):
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
      "NOT PART OF THE LESSON" in line and "live/cards/" in line)

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
      tutorcli.turn_signal("[2026-09-17 21:40:02] [ship] a mission finished")
      == "ship")
for carried in (0, 1, 7, 40):
    use, template, fresh = tutorcli.turn_plan(SPEC, carried, 12, "ship")
    check("a ship runs fresh with %d turn(s) there to resume" % carried,
          fresh is True and use == SPEC["headless_first"]
          and template is tutorcli.HEADLESS_SHIP_PROMPT)
check("and the lesson does not resume into the ship's session either",
      tutorcli.carry_after("ship", True, 6) == 0)

shipped = tutorcli.HEADLESS_SHIP_PROMPT
check("a ship is told this turn is not part of the lesson",
      "NOT PART OF THE LESSON" in shipped)
check("and to write no card", "Write no card" in shipped)
for name in ("board write", "board open", "live/state.json", "live/cards/",
             "HANDOFF.md", "board wait"):
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
      tutorcli.turn_timeout(CFG, tempfile.mkdtemp(), None, "ship") == 3600)

said = sense.ship_sense("colibri", "reproduce the corrected transcript")
check("the line a ship is woken with names what the mission was asked to do",
      "reproduce the corrected transcript" in said)
check("and who did the work, which is the whole reason it is not them pushing",
      "colibri" in said and "not the assistant that made them" in said)
check("and says the lesson on the board is somebody else's",
      "NOT PART OF THE LESSON" in said and "live/cards/" in said)

line = sense.revise_sense("writeups/serve/serve.tex",
                          "writeups/serve/feedback/2026-09-16-v1.md")
check("the line it is woken with names the document",
      "writeups/serve/serve.tex" in line)
check("and the feedback file", "writeups/serve/feedback/2026-09-16-v1.md" in line)
check("and says the lesson on the board is somebody else's",
      "NOT PART OF THE LESSON" in line and "live/cards/" in line)

# ---------------------------------------------------------------------------
# the other kind, which the board does not revise itself
# ---------------------------------------------------------------------------
tmp = tempfile.mkdtemp(prefix="tutor-revising-")
os.makedirs(os.path.join(tmp, "projects", "Paper-Writer"), exist_ok=True)
with open(os.path.join(tmp, "atlas.json"), "w", encoding="utf-8") as fh:
    json.dump({"families": [{"id": "projects", "name": "Projects"},
                            {"id": "research", "name": "Research"}]}, fh)
with open(os.path.join(tmp, "projects", "Paper-Writer", "tutorboard.json"), "w",
          encoding="utf-8") as fh:
    json.dump({"name": "Paper-Writer"}, fh)
work = os.path.join(tmp, "research", "Trial")
os.makedirs(os.path.join(work, "manuscripts", "feedback"))
with open(os.path.join(work, "tutorboard.json"), "w", encoding="utf-8") as fh:
    json.dump({"name": "Trial"}, fh)
with open(os.path.join(work, "manuscripts", "manuscript.md"), "w",
          encoding="utf-8") as fh:
    fh.write("# A delivered manuscript\n")
note = os.path.join("manuscripts", "feedback", "manuscript-2026-09-16-v1.md")
with open(os.path.join(work, note), "w", encoding="utf-8") as fh:
    fh.write("# Feedback\n\nSection 3 reports the wrong split.\n")

os.environ["TUTORBOARD_COURSES"] = tmp
atlas.forget()
library.forget()

out = manuscript.revise(work, {"title": "A delivered manuscript",
                               "rel": "manuscripts/manuscript.md"},
                        note, base=tmp, dry_run=True)
body = out.get("markdown") or ""
check("a revision job is assembled rather than refused", out.get("ok") is True)
check("it carries a Revision section, which a new paper's job does not",
      manuscript.REVISION in body
      and manuscript.REVISION not in manuscript.job(work))
check("the section names the delivered document",
      "document: manuscripts/manuscript.md" in body)
check("and the feedback file", "feedback: %s" % note in body)
check("it says the existing document stands except where the feedback says not",
      "Revise it" in body and "different paper" in body)
check("their words are in the job as well, where every parser reads",
      "wrong split" in body)
check("and the feedback file is not listed as prose to preserve",
      note not in body.split(manuscript.REVISION)[-1].split("Manuscript prose")[-1])
check("a revision with no document named is refused rather than guessed at",
      manuscript.revise(work, {"title": "x", "rel": ""}, note,
                        base=tmp, dry_run=True).get("ok") is False)

# WHICH ROOT THOSE PATHS ARE RELATIVE TO. The factory is another workspace with its
# own state directory, and it cannot resolve `manuscripts/manuscript.md` against a
# root nobody named.
check("the job names the workspace the two paths are relative to",
      "workspace: %s" % os.path.realpath(work) in body)

# AND IT NAMES THE SOURCE, NOT THE RENDERING. `library.py` sets `rel` to the PDF
# wherever there is one, because `rel` is what goes on the glass -- and a revision
# pointed at a PDF is a revision asked to edit a picture of the document.
built = manuscript.revise(work, {"title": "A delivered manuscript",
                                 "source": "manuscripts/manuscript.md",
                                 "rel": "manuscripts/manuscript.pdf"},
                          note, base=tmp, dry_run=True).get("markdown") or ""
check("a document with a PDF beside it is revised by its source",
      "document: manuscripts/manuscript.md" in built
      and "document: manuscripts/manuscript.pdf" not in built)

# AND AN EXPLAINER IS NOT ROUTED THROUGH THE FACTORY. It is a manuscript factory
# with gates for venue, claims, citations and a reporting checklist; "how the
# serve harness works" has no venue and makes no claims, and every one of those
# gates would either refuse it or invent something to satisfy itself.
os.makedirs(os.path.join(work, "writeups", "serve-harness"))
with open(os.path.join(work, "writeups", "serve-harness", "serve-harness.tex"),
          "w", encoding="utf-8") as fh:
    fh.write("\\documentclass{article}\n\\title{How the serve harness works}\n")
with open(os.path.join(work, "writeups", "serve-harness", "serve-harness.pdf"),
          "w", encoding="utf-8") as fh:
    fh.write("x" * 30000)
library.forget()
made = {d["title"]: d["made"] for d in library.documents(work)}
check("a board-made explainer is the board's to revise",
      made.get("How the serve harness works") == "board")
src = {d["title"]: (d.get("source"), d["rel"]) for d in library.documents(work)}
check("and a document carries its source beside the file the glass draws",
      src.get("How the serve harness works")
      == ("writeups/serve-harness/serve-harness.tex",
          "writeups/serve-harness/serve-harness.pdf"))
check("and a delivered manuscript is the factory's",
      made.get("A delivered manuscript") == "paper-writer")

# The other half of the seam, which lives in Paper-Writer's own repository. It is
# checked when it is there, and said plainly when it is not, rather than making
# this suite depend on another workspace being checked out.
template = os.path.join(os.path.dirname(ROOT), "projects", "Paper-Writer",
                        "PROMPT_TEMPLATE.md")
if os.path.isfile(template):
    text = open(template, encoding="utf-8").read()
    check("the template names a revision section for the board to fill in",
          manuscript.REVISION in text)
    check("and says to leave it out for a new paper",
          "LEAVE THIS OUT FOR A NEW PAPER" in text)
    check("and asks for the workspace those paths are relative to",
          "workspace:" in text)
    check("and says the document named is the source rather than a built format",
          "never a .docx" in text)
    check("the template names a delivery section for the landing to go in",
          manuscript.DELIVERY in text)
    check("and asks for it absolutely, because the factory is another repository",
          "ABSOLUTE" in text and "landing:" in text)
else:
    print("ok   (Paper-Writer is not checked out here; its template is not read)")

# BOTH SIDES OF THE SEAM, AGAINST EACH OTHER. The board writes a job and the
# factory parses one, and until this ran the only thing checked was that each of
# them was self-consistent -- which is how a field gets written in one spelling
# and read in another for a month without anybody noticing. Skipped where the
# factory is not checked out, rather than making this suite depend on it.
writer = os.path.join(os.path.dirname(ROOT), "projects", "Paper-Writer")
if os.path.isdir(os.path.join(writer, "paperwriter")):
    sys.path.insert(0, writer)
    from paperwriter import jobspec as pw_jobspec              # noqa: E402

    spec = pw_jobspec.revision(body)
    check("the factory reads the document out of the job the board wrote",
          spec.get("document") == "manuscripts/manuscript.md")
    check("and the feedback file", spec.get("feedback") == note)
    check("and the workspace those two are relative to",
          spec.get("workspace") == os.path.realpath(work))
    check("so the two of them resolve to the file on disk",
          os.path.isfile(os.path.join(spec["workspace"], spec["document"])))
    check("and a job for a NEW paper is read as one, which is what makes the "
          "section the signal",
          pw_jobspec.revision(manuscript.job(work)) == {})

    # AND THE LANDING, the same way. A sentence of prose said this for months and
    # nothing read it, so every delivered paper stopped in the factory's own
    # out-directory and no workspace ever saw one.
    check("the factory reads the landing out of the job the board wrote",
          pw_jobspec.landing(body)
          == os.path.join(os.path.realpath(work), manuscript.LANDING))
    check("and it is absolute, so the factory can resolve it from its own root",
          os.path.isabs(pw_jobspec.landing(body)))
    check("a revision lands in the corrected document's own directory, so the "
          "correction replaces it rather than sitting beside it",
          pw_jobspec.landing(body)
          == os.path.dirname(os.path.join(os.path.realpath(work),
                                          "manuscripts", "manuscript.md")))
    check("a new paper's job names a landing too -- it is not the revision signal",
          pw_jobspec.landing(manuscript.job(work)).startswith(
              os.path.join(os.path.realpath(work), manuscript.LANDING)))
    sys.path.remove(writer)
else:
    print("ok   (Paper-Writer is not checked out here; its parser is not run)")

print()
if fails:
    print("%d FAILURES" % len(fails))
    sys.exit(1)
print("a revision changes the document and a ship pushes one, and neither is "
      "part of the lesson")
