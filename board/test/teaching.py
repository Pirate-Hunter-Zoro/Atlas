#!/usr/bin/env python3
"""The teaching method ships with the board, not with the course.

The same document pasted into a dozen `AI_INSTRUCTIONS.md` files goes out of step
one repository at a time, and the one that drifts is the one you notice last. So
`TEACHING.md` lives here and is copied into every course's `live/` on every
`board start`, and every path that briefs an assistant points at it.

ONE document, delivered WHOLE. It used to be filtered: sections carried
`<!-- mode: math -->` or `<!-- mode: code -->` and a repository was handed
whichever half its declared mode selected. The mode is gone, so the filter is
gone with it -- and the sections about a repository that follows no book now go
to everybody, because most repositories are one and nothing declares which.

What is guarded is the delivery and the rules that a real sitting turned out to
depend on -- exercises first, a chosen few rather than all of them, one question
per turn, and a skip that is obeyed rather than argued with.
"""

import importlib.machinery
import importlib.util
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

loader = importlib.machinery.SourceFileLoader("boardcli", os.path.join(ROOT, "bin", "board"))
spec = importlib.util.spec_from_loader("boardcli", loader)
boardcli = importlib.util.module_from_spec(spec)
loader.exec_module(boardcli)

fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


METHOD = os.path.join(ROOT, "TEACHING.md")
check("the method ships with the board", os.path.isfile(METHOD))
text = open(METHOD, encoding="utf-8").read() if os.path.isfile(METHOD) else ""

# The rules the sitting actually turned on. Each of these was a thing the tutor
# got wrong before it was written down.
for phrase, why in [
    ("exercises", "the lesson is aimed at the section's exercises"),
    ("Not all of them", "a chosen few, not the whole exercise list"),
    ("skip", "a declined prompt is obeyed"),
    ("one question", "one question per turn"),
    ("HANDOFF.md", "the session ends in writing"),
    ("Write the card before", "the card lands before the turn's other work"),
    ("board hw", "an agreed answer is typeset into the course's own file"),
    # THE QUESTION IS THE LAST THING ON THE CARD. Reported from the iPad: "I've
    # got a board to write on and have to scroll up to see the question again."
    # The definition list sits between the statement and the answer block, so a
    # card that asks once at the top asks it six lines above where the pen is.
    ("Then ask it again", "a posing card closes by restating the question"),
    ("last line of the card", "and that restatement is the last thing on it"),
    ("pointer", "a pointer back to the statement is not a restatement"),
    # PROBLEM BY PROBLEM. The rule was always "in the same turn"; what was
    # missing is that batching is the same defect in smaller units.
    ("Problem by problem", "the write-up happens problem by problem"),
    ("next problem is posed",
     "and is compiled before the next problem is posed"),
    ("Batching", "so three worked and one transcription pass is refused too"),
    ("board finish", "the session ends by offering the push"),
    ("assignment sheet", "a homework sitting reads the sheet it was set"),
    ("not yours", "and does not choose its own problems there"),
    # A skip means two different things and reading it the lecture way in a
    # homework sitting quietly shortens the sheet. The problems are assigned:
    # tapping past one chooses an order, and an unanswered one is a lost mark.
    ("not now", "a skipped homework problem is deferred, not dropped"),
    ("come back to it once the others are done",
     "and is returned to when the rest of the sheet is done"),
    ("only one left", "and comes straight back if it is the last one standing"),
    # The student works the sheet in whatever order suits them; the document is
    # not theirs to reorder. Answering 4 before 2 must not put 4 above 2 on the
    # page, which is what appending as you go does.
    ("skeleton in order", "the document's order is fixed before anything fills it"),
    ("order regardless",
     "so the write-up reads in the assignment's order, not the answering order"),
    # Revising for a test inverts the homework rule: the student chose the
    # scope, and inside it the questions are the tutor's. Both halves have to be
    # written down, because the failure in either direction is silent -- a tutor
    # that asks outside the scope wastes the evening, and one that treats the
    # scope as a syllabus teaches it instead of testing it.
    ("test review", "a test review is a sitting of its own"),
    ("Do not widen the scope", "and its scope is not the tutor's to widen"),
    ("Spread the questions", "and the questions are spread across all of it"),
    ("no write-up", "and nothing is transcribed or compiled for a review"),
    # THE CARD-FIRST RULE IS A TEACHING TURN'S RULE, and it used to say it was
    # absolute -- "there is no exception to this, and nothing else in this file
    # overrides it". In a turn that DOES the work rather than teaching it, that
    # ordering produces a card describing an intention and no work at all, which
    # is what came back the first time somebody tapped "write the code for me":
    # a four-hundred-word plan, a list of what had not been done, and a question.
    # Both halves are checked, because either one alone is the old defect.
    ("write the\ncard first and let it land", "a teaching turn gets its card up first"),
    ("This is a teaching turn's rule",
     "and it says which kind of turn that is a rule for"),
    ("A doing turn: the work first", "a turn that does the work inverts the order"),
    ("board write --over",
     "and reports over the sentence it opened with, so one card carries the truth"),
    ("Never hand back a plan of what you would do",
     "a plan handed back as though it were the work is named as the failure it is"),
    ("do the **first part of it**",
     "and a job too big for one turn is half done rather than all described"),
    # Every card, in every sitting. Asked for after one that was correct and
    # unreadable: "the tutor should ALWAYS give me easy to understand responses."
    ("Say it plainly", "every card is written to be understood the first time"),
    ("The answer is the first sentence", "with the answer in the first sentence"),
    ("One idea per sentence", "one idea to a sentence"),
    ("Spell out every piece of shorthand",
     "and no shorthand left unexplained the first time it appears"),
    ("read a sentence twice", "and a sentence that has to be read twice is wrong"),
    ("Never label a question", "a question is answered, not graded"),
    ("do not know how to start", "and not knowing where to start is a real answer"),
    ("has not produced", "no solution is invented for the student"),
    # THE WRITE-UP IS THE TUTOR'S, AND SO IS THE SENTENCE ABOUT IT. The act was
    # already governed -- a whole section says every sitting produces a compiled
    # document and the tutor transcribes it -- and the card still said "two words
    # to add when you write it up". Nothing forbade addressing the student as the
    # person who would write something, so an errand that does not exist was
    # handed over. The worse half is in the same clause: the missing word was
    # `non-zero`, which is a fact about the proof, so the fix was deferred onto
    # somebody who was never going to make it.
    ("never tells them to write anything up",
     "no card hands the write-up back to the student"),
    ("when you write it up",
     "and the phrase that did it is quoted, so it is recognisable"),
    ("made in the write-up, in the\nsame turn",
     "a correction belonging in the document is made there, that turn"),
    ("Never tell them to write, typeset, transcribe or add to anything",
     "and the sentence-level half sits with the other sentence-level rules"),
    # A concept that has only been read is not one the student can use, and the
    # exercise is a bad place to discover that. Found the hard way: a card taught
    # cosets, the index and normality, then went straight to the exercise.
    ("hand-check", "every concept is worked by the student before the exercise"),
    ("One concept per check", "one concept per check, not three in one card"),
    ("Tiny", "a check is small enough to answer at once"),
    ("can be skipped", "and a check can be declined like any other prompt"),
    # And then the half that was missing: the checks are not a supplement to the
    # explaining, they ARE the explaining. A model handed a chapter and told to
    # teach writes a lecture, because that is what teaching looks like in
    # everything it has ever read. So the shape is stated outright and first.
    ("exercises, all the way down", "a lesson is exercises and nothing else"),
    ("no explaining step that", "with no explaining step that stands on its own"),
    ("There is no worked-example card", "and no card that only demonstrates"),
    ("You bring the objects; they do the showing",
     "the tutor supplies the objects and the student shows what they are"),
    ("non-example", "and a non-example is how a definition gets fixed"),
    ("ladder is as short as it can possibly be",
     "only what the exercise needs is taught, and nothing else is"),
    ("Re-pose the exercise", "the exercise comes back after the ladder"),
    ("is not a re-pose", "restated in full, because a reference is not a re-pose"),
    ("measure of a sitting is how many exercises got answered",
     "and a sitting is measured in exercises answered"),
    # A review is the one sitting that must NOT ladder before the question --
    # laddering first would tell you only that they can follow a ladder.
    ("ladder comes after the break", "a review asks cold and ladders from a break"),
    # Asked for from the board, mid-proof: "I don't want to have to scroll back
    # to understand exactly what I'm trying to prove." A statement on its own is
    # not the whole question -- the definitions it leans on are part of it.
    ("self-contained", "a card that poses a problem is self-contained"),
    ("every definition, symbol and named result",
     "and carries every definition the statement uses"),
    ("scroll back", "so nothing has to be hunted for up the transcript"),
    ("Include the ones from the rungs",
     "including the ones from checks that were skipped"),
    # A repository that follows no book used to be a different MODE, with a
    # different method and a different board. What is left is where the
    # exercises come from -- and that has to be said, because a first card on a
    # repository with no chapters once opened with "Which chapter this is",
    # invented an order out of the README's headings, and taught a lesson nobody
    # asked for while the actual task list sat unread in another repository.
    ("not a course", "a project is not a course"),
    ("method does not change between the two",
     "and is taught by the same method regardless"),
    ("where they come from", "with only the source of the exercises differing"),
    ("Do not manufacture a curriculum", "and no curriculum is invented for it"),
    # The tutor used to be told to read the README and follow what it points at.
    # It still must not choose its own work -- but it no longer goes looking:
    # the briefing names the plan and quotes its steps, so what is asserted here
    # is that the plan still OUTRANKS the tutor, which was always the point.
    ("names that file", "the briefing names the plan rather than sending the tutor to find it"),
    ("outranks anything you would have chosen",
     "and the plan outranks anything the tutor would have picked"),
    ("labelled\nwith", "and the sitting's label says which step to open"),
    ("do not choose an agenda", "and asks rather than choosing its own work"),
    ("goes with a commit", "and finishing work includes writing it down"),
    ("go and look", "a turn saying it is implemented sends the tutor to the code"),
    ("no button for this", "and there is no tap that stands in for saying so"),
    # Not every project wants a tutor. One line of configuration, and the tutor
    # does the work instead of setting it -- without any of the rest of a turn
    # changing, which is why it is a line of configuration and not a mode.
    ('"stance": "do"', "a repository can ask for the work to be done, not taught"),
    ("declared, never inferred", "and that is never guessed at"),
    ("still one card, still short", "a doing turn is still one short card first"),
    ("say what you did not verify", "and says what it has not actually run"),
]:
    check("the method states: " + why, phrase.lower() in text.lower())

# Front-loading is the failure it exists to prevent.
check("and it forbids the survey-then-ask shape outright",
      "front-load" in text.lower() or "Front-loading" in text)

# --- delivery -----------------------------------------------------------------
tmp = tempfile.mkdtemp(prefix="tutor-teaching-")
try:
    import json  # noqa: E402
    # A course file still carrying the old `mode` key, because the course
    # repositories are not this one and nobody is going to edit nine of them.
    # It must make no difference to what is delivered.
    with open(os.path.join(tmp, "tutorboard.json"), "w", encoding="utf-8") as fh:
        json.dump({"name": "T", "mode": "code"}, fh)
    live = boardcli.Live(tmp)
    dest = boardcli.install_teaching(live)
    check("starting a board puts it in the course's live/", bool(dest) and os.path.isfile(dest))

    delivered = open(dest, encoding="utf-8").read() if dest else ""
    check("and what lands there is the whole document, byte for byte",
          delivered == text)
    check("a stale 'mode' in the course's own file changes nothing",
          delivered == text)

    # There is no filter left to get wrong. `for_mode` selected sections by mode
    # and it is gone; the failure it used to risk -- a tutor teaching with half a
    # method -- is now unreachable rather than guarded.
    check("there is no mode filter any more", not hasattr(boardcli, "for_mode"))
    check("and nothing guesses a subject either",
          not hasattr(boardcli, "guess_mode"))
    check("nothing in the method is tagged for one kind of repository",
          "<!-- mode:" not in text.replace("`<!-- mode:", ""))

    # The sections that used to be delivered to one half each now go to both,
    # and that is the whole point: most repositories follow no book, and the
    # tutor cannot be told which after the first card is written.
    for section, why in [
        ("A section, from start to finish", "how an exercise is posed"),
        ("A homework sitting", "the homework rules"),
        ("A test review", "the review rules"),
        ("An agreed answer gets written up", "the write-up"),
        ("A repository that is not a book", "where exercises come from without one"),
        ("When the repository says DO rather than TEACH", "the doing stance"),
        ("Write the card before you do anything else", "and the card-first rule"),
    ]:
        check("every course is given " + why, section in delivered)

    # It is a delivery, not an edit to the course: live/ is ignored by git.
    check("it lands under live/, which no course commits",
          bool(dest) and os.path.basename(os.path.dirname(dest)) == "live")

    # Delivered again on the next start, so a stale copy cannot survive an edit.
    open(dest, "w", encoding="utf-8").write("something older")
    boardcli.install_teaching(live)
    check("a stale copy is replaced on the next start",
          open(dest, encoding="utf-8").read() == text)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# --- every path that briefs an assistant has to point at it -------------------
tutor_src = open(os.path.join(ROOT, "bin", "tutor"), encoding="utf-8").read()
check("the session brief points at it", "live/TEACHING.md" in tutor_src)
check("the headless prompt points at it too",
      tutor_src.count("TEACHING.md") >= 3)

serve_src = open(os.path.join(ROOT, "tutorboard", "sense.py"),
                 encoding="utf-8").read()
# In a headless session the begin line IS the prompt, so it carries the pointer.
check("and so does the cold start, which in headless is the whole prompt",
      "TEACHING.md" in serve_src)

# The pointer is not enough on its own. In headless the sense line IS the whole
# prompt, and a tutor that reads "teach what the exercise needs" without the
# shape attached writes a lecture and asks at the bottom of it. So every sitting
# carries the shape, and it carries the SAME one -- one paragraph, hoisted.
# AS A MODULE OF ITS PACKAGE, and that matters more than it looks. This used to
# load `sense.py` by path under a name of its own, which cannot resolve the
# relative imports at the top of it -- so the load raised, `serveapp` became
# None, a note was printed, and EVERY check below this line was silently
# skipped. A suite that says "ok" for a block it did not run is worse than one
# that has no block, and it stayed that way long enough for the shape of the
# headless prompt to be unguarded.
sys.path.insert(0, ROOT)
from tutorboard import sense as serveapp                     # noqa: E402

sense = serveapp.METHOD_SENSE
if serveapp:
    for phrase, why in [
        ("LESSON IS", "the sense line says the lesson is exercises"),
        ("EXERCISES", "in the word the tutor cannot read past"),
        ("state the exercise in full", "the exercise is stated in full first"),
        ("ONE tiny thing", "then one small thing at a time"),
        ("RESTATED IN FULL", "and the exercise is restated in full at the end"),
        ("not a re-pose", "a reference to it is not a re-pose"),
        ("self-contained", "every posing card is self-contained"),
        ("scroll back", "so nothing has to be hunted for up the transcript"),
        ("One question per turn", "one question per turn"),
        ("THEN ASK IT AGAIN", "and the question is asked again under the list"),
        ("LAST thing on the card", "so it is the last thing above the board"),
    ]:
        check("the headless prompt " + why, phrase in sense)

    # THE WRITE-UP, IN THE PROMPT AND NOT ONLY IN THE DOCUMENT. `TEACHING.md`
    # has said "in the same turn" since it was written, and in a headless
    # session that is a file the tutor may or may not open while this string is
    # the whole prompt -- which is how a sitting worked five problems and
    # compiled nothing.
    for phrase, why in [
        ("TURN THAT AGREES AN ANSWER", "the write-up is part of that turn"),
        ("before you pose the next one", "and lands before the next problem"),
        ("board hw build", "it is compiled, by name"),
        ("COMPILING IS YOURS", "and compiling is the tutor's job, not theirs"),
        ("never leave the write-up for the end",
         "and it is never left to the end of the sitting"),
        # A phrasing rule cannot honestly be unit-tested against a real card,
        # and a test that pretended to would be a test of nothing. What is
        # checkable is that the rule reaches the turn: in headless this string
        # IS the prompt, and the document beside it is a file the tutor may or
        # may not open.
        ("NEVER TELL THEM TO WRITE IT UP",
         "and the student is never told to write it up"),
        ("what the file NOW SAYS",
         "the card reports the document rather than handing over an errand"),
        ("make it in the write-up in this same turn",
         "and a correction that belongs there is made there, in that turn"),
    ]:
        check("the headless prompt " + why, phrase in serveapp.WRITEUP_SENSE)
    check("every sitting that hands something in is told to write it up",
          "how += WRITEUP_SENSE" in serve_src)
    # The two that hand nothing in say so themselves, and must not be told to
    # transcribe: a review is rehearsal and a walkthrough reads code that is
    # already written.
    check("and the two that hand nothing in are not",
          "no write-up" in serveapp.WALK_SENSE
          and "WRITEUP_SENSE" not in serveapp.WALK_SENSE)
    check("and every kind of sitting is given the same shape",
          serve_src.count("METHOD_SENSE") >= 4)
    # A review inverts one thing and only one: it asks before it teaches.
    check("except a review, which asks cold and ladders from the break",
          "asks COLD" in serve_src and "Ladder only from a break" in serve_src)
    # A skipped check is a rung, so the skip has somewhere to go next.
    check("a skipped check moves to the next rung, or to the exercise",
          "hand-check" in serveapp.SIGNAL_SENSE["skip"]
          and "restated in full" in serveapp.SIGNAL_SENSE["skip"])



board_src = open(os.path.join(ROOT, "bin", "board"), encoding="utf-8").read()
check("board start installs it rather than assuming it is there",
      "install_teaching(live)" in board_src)


# ---------------------------------------------------------------------------
# THE TURN THAT DOES THE WORK
# ---------------------------------------------------------------------------
# A person tapped "write the code for me" on the map and got a plan, a list of
# what had not been done, and a question -- no code. The contract is why: it
# says, three times, that the card is written before anything else happens, and
# in a doing turn that means the card can only describe an intention.
#
# The document half is checked above. This is the half a document cannot hold:
# that the turn is actually TOLD, in the line it is woken with, and that there is
# a way to replace an opening sentence with a report once the work is done.
from tutorboard import sense as sense_mod                   # noqa: E402
from tutorboard.course import config as course_config        # noqa: E402

# A DOCUMENT IS ABOUT THE SUBJECT, NOT ABOUT THE SITTING.
#
# Everything else in the make method is about HOW to work -- sections, show each
# one, take the corrections -- and it said nothing about what the document IS. A
# tutor that has just spent three hours teaching, asked to write it up, writes up
# the three hours. It is a refusal rather than a preference, and it has to hold in
# three places that must not drift: the method a turn is given, the one sentence
# behind the word a person taps, and the contract copied into every workspace.
for phrase, why in [
    ("EXPLAINER", "the document is named as an explainer"),
    ("was not in the room", "written for somebody who was not there"),
    ("no first person", "with no first person"),
    ("narrate the hand-check", "and no narration of how it was taught"),
    ("writeups/", "and kept where a document goes"),
]:
    check("the make method says " + why, phrase in sense_mod.MAKE_SENSE)
for _aim in ("paper", "slides"):
    _said = course_config.AIM_MEANS[_aim]
    check("the word a person taps for %s says it too" % _aim,
          "explainer" in _said.lower() or "explains" in _said.lower())

# TWO SENTENCES WERE WELDED INTO ONE REFUSAL, AND ONLY ONE OF THEM WAS RIGHT.
#
# The failure it was written against was a tutor narrating the evening it had
# just taught -- first person, "as we saw above", the hand-check retold instead
# of the concept explained. That is about CONTENT and the refusal is correct.
#
# What got banned alongside it is SCOPE: "AND ITS SCOPE IS THE BOX, NOT THE
# EVENING". So *"a deck about the four things this sitting covered"* -- which is
# the ask `POST /writeup` exists for -- had no phrasing anywhere that the rule
# did not refuse. The two are separated now, and BOTH halves have to hold in all
# four places, because two of the four worded the old refusal differently and
# that is exactly how a rule gets fixed in one and left in the other.
WHERE_THE_RULE_LIVES = (
    ("the make method", sense_mod.MAKE_SENSE),
    ("the word a person taps for a paper", course_config.AIM_MEANS["paper"]),
    ("the word a person taps for a deck", course_config.AIM_MEANS["slides"]),
    ("TEACHING.md", text),
)
for _where, _said in WHERE_THE_RULE_LIVES:
    check("%s still refuses a narration of the sitting" % _where,
          "narration of this sitting" in _said.lower())
    check("%s allows the evening as a scope" % _where,
          "the concepts this sitting covered" in _said)
# And the scope half says what the evening MEANS, in the two places a turn reads:
# the concepts, read back in one call, not the order or the questions or who got
# what wrong.
for phrase, why in [
    ("THE BOX, THE CHAPTER, OR THE WHOLE EVENING", "all three scopes are named"),
    ("board recap --all", "the lesson is read back in one call"),
    ("not the questions", "and the questions are not the document"),
]:
    check("the make method says " + why, phrase in sense_mod.MAKE_SENSE)
for phrase, why in [
    ("about the SUBJECT", "the contract says the same"),
    ("was not in the room", "for somebody who was not there"),
    ("refusal", "and says it is a refusal rather than a preference"),
    ("writeups/", "and names where a new document goes"),
    ("board recap --all", "and how the evening is read back"),
]:
    check("TEACHING.md: " + why, phrase in text)

# ---------------------------------------------------------------------------
# A DOCUMENT IS A PRODUCT, NOT AN AIM
# ---------------------------------------------------------------------------
# Asked for from any sitting at all, including the two the aim row is withheld
# from. The route is guarded in `test/aiming.py`; what is guarded here is the
# line the turn is woken with, because in headless that string IS the prompt.
for _makes, _word in (("paper", "a PAPER"), ("slides", "a DECK of slides")):
    _line = sense_mod.writeup_sense(_makes)
    check("a %s asked for mid-sitting says which product it is" % _makes,
          _word in _line)
    check("and carries the make method whole rather than restating it (%s)" % _makes,
          sense_mod.MAKE_SENSE in _line)
    check("and says the turn writes no card (%s)" % _makes,
          "Write no card" in _line and "THIS TURN IS NOT PART OF THE LESSON" in _line)
    check("and that the sitting's own aim has not changed (%s)" % _makes,
          "aim of it has not changed" in _line)
    # The scope with nobody naming one is the evening, which is the whole reason
    # this route exists: the map already opens a make sitting over a box.
    check("with the evening as its scope where nobody named one (%s)" % _makes,
          "THE CONCEPTS THIS SITTING COVERED" in _line
          and "board recap --all" in _line)
    _named = sense_mod.writeup_sense(_makes, "the serve harness")
    check("and what they said it was about where they said anything (%s)" % _makes,
          "the serve harness" in _named
          and "THE CONCEPTS THIS SITTING COVERED" not in _named)

from tutorboard.course import config as config_mod          # noqa: E402
from tutorboard.course.repo import Repo                      # noqa: E402

check("there is a clause telling a turn to do the work before it reports",
      "DOING TURN" in sense_mod.DOING_SENSE
      and "board write --over" in sense_mod.DOING_SENSE)
check("and it says outright that it overrides the card-first rule",
      "TEACHING.md" in sense_mod.DOING_SENSE
      and "opposite" in sense_mod.DOING_SENSE.lower())
check("a plan handed back instead of the work is named as the failure",
      "Never hand back a plan" in sense_mod.DOING_SENSE)
check("and a question is not how a doing turn ends by default",
      "not how a doing turn ends" in sense_mod.DOING_SENSE)

# ---------------------------------------------------------------------------
# ONE MODULE, ONE JOB -- and it has to say the same thing in both places
# ---------------------------------------------------------------------------
# A standing rule about the code a doing turn writes, not a task. The reason it
# is guarded here is that it is written down TWICE: in `TEACHING.md`, which the
# tutor reads, and in `DOING_SENSE`, which in a headless turn IS the whole
# prompt and is the only one of the two a wakened turn is guaranteed to see. A
# rule fixed in one and left in the other is the failure this file exists for.
# Both documents wrap their prose, so a sentence in either one has newlines
# through it. Compared with the whitespace flattened and the case dropped: what
# has to agree is the RULE, not how a paragraph happened to be filled.
def _flat(said):
    return " ".join(str(said or "").lower().split())


_METHOD, _DOING = _flat(text), _flat(sense_mod.DOING_SENSE)
ONE_JOB = (
    ("a new thing goes in a module named for the one job it does",
     "the rule itself, in one sentence"),
    ("move it first",
     "and moving what is in the way is part of it rather than a later tidy-up"),
    ("mirror",
     "the reason: the diagram is drawn from the code, so it reflects it"),
    ("the failure is the module",
     "and an unreadable box is the module's fault, not the renderer's"),
    ("getting away with it is not the test",
     "and that Python letting you get away with it settles nothing"),
)
for _phrase, _why in ONE_JOB:
    check("TEACHING.md says " + _why, _phrase in _METHOD)
    check("and a doing turn is told the same: " + _why, _phrase in _DOING)
check("the rule names the four words that mean nobody decided",
      all(w in _METHOD and w in _DOING
          for w in ("helpers", "utils", "common", "misc")))
check("a doing turn is pointed at the section rather than handed a paraphrase "
      "of it", "where a new thing goes" in _DOING
      and "## where a new thing goes" in _METHOD)
# ---------------------------------------------------------------------------
# A COMPONENT BOUNDARY IS A STOPPING POINT -- in both places, again
# ---------------------------------------------------------------------------
# The same two-places problem as *one module, one job*, and for the same reason:
# a tutor with the document open reads `TEACHING.md`, and a headless turn reads
# `node_sense` and nothing else. This rule is about what to do when the work
# LEAVES the box -- which is the honest case the old focus line said nothing
# about. It only said not to WANDER: not to pick an agenda outside the box. The
# case it left open is the work genuinely leading into another component, where
# the right answer is to stop rather than to follow it.
_BOUNDARY = _flat(sense_mod.BOUNDARY_SENSE)
BOUNDARY = (
    ("a component boundary is a stopping point", "the rule itself"),
    ("do not follow it",
     "and that the work leading out of the box is not a reason to leave it"),
    ("saving point",
     "what happens instead: what is in hand gets to a saving point"),
    ("which box the work continues in", "and the turn says where it continues"),
    ("a tap, not an errand",
     "the hand-off is a link they open, not an instruction to a person"),
    ("markdown link", "so the box is named as one"),
    ("propose the step",
     "and a box with nothing planned on it gets the step proposed"),
)
for _phrase, _why in BOUNDARY:
    check("TEACHING.md says " + _why, _phrase in _METHOD)
    check("and a turn woken in a box is told the same: " + _why,
          _phrase in _BOUNDARY)

# AND THE OTHER HALF: a sitting that has NO box, where a box is what a sitting
# is. `map.scoped` decides where that applies, so neither document may state it
# as a rule for the whole board -- a chapter of a book already IS a scope.
_NOBOX = _flat(sense_mod.NO_NODE_SENSE + sense_mod.NO_NODE_ASK)
for _phrase, _why in (
        ("no part of the map", "a sitting with no box says so"),
        ("do not pick a part of the repository",
         "and does not choose one for itself"),
        ("first card asks which box", "it asks, in its first card"),
        ("markdown links to the addresses", "and asks it as taps"),
):
    check("TEACHING.md says " + _why, _phrase in _METHOD)
    check("and a turn woken without one is told the same: " + _why,
          _phrase in _NOBOX)
check("neither document makes it a rule for a book course, which has chapters "
      "rather than components",
      "the chapter already is the scope" in _METHOD
      and "rather than as the chapters of a book" in _NOBOX)

check("every briefing carries the rule about how a card reads",
      "ANSWER in the first sentence" in sense_mod.PLAIN_SENSE
      and "One idea per sentence" in sense_mod.PLAIN_SENSE)

# A DOING TURN IS NOT GIVEN A TEACHING TURN'S CLOCK.
#
# One timeout, 900 seconds, for every turn. A teaching turn writes a card in
# thirty; a doing turn stages models, runs a test suite and submits jobs, and the
# first successful one took 56 minutes. The second was killed at 15 with eight
# files changed and nothing committed.
import importlib.machinery as _im                            # noqa: E402
import importlib.util as _iu                                 # noqa: E402

_tl = importlib.machinery.SourceFileLoader("tutorcli", os.path.join(ROOT, "bin", "tutor"))
tutorcli = importlib.util.module_from_spec(
    importlib.util.spec_from_loader("tutorcli", _tl))
_tl.exec_module(tutorcli)
_cfg = tutorcli.load_config()

_clock = tempfile.mkdtemp(prefix="tutor-clock-")
try:
    os.makedirs(os.path.join(_clock, "live"))

    def _sitting(**kw):
        import json as _j
        with open(os.path.join(_clock, "live", "state.json"), "w",
                  encoding="utf-8") as fh:
            _j.dump(kw, fh)

    _sitting(session="lecture", aim="teach")
    teach_for = tutorcli.turn_timeout(_cfg, _clock)
    _sitting(session="lecture", aim="build", stance="do")
    build_for = tutorcli.turn_timeout(_cfg, _clock)
    _sitting(session="make", makes="paper")
    make_for = tutorcli.turn_timeout(_cfg, _clock)
    check("a turn that writes the code gets longer than one that writes a card",
          build_for > teach_for)
    check("and long enough for work that actually runs (%d minutes)"
          % (build_for // 60), build_for >= 2400)
    check("a sitting that makes a document gets the same",
          make_for == build_for)
    check("while a teaching turn's clock is unchanged", teach_for == 900)
finally:
    shutil.rmtree(_clock, ignore_errors=True)

home = tempfile.mkdtemp(prefix="tutor-doing-")
try:
    root = os.path.join(home, "Course")
    os.makedirs(root)
    with open(os.path.join(root, "tutorboard.json"), "w", encoding="utf-8") as fh:
        fh.write('{"name": "Course"}')
    repo = Repo(root)

    def state(**kw):
        st = {"course": "Course", "session": "lecture"}
        st.update(kw)
        with open(repo.state_path, "w", encoding="utf-8") as fh:
            import json as _json
            _json.dump(st, fh)

    # Every way of saying "this turn does the work" has to reach the same clause,
    # because they are written down in three different places and a person taps
    # one of them without knowing which.
    for kw, why in ((dict(aim="build"), "the aim they tapped on the map"),
                    (dict(stance="do"), "a stance chosen for the sitting"),
                    (dict(session="make", makes="paper"), "a sitting that makes a document"),
                    (dict(aim="slides"), "an aim of building a deck")):
        state(**kw)
        check("a doing turn is told so by %s" % why,
              "DOING TURN" in sense_mod.session_sense(repo))
    for kw, why in ((dict(aim="teach"), "teaching"),
                    (dict(aim="coach"), "coaching them through it"),
                    (dict(), "a plain lecture in a teach repository")):
        state(**kw)
        said = sense_mod.session_sense(repo)
        check("and a turn that is %s is not" % why, "DOING TURN" not in said)
        check("...but is still told how to write (%s)" % why,
              "ANSWER in the first sentence" in said)

    # And the mechanism the shape depends on: one card, opened with a sentence
    # and finished with the report, keeping its place in the transcript.
    import io as _io
    import contextlib as _ctx

    def write(args, body):
        out = _io.StringIO()
        old_stdin = sys.stdin
        sys.stdin = _io.StringIO(body)
        try:
            with _ctx.redirect_stdout(out):
                code = boardcli.cmd_write(boardcli.Live(root), args)
        finally:
            sys.stdin = old_stdin
        return code, out.getvalue().strip()

    # A flag is not part of a title. `board write lesson --title "..."` is the
    # obvious thing to type and there was no such option, so the flag went INTO
    # the title: a card on the board called `--title Opening: verify the call
    # path`, filed under `0001-title-opening-...`. The title is what the reader
    # sees and what the transcript is indexed by.
    code, flagged = write(["lesson", "--title", "Opening: verify the call path"],
                          "one sentence.")
    head = open(flagged, encoding="utf-8").read()
    check("a --title is read as the title rather than written into it",
          code == 0 and "title: Opening: verify the call path" in head)
    check("and the card is filed under the title, not under the flag",
          os.path.basename(flagged) == "0001-opening-verify-the-call-path.md")
    code, odd = write(["lesson", "--nonsense", "real name"], "x")
    check("an option nobody implemented is dropped, not printed on the board",
          code == 0 and "--nonsense" not in open(odd, encoding="utf-8").read())
    for name in os.listdir(repo.cards):
        os.remove(os.path.join(repo.cards, name))

    code, first = write(["lesson", "starting"], "I am about to split it in two.")
    check("a doing turn can put one sentence up at once",
          code == 0 and os.path.basename(first).startswith("0001-"))
    code, again = write(["--over", os.path.basename(first), "lesson", "the seam is cut"],
                        "Done. Split it into two functions and ran the tests.")
    body = open(again, encoding="utf-8").read()
    check("and write the report over it rather than beside it",
          code == 0 and "Split it into two functions" in body)
    check("one card, keeping its place in the transcript",
          len([n for n in os.listdir(repo.cards) if n.endswith(".md")]) == 1
          and os.path.basename(again).startswith("0001-"))
    check("and the card is renamed to what it now says",
          "the-seam-is-cut" in os.path.basename(again))
    # A path out of an argument is a path somebody could have written anything
    # into, and this one is opened for writing.
    code, _said = write(["--over", "../../../etc/passwd", "lesson", "no"], "x")
    check("a card outside this board is refused rather than written over",
          code == 1)

    # ASKING WHAT A COMMAND DOES MUST NOT WRITE ONE. `board write --help` went
    # straight to `cmd_write`, which drops anything that looks like an option,
    # read an empty body off the terminal and put a blank card on the lesson --
    # pushed to every device, in the transcript, with no undo.
    before = sorted(os.listdir(repo.cards))
    out = _io.StringIO()
    old_stdin, sys.stdin = sys.stdin, _io.StringIO("")
    try:
        with _ctx.redirect_stdout(out):
            code = boardcli.main(["write", "--help", "--repo", root])
    finally:
        sys.stdin = old_stdin
    said = out.getvalue()
    check("`board write --help` prints what the command is for",
          code == 0 and "board write" in said and "--over" in said)
    check("and writes no card while it does it",
          sorted(os.listdir(repo.cards)) == before)
    # The fix is in the dispatcher, so it is every command's, not one command's.
    out = _io.StringIO()
    with _ctx.redirect_stdout(out):
        code = boardcli.main(["handoff", "--help", "--repo", root])
    check("and every other command answers the same question the same way",
          code == 0 and "board handoff" in out.getvalue())
    out = _io.StringIO()
    with _ctx.redirect_stdout(out):
        code = boardcli.main(["--help"])
    check("while the bare word still prints the whole list",
          code == 0 and len(out.getvalue()) > 200)
finally:
    shutil.rmtree(home, ignore_errors=True)

print()
print("%d FAILURES" % len(fails) if fails else "the method ships with the board")
sys.exit(1 if fails else 0)
