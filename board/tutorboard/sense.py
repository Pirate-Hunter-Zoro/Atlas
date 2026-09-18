"""What a turn MEANS, in a sentence the assistant can act on.

In a headless session these strings are the whole prompt. The shape of a
lesson is carried here rather than left to be inferred, because a model handed
a chapter and told to teach writes a lecture every time.

There is ONE shape, for every repository. There used to be two: a `mode` in
`tutorboard.json` said `math` or `code`, and a code repository was handed a
different method, a different first card and three tap-signals instead of an
answer. It is gone. A repository whose subject is code is still taught by being
asked to do things; what differs between courses is where the exercises come
from -- a book has them at the end of a section, and a repository without one
has them wherever it says its work is planned.

A WALKTHROUGH is where that stopped being enough, and it is a sitting rather
than a second shape. Every other sitting ends in the student producing something
new, and in a working project most of what has to be understood was written
months ago: a tutor with nowhere to put that does the only thing it can, which is
manufacture exercises around it. So the exercise becomes a hand trace through
code that already exists -- still one card, still short, still one question, and
still answered on the board. `WALK_SENSE` is the whole of the difference.
"""

import os

from . import plain
from .course import config, homework, plan, reading, results, review, syllabus, walk
# `map` is a builtin; the module keeps the name the board calls the thing.
from .course import map as mapping


# arrives at a board with nothing on it and an assistant with no other context.
SIGNAL_SENSE = {
    "begin": "there is nothing on the board yet and they are waiting. "
             "Open the session and write the first card.",
    # The lecture and test-review reading. A homework sitting means something
    # different by the same tap and gets its own sentence -- see `skip_sense`.
    "skip": "they are not writing this one out. Do not re-ask it and do not press "
            "them on it; carry on with the lesson. If it was a hand-check, treat "
            "that idea as known and go to the next one -- or, if it was the last "
            "one, straight to the exercise, restated in full.",
    # A CHANGE OF AIM IS AN INTERRUPTION, NOT A NEW SITTING. `/aim` writes the
    # new aim and wakes a turn; nothing is archived and no tutor is replaced, so
    # the one thing that has to be said is that everything already on the board
    # still stands. Without it a turn woken by this reads a changed style as a
    # changed subject and starts the evening again.
    "aim": "they have changed WHAT THEY WANT FROM THIS SITTING, in the middle of "
           "it, and nothing else about it has changed. Everything already on the "
           "board stands: the lesson was not filed away, you are not a new "
           "tutor, and what you have both agreed is still agreed. Write the NEXT "
           "card the new way. Do not start over, do not re-introduce yourself, "
           "and do not recap what you have just done together.",
    # ONE STEP HANDED OVER, AND THE SITTING IS STILL A COACHING SITTING.
    # `coach` names the calls and lets them type it, and there was no way out of
    # one step of that: the only escape was `/aim`, which changes the WHOLE
    # sitting to `build`, so the way to get one step written for you was to stop
    # being coached and have every card after it written the new way. Asked for
    # as *"in coach coding mode, I still want to be able to have a 'fuck this,
    # you do this step' option."* `handover_sense` names the card and says what
    # to write; this is what the tap meant.
    "handover": "they do not want to type this one. You write it -- this step "
                "and no more -- and then carry on coaching. The aim has not "
                "changed, nothing has been filed away, and you are not a new "
                "tutor.",
    "done": "their work is ready for you to check.",
    "help": "they are stuck and want help.",
    "confused": "something is not making sense to them.",
}


# The method in one paragraph. In a headless session these strings ARE the whole
# prompt, and the shape is the half that goes wrong -- a model handed a chapter
# and told to teach writes a lecture, every time, because that is what teaching
# looks like in everything it was trained on. So the shape is said outright and
# said first: a lesson is exercises, and explanation that is not something the
# student does is not part of it.
# HOW EVERY CARD READS, whatever the sitting is.
#
# Asked for after a card that was correct and nearly unreadable -- five headings,
# five hundred words, and the answer to "what did you just do" nowhere in the
# first paragraph: *"the tutor should ALWAYS give me easy to understand
# responses."* Whatever is being done -- mathematics, code written for them,
# code they are being coached through, a paper, a deck -- what lands on the
# board is read on a tablet by somebody who has been doing something else.
#
# This is in every briefing rather than in one kind of sitting, because the
# complaint was about all of them.
PLAIN_SENSE = (
    "HOW TO WRITE, in every card, whatever this sitting is. Put the ANSWER in "
    "the first sentence -- what happened, what it is, what to do -- and the "
    "reasoning under it. One idea per sentence, short sentences, plain words. "
    "Never open by restating the question or by narrating what you are about to "
    "say. Spell out any term, filename or shorthand the first time it appears, "
    "in the same sentence, in a few plain words. No headings in a card under "
    "300 words, and no closing paragraph -- the last useful sentence ends it. "
    "If they would have to read a sentence twice, it is the wrong sentence.\n"
    # Two of the rules above are a door rather than a request, for the reason
    # HANDOFF.md reached eleven times its cap while a prompt asked nicely: see
    # `tutorboard/plain.py`. A turn is told the numbers here so it writes the
    # card once, rather than discovering them from a refusal.
    "TWO OF THOSE ARE A DOOR, NOT A REQUEST: `board write` refuses a card over "
    "%d words, and one with a single paragraph over %d. A list of definitions is "
    "a list, one line each; fenced code and displayed mathematics are not "
    "counted. What will not fit belongs in a later card, or in a file in the "
    "repository the board can open -- not on the glass over the lesson. "
) % (plain.CARD_WORDS, plain.PARAGRAPH_WORDS)


METHOD_SENSE = (
    "Follow live/TEACHING.md, and the rule it all follows from: THE LESSON IS "
    "EXERCISES, not explanation. Never write a card that teaches for four "
    "paragraphs and asks at the bottom. Instead: state the exercise in full so "
    "they can see what it is for, then hand them ONE tiny thing to work "
    "themselves -- you supply the concrete objects, they show what those objects "
    "are (is this one an example, which of these three is not, where does this "
    "one fail) -- one per turn, and only for what the exercise actually needs. "
    "When the last of those is answered or skipped, put the exercise back in "
    "front of them RESTATED IN FULL and ask for it; a reference to it is not a "
    "re-pose. EVERY card that poses a problem is self-contained: under the "
    "statement, list every definition, symbol and named result the problem uses, "
    "one line each, including ones from checks they skipped. They are reading on "
    "a tablet and must never have to scroll back up the lesson to find out what "
    "they are being asked to prove. "
    "THEN ASK IT AGAIN. After that list, close the card by restating the "
    "question -- the whole ask, not a pointer to it -- so the LAST thing on the "
    "card is what they are being asked to do. The definitions sit between the "
    "statement and the board they write on, so a card that asks once at the top "
    "sends them scrolling back up past every definition to remember the "
    "question. Twice on one card is not repetition; it is the question being "
    "where the pen is. "
    "One question per turn, then stop and wait. "
    "The only thing that counts is exercises answered. "
)


# THE WRITE-UP HAPPENS IN THE TURN THAT AGREES THE ANSWER.
#
# `live/TEACHING.md` has said so since it was written -- "once an answer is
# agreed correct, not before, transcribe it into that file, in the same turn" --
# and in a headless session that document is a file the tutor may or may not
# open, while THIS string is the whole prompt. So the rule was in the place
# nobody reads on a turn that is going well, and what came back was a sitting
# that worked five problems and compiled nothing.
#
# Reported plainly: "the math tutor hasn't been writing up and compiling the
# solutions as we've been working through problems -- that should be automatic
# problem by problem as we finish each one correctly."
#
# Not on the two sittings that hand nothing in. A review and a walkthrough each
# say, in their own words, that the lesson is the record.
WRITEUP_SENSE = (
    "THE WRITE-UP IS PART OF THE TURN THAT AGREES AN ANSWER, not part of the end "
    "of the sitting. The moment one problem is agreed correct -- not before, and "
    "before you pose the next one -- do all four of these in that same turn: "
    "`board hw use <chNN>` if this sitting is not bound to a file yet "
    "(`board hw list` shows what there is, `board hw new <name>` lays one down "
    "where there is none); transcribe the STATEMENT into its problem environment "
    "and THEIR argument into the solution region beneath it, in the sheet's own "
    "order rather than the order they answered in; `board hw file <label>` to "
    "put their handwriting beside it; and `board hw build` to compile it. "
    "COMPILING IS YOURS, not theirs -- if it fails, put the LaTeX error it "
    "printed on the board rather than the word 'failed'. Never write a solution "
    "they have not produced, and never leave the write-up for the end: a sitting "
    "is abandoned far more often than it is finished tidily, so an exercise "
    "agreed at half past is typeset by twenty-five to. "
    # AND NEVER TELL THEM TO WRITE IT UP. A card in Galois Theory said "two
    # words to add when you write it up", which is two failures in one clause:
    # it hands over an errand that does not exist -- the document is the tutor's
    # -- and it DEFERS A CORRECTION, because the missing word was a fact about
    # the proof rather than a note for later. Reported as "I'M not fucking
    # writing anything up... It should put phrases in like that - that makes me
    # uneasy." In headless this string is the whole prompt, so the rule has to
    # be here and not only in the document.
    "NEVER TELL THEM TO WRITE IT UP. No card says 'when you write it up', 'add "
    "this to your write-up' or 'two words to add' -- the document is yours, so "
    "report what the file NOW SAYS rather than handing them an errand. And where "
    "the missing words are a CORRECTION, make it in the write-up in this same "
    "turn and say on the card what was wrong and that the file now says it "
    "right: a fix made conditional on something they were never going to do "
    "leaves the proof wrong in a document you have told them is finished. "
)


# The one thing a repository may still say about how it is taught, and it is a
# STANCE rather than a subject: teach the work, or do it. It is a paragraph
# appended to the method rather than a method of its own -- everything about the
# shape of a turn is unchanged, which is why it is one line of configuration.
DO_SENSE = (
    "THIS REPOSITORY'S STANCE IS DO, NOT TEACH. It said so in writing, in "
    "tutorboard.json, so: you write the code yourself, run what needs running, "
    "and commit when it is right. Do not withhold an implementation and do not "
    "ask them to type it. The card is a report rather than an exercise -- what "
    "you changed, what it does now, what you ran and what came back, and the one "
    "decision or check you need from them. Still one card, still short, still one "
    "thing per turn, and it still stops and waits. Say what you did NOT verify -- "
    "a card claiming a job ran when it was only submitted is worse than no card. "
)


# THE SHAPE OF A TURN THAT DOES THE WORK, and it is the opposite shape to a
# teaching turn's.
#
# `live/TEACHING.md` says, three times and in capitals, that the card is written
# before anything else happens. That rule is right and it is a TEACHING turn's
# rule: there the card IS the work, so writing it first fills the board while
# everything else happens behind it.
#
# In a doing turn the work is a change to the repository, and a card written
# before that change can only describe an intention. That is not a hypothetical:
# the first time somebody tapped "write the code for me", what came back was a
# four-hundred-word plan, a list of what had not been done, and a question --
# reported as *"I'm not sure any coding happened."* The card was written first,
# the card was the turn, and the turn ended.
#
# So the order is inverted here, and the board is kept alive by the one thing
# that costs nothing: a sentence, then the work, then the report over the top of
# it. `board write --over` exists for precisely that.
DOING_SENSE = (
    "THIS IS A DOING TURN, AND ITS ORDER IS THE OPPOSITE OF A TEACHING TURN'S. "
    "live/TEACHING.md says to write the card before anything else; that is a "
    "teaching turn's rule, where the card is the work. Here the work is the "
    "change, and a card written before it can only describe an intention. Do it "
    "in this order, and do not stop before the end:\n"
    "1. `board write` ONE sentence saying what you are about to do, in plain "
    "words. It lands at once, so the board is never blank. Keep the path it "
    "prints.\n"
    "2. DO THE WORK. Write the code. Run it. Read what came back. Fix what it "
    "showed you. If something cannot be run here, run what can and say which.\n"
    "3. `board write --over <that path>` with the REPORT: what you changed, "
    "which files, what you ran, what it said, and what is left. Plain words, "
    "under 200, no headings.\n"
    "4. Then stop. Ask something only if you are actually blocked -- if you can "
    "pick a reasonable answer and say which you picked, do that instead. A "
    "question is not how a doing turn ends by default.\n"
    "Never hand back a plan of what you would do as though it were the work. If "
    "the job is genuinely too big for one turn, do the FIRST PART OF IT and "
    "report that, rather than describing all of it and doing none.\n"
    "AND WHERE THE NEW THING GOES: a new thing goes in a module named for the "
    "one job it does, and if that means moving something first, move it first. "
    "This workspace has a map, and the boxes on it are its own modules with the "
    "arrows drawn from what they import -- so a module that does six unrelated "
    "things draws as one box with eleven arrows into it and teaches nobody "
    "anything. The picture is a mirror, and the failure is the module rather "
    "than the renderer. `helpers`, `utils`, `common` and `misc` are four "
    "spellings of nobody decided. Python will let you append anything to any "
    "file and it will run; getting away with it is not the test, and the test "
    "is what the box looks like on the map. live/TEACHING.md says the same "
    "under `Where a new thing goes`. "
)


# WHAT A HANDED-OVER STEP IS, and the one thing it must not come back as.
#
# `coach` is one step per card, named in English, typed by them. The tap that
# reaches this hands over ONE of those steps and leaves the sitting coaching, so
# the turn it wakes is a doing turn inside a teaching sitting -- `DOING_SENSE`
# carries the order, and this carries what is different about it.
#
# THE STEP IS NOT WRITTEN UP AS A COACH CARD AFTERWARDS. A card explaining how
# the step was done is a lecture nobody asked for: they handed it over because
# they did not want to type it, and their next act is the NEXT step. So the one
# card is a short report with the next step posed under it, which is also what
# keeps the lesson moving without a second tap.
HANDOVER_SENSE = (
    "THE STEP IS CARD %s, AND IT IS THE ONLY ONE YOU WRITE. Do what that card "
    "told them to do: write it, run what needs running, and leave the "
    "repository as that card described. Do not take the step after it, do not "
    "widen it into the rest of the job, and do not change the aim of this "
    "sitting -- they asked for one step, not for the wheel.\n"
    "THEN ONE CARD, AND IT IS NOT A COACH CARD ABOUT THE STEP YOU JUST DID. A "
    "card explaining how you did it is a lecture nobody asked for. That card "
    "is, in this order: three or four lines of REPORT -- what you changed, "
    "which files, what you ran and what came back -- and then THE NEXT STEP, "
    "posed the way you were posing them before, naming the calls, the "
    "arguments and the order in English for them to type. If the step you were "
    "handed was the last one, say what is left instead of inventing another. "
)


def handover_sense(card):
    """The inbox line for one step handed over, naming the card it is about."""
    return HANDOVER_SENSE % card


# What a stance chosen for THIS SITTING has to say that a repository's own does
# not: that it is this sitting's and stops with it. A tutor told to write the
# code, in a repository whose standing answer is to withhold it, must not carry
# that into the next lesson -- and it has no way of knowing it was a sitting's
# choice unless it is told so here.
SITTING_DO_SENSE = (
    "THIS STANCE WAS CHOSEN FOR THIS SITTING and is not what the repository "
    "says. It ends when the sitting does. Do not write it into HANDOFF.md as "
    "though it were the repository's standing answer, and do not carry it into "
    "the next lesson. "
)

SITTING_TEACH_SENSE = (
    "THIS REPOSITORY'S STANCE IS DO, AND THIS SITTING'S IS TEACH -- they asked "
    "for this one to be taught rather than done. So the withholding is back on "
    "for the whole of it: they write the code, you do not, and you do not put a "
    "solution on the board. It ends when the sitting does; the repository's own "
    "answer is unchanged and the next lesson is a doing one again unless it says "
    "otherwise. "
)


def stance_sense(stance, chosen=False, declared="teach"):
    """The stance paragraph for this sitting, or nothing at all.

    Never guessed, and nothing infers it from what is in the repository -- a
    directory full of Python is not a request to have the Python written. What
    is new is that the ANSWER may come from the sitting rather than from the
    repository, and when it does it says so: a stance that overrode the written
    one has to be visibly temporary, or the tutor writes it into the handoff and
    it quietly becomes permanent.
    """
    if stance == "do":
        return DO_SENSE + (SITTING_DO_SENSE if chosen and declared != "do" else "")
    if chosen and declared == "do":
        return SITTING_TEACH_SENSE
    return ""


def where_sense(book, root=None):
    """Where the exercises come from, which is the only thing a subject decides.

    A course that follows a book has them at the end of a section. A repository
    that does not is not thereby a different kind of sitting -- it is the same
    lesson whose exercises come from wherever the repository says its work is
    planned. This used to be a whole second method, `code_sense`, and it carried
    a whole second interface with it.

    WHAT CHANGED: the plan is now NAMED, and where possible its next steps are
    quoted. The old text told a tutor to read the README and follow what it
    points at, which is honest and expensive -- in PSYCH-ASR it is a 1,500-line
    README, a pointer out of it, and a 1,300-line task list, paid for on every
    cold turn before a word is taught. `plan.py` already found the file and read
    the steps for the drawer; handing the same answer to the tutor costs nothing
    and removes the two round trips and the guess between them.
    """
    if book:
        return ("Read the section's exercises before you teach anything and "
                "choose a manageable few -- three to five -- saying which and "
                "why in your first card. ")

    where = plan.where(root) if root else ""
    steps = plan.steps(root) if root else []
    if steps:
        listed = "; ".join("%s. %s" % (x["num"], x["title"]) for x in steps[:6])
        return (
            "This repository does not follow a book: no chapters, no sections, "
            "and no exercises at the end of anything. That changes where the "
            "exercises come from and NOTHING else -- the lesson is still "
            "exercises and they are still answered on the board. "
            "ITS WORK IS PLANNED IN %s, AND THAT FILE OUTRANKS ANYTHING YOU "
            "WOULD HAVE CHOSEN. Its next steps, in its own order: %s. Do not "
            "re-derive this from the README and do not survey the repository "
            "for an agenda of your own -- open the plan at the step this "
            "sitting is labelled with, or at the first one if it carries no "
            "label, and read THAT step before your first card. Then set the "
            "exercises that step actually needs, three to five of them, saying "
            "which and why in your first card. If the step is one you cannot "
            "set work from because it needs a decision from them, ask for the "
            "decision instead. " % (where, listed))
    return (
        "This repository does not follow a book: no chapters, no sections, and "
        "no exercises at the end of anything. That changes where the exercises "
        "come from and NOTHING else -- the lesson is still exercises and they "
        "are still answered on the board. Read README.md at the root first, and "
        "follow what it points at -- a task list, a planning document, a "
        "companion repository -- because that is what says what comes next and "
        "it outranks anything you would have chosen. Read HANDOFF.md too if "
        "there is one. Do NOT manufacture a curriculum out of the README's "
        "headings: they describe how the thing is built, not an order to learn "
        "it in. Then set the exercises the work actually needs, three to five of "
        "them, saying which and why in your first card. If nothing names what "
        "comes next, ask in that card rather than picking an agenda of your own. "
    )


# WHAT THE TUTOR MAY PUT ON A CARD BESIDES ITS OWN WORDS.
#
# These repositories have documents in them that explain the machinery better
# than a card can -- a 33-slide walkthrough of the reference pipeline, written
# for exactly this purpose -- and until now the board could not show a page of
# one. So it was read on a laptop beside a lesson on an iPad, which is the
# split attention the board exists to remove.
def reading_sense(repo):
    """The documents this course can show, named, with how to put one on a card."""
    try:
        found = reading.documents(repo.root)
    except Exception:                                        # noqa: BLE001
        return ""
    if not found:
        return ""
    named = "; ".join("%s (%s)" % (d["name"], d["id"]) for d in found[:6])
    return (
        "THIS COURSE CAN SHOW SLIDES, and you may put one in a card: write a "
        "markdown image whose source is /doc/<id>/<page>.png -- for example "
        "![slide 24](/doc/%s/24.png) -- and that page appears in the lesson. "
        "The documents here are: %s. Use one when the document already makes "
        "the point better than a paragraph would, and then ask your question "
        "UNDER it: a slide is an object to work on, not an explanation that "
        "replaces the exercise. One slide per card at most. Never paste a slide "
        "in place of a question, and never show a page you have not opened and "
        "read yourself. " % (found[0]["id"], named))


def results_sense(repo):
    """The figures this workspace made, named, with how to put one on a card.

    `reading_sense`'s shape, for the other kind of picture. A tutor teaching the
    overlap between two arms had to describe a histogram somebody was looking at
    on a laptop; the figure exists, the pipeline wrote it, and there was no
    address for it.
    """
    try:
        found = results.figures(repo.root)
    except Exception:                                        # noqa: BLE001
        return ""
    if not found:
        return ""
    named = "; ".join(
        "%s%s (%s)" % (f["name"], " in " + f["where"] if f["where"] else "",
                       f["id"])
        for f in found[:6])
    return (
        "THIS WORKSPACE'S OWN FIGURES CAN GO ON THE BOARD, and you may put one "
        "in a card: write a markdown image whose source is /result/<id> -- for "
        "example ![the overlap](/result/%s) -- and that figure appears in the "
        "lesson. The most recently written ones are: %s. These are the "
        "pipeline's output, not yours: show one to ask about what it shows, "
        "and say what you are looking at UNDER it. Never show a figure you "
        "have not opened and read yourself, and never let one stand in place of "
        "the question. One figure per card at most. " % (found[0]["id"], named))


def review_sense(repo, st):
    """A test review, in a sentence the assistant can act on.

    A review is not a third way of teaching -- it is the homework loop pointed at
    a scope the student chose instead of at a sheet somebody set. So this says
    the two things that are actually different, and leaves the shape of a turn to
    live/TEACHING.md where it belongs: what the scope is, and that it is not the
    assistant's to widen.

    The chapters are NAMED here rather than left to be looked up. In a headless
    session this string is the whole prompt, and a tutor that has to glob the
    repository to find out what it is reviewing pays a round trip for something
    the board already knew.
    """
    chosen = review.scope(repo.root, st)
    of = review.kind(repo.root) or "chapters"
    # What this repository HAS, not what it was once declared to be. `review`
    # already answers that -- chapters where there is a book, the repository's
    # own top-level parts where there is not -- and asking it is how this stopped
    # needing a mode to tell it.
    project = of == "parts"
    what = "parts of this project" if project else "chapters"
    counted = (review.noun("parts", len(chosen)) + " of this project") \
        if project else review.noun("chapters", len(chosen))

    if not chosen:
        # Reachable from `board open --review` with nothing named. The board's
        # own picker cannot produce it, and inferring a scope is exactly the
        # mistake a homework sitting with no sheet is told not to make.
        return ("Follow live/TEACHING.md. This is a TEST REVIEW sitting and "
                "nothing has been chosen for it to cover. Ask in your first card "
                "which %s the test is over, and do not choose them yourself -- "
                "they know what is on it and you do not." % what)

    named = ", ".join(u["label"] for u in chosen)
    where = (
        "Read those parts of the repository before your first card, then ask "
        "about the code that is already there: what a function does, why it is "
        "written that way, what would break if it changed. This is not a sitting "
        "for setting work -- do not assign a change, and do not write code into a "
        "card even where this repository's stance is to do the work, because a "
        "review asks. "
        if project else
        "Draw each question from those chapters' own exercises where there are "
        "some, and write one in the same style where there are not. "
    )
    return (
        METHOD_SENSE +
        "A review is the one sitting that asks COLD: no hand-checks in front of "
        "the question and nothing taught toward it, because you are finding out "
        "what is not solid. Ladder only from a break, once there is one, and "
        "then re-pose the question in full. "
        "This is a TEST REVIEW over %s, "
        "in this order: %s. "
        "The scope is theirs and is not yours to widen or narrow -- ask over "
        "exactly those and nothing else, and spread the questions across all of "
        "them rather than exhausting the first. A review is for finding what is "
        "not solid yet, so a question they answer cleanly is a question you move "
        "on from. %s"
        "Pose them exactly as a homework problem is posed: state the question in "
        "full in a `question` card, stop, and read what comes back -- locate the "
        "break rather than repairing it. "
        "Nothing is being handed in, so there is no write-up: do not transcribe "
        "into a .tex and do not compile anything. The lesson itself is the record. "
        "Say in your first card what this review covers and which one you are "
        "starting on." % (counted, named, where)
    )


# THE SHAPE OF A WALKTHROUGH, WHICH IS A LESSON ABOUT SOMETHING ALREADY WRITTEN.
#
# The failure this replaces is on disk in PSYCH-ASR: a tutor with no sitting for
# existing machinery invented a curriculum of diarization arithmetic on fictional
# numbers, in a repository whose owner had said what he wanted explained. A model
# asked to teach code it cannot set as an exercise writes a tour of the file, top
# to bottom, and the person reading it on a tablet has understood nothing by the
# end -- which is the same failure as the lecture `METHOD_SENSE` exists to
# prevent, in a place that had no rule against it.
#
# So the exercise is a HAND TRACE. The format is not invented here either: the
# owner of these repositories wrote `stage2_reference_walkthrough` by hand for
# exactly this purpose -- plain names before identifiers, one invented example
# carried the whole way through, the algorithm shown as worked passes over it --
# and describes it as the plainest document in the repository. This is that, one
# card at a time, with the student doing the passes instead of reading them.
WALK_SENSE = (
    "Follow live/TEACHING.md. THIS IS A WALKTHROUGH SITTING: the machinery "
    "already exists and the lesson is understanding it, not writing it. "
    "NOTHING IS BEING BUILT HERE. Do not assign a change, do not propose a "
    "refactor, do not offer to fix anything you find, and do not write code into "
    "a card -- not even where this repository's stance is to do the work, "
    "because a walkthrough reads. If you find a real bug, say so in one sentence "
    "at the end of a card and carry on; it is a separate sitting. "
    "THE LESSON IS STILL EXERCISES, and the exercise is a hand trace: you supply "
    "a concrete input, they carry it one step through the code and say what comes "
    "out. Never write a card that explains for four paragraphs and asks at the "
    "bottom. "
    "Read the files named below BEFORE your first card -- all of them, properly. "
    "That is the one thing you do up front and it is not a card. "
    "THEN, IN THIS ORDER. "
    "(1) ONE INSTANCE FOR THE WHOLE SITTING, and you invent it: three rows, two "
    "turns, two speakers -- small enough to hold in the head, and the SAME one in "
    "every card, so they are not learning a new example each turn. It is always "
    "INVENTED and you say so on the card. Real rows in these repositories are "
    "clinical data and do not go on a board. "
    "(2) PLAIN NAMES BEFORE IDENTIFIERS. The first time a component appears, "
    "give it a name in everyday words -- the typist, the stopwatch, the "
    "name-tagger -- say in one sentence what job it does, and then use that name "
    "beside the real one for the rest of the sitting. "
    "(3) YOUR FIRST CARD says what this machinery is FOR in one sentence of "
    "ordinary words, shows the instance as a small markdown table, says how many "
    "steps the trace has, and asks the FIRST question. Nothing else. "
    "(4) EVERY CARD AFTER IT is one step of the trace. Show the smallest excerpt "
    "of the real source the question is about -- a handful of lines, never the "
    "file, never a whole function if half of it is beside the point -- put the "
    "state of the instance before that step in a table, and ask ONE thing: what "
    "does this return, which of these two branches runs, what is in this "
    "variable now, what breaks if this line goes. They answer on the board, by "
    "writing on the card or by typing. "
    "(5) WHEN THEY ARE WRONG, find the break in their reasoning and re-ask the "
    "SAME step on a fresh instance rather than explaining it again. An "
    "explanation they read is not a step they worked. "
    "(6) THE DESTINATION is them carrying the instance all the way through and "
    "producing what the code would produce. Keep it visible in one short line "
    "-- 'two steps left: the match pass, then the labels' -- and do not expand "
    "the steps before you reach them. "
    "(7) ONLY WHEN THE TRACE IS DONE, write the recap: three or four lines on "
    "what this machinery does and where it is weak. Last, never first -- a "
    "summary before the trace is the word dump this sitting exists to replace. "
    "Nothing is handed in and there is no write-up: do not transcribe into a "
    ".tex and do not compile anything. The lesson itself is the record. "
)


def walk_sense(repo, st):
    """A walkthrough, in a sentence the assistant can act on.

    The scope is NAMED here rather than left to be looked up: in a headless
    session this string is the whole prompt, and a tutor that has to search the
    repository for what it is walking through pays a round trip for something
    the board already knew -- and, worse, may find something else and teach
    that.
    """
    chosen = walk.scope(repo.root, st)
    if not chosen:
        # Reachable from `board open --walk` with nothing named. The board's own
        # picker refuses to start one, and choosing the machinery for them is
        # the same mistake as choosing what a test covers: they know what they
        # do not understand and you do not.
        return ("Follow live/TEACHING.md. This is a WALKTHROUGH sitting and "
                "nothing has been named for it to cover. Ask in your first card "
                "which file or function they want walked through, and do not "
                "choose it yourself -- they know what they do not understand "
                "and you do not. Do not survey the repository for a candidate.")

    named = ", ".join(u["label"] for u in chosen)
    one = len(chosen) == 1
    return (WALK_SENSE +
            "THIS WALKTHROUGH IS OVER %s: %s. Read %s before your first card. "
            "The scope is theirs and is not yours to widen: everything else in "
            "this repository is off the table for this sitting, however relevant "
            "it looks. Where a named symbol is given after `::`, that function "
            "is where the sitting starts -- the rest of its file is background "
            "you read and do not teach. "
            "Say in your first card what you are walking through and what the "
            "first step is."
            % ("one file" if one else "%d files" % len(chosen), named,
               "it" if one else "all of them"))


def skip_sense(repo):
    """What a skip means, which depends on what kind of sitting this is.

    In a lecture it means *I have this already*: the concept check is pace
    control, and re-asking a question somebody has waved away teaches nothing.
    That reading was applied everywhere, and in a homework sitting it is wrong
    and expensive -- the problems are not the assistant's to drop. A skipped
    homework problem is a lost mark, and the student skipping it means *not now*,
    not *never*. They are entitled to work the sheet in whatever order they like;
    they are not entitled to have the assistant quietly agree the sheet is
    shorter than it is.

    So in homework the tap defers, and the sentence says what is still owed and
    what to come back to. The list is read off the document rather than the
    conversation, which is what makes it survive a restart, a new tutor, and the
    two hours between the skip and the return.
    """
    st = repo.state()
    if (st.get("session") or "lecture") != "homework":
        return SIGNAL_SENSE["skip"]

    line = ("they are not writing this one out NOW. This is a homework sitting, so "
            "the problem is still assigned and still owed: leave it, carry on with "
            "the rest, and come back to it once the others are done. Do not press "
            "them on it in the meantime, and do not treat it as finished. ")
    try:
        st_hw = homework.status(repo.root, st)
    except Exception:
        st_hw = None
    left = (st_hw or {}).get("outstanding") or []
    if len(left) == 1:
        # The degenerate case, and it is not a paradox: skipping the only thing
        # left means it comes straight back, because there is nothing else to go
        # on with and the sheet is not finished. Say so, or an assistant reading
        # "come back to it once the others are done" concludes the others never
        # will be and drops it.
        line += ("It is also the ONLY problem left on the sheet, so there is "
                 "nothing else to carry on with: ask it again. That is not a "
                 "mistake and it is not pressing them -- the sheet is not done "
                 "until it is done. ")
    elif left:
        line += ("Still to write up, in the sheet's order: %s. The next agreed "
                 "answer goes in %s. " % (", ".join(left), left[0]))
    line += ("They may work the sheet in any order; the document is written in "
             "the sheet's order regardless.")
    return line


def node_sense(repo, st):
    """The part of the map this sitting is about, handed over rather than hunted.

    A sitting opened from the map names a BOX -- a part of the repository, its
    one-line purpose, the files it is made of, the steps of the plan that name
    it. All of that is on disk already, and a tutor that has to go and find it
    pays for the search on every cold turn, in money and in latency, before a
    word is taught. `where_sense` learned this for the plan; this is the same
    lesson for the thing the plan is about.

    Re-resolved on the way out rather than echoed back from `state.json`: a box
    whose directory has been deleted between the sitting opening and the tutor
    waking would otherwise send it to read machinery that is not there.
    """
    node_id = (st or {}).get("node")
    if not node_id:
        return ""
    try:
        node = mapping.find(repo.root, node_id, st)
    except Exception:                                        # noqa: BLE001
        return ""
    if not node:
        return ""
    said = " This sitting is about %s" % node["name"]
    if node.get("also"):
        said += " (%s)" % node["also"]
    said += ", a part of this repository."
    if node.get("does"):
        said += " What it is: %s" % node["does"]
        if not said.endswith("."):
            said += "."
    files = node.get("files") or []
    if files:
        said += (" It is made of %d file%s: %s."
                 % (len(files), "" if len(files) == 1 else "s",
                    ", ".join(files[:6])
                    + (", and %d more" % (len(files) - 6) if len(files) > 6 else "")))
        said += (" Read those before your first card; do not survey the rest of "
                 "the repository for an agenda of your own.")
    steps = node.get("steps") or []
    if steps:
        said += (" The plan has %d step%s on this part: %s."
                 % (len(steps), "" if len(steps) == 1 else "s",
                    "; ".join("%s. %s" % (x["num"], x["title"]) for x in steps[:4])))
    if node.get("doc"):
        said += (" There is a document about it -- put a page of it in a card "
                 "with ![](/doc/%s/<page>.png) when a slide says it better than "
                 "you can." % node["doc"])
    return said


def aim_sense(st, aim=None):
    """What this sitting is FOR, in the words the person tapped.

    Not a mode and not a stance: it is the answer to "what do you want to do
    about this part", chosen on the map at the moment of opening. A sitting
    opened as *tell me what to write* and one opened as *write it for me* are
    both `stance: teach`-shaped requests in the old vocabulary and they are not
    the same evening, and a tutor that is not told which will pick one.

    `aim` is what the CALLER resolved, where the caller has more to go on than
    the sitting does: a sitting nobody opened from the map names none, and
    `config.aim_for` then answers from the workspace or its family. The two
    sittings held over a scope do not pass one -- a review that inherited
    `build` from its family would be told to write code, which is the one thing
    a review does not do.
    """
    aim = config.clean_aim(aim or (st or {}).get("aim"))
    if not aim:
        return ""
    return " " + config.AIM_MEANS.get(aim, "")


MAKE_SENSE = (
    "THIS IS A MAKE SITTING: its product is a DOCUMENT, not an answer. "
    "Nothing here is an exercise and nothing is handed in. You draft, they read "
    "and correct, you revise. "
    # WHAT THE DOCUMENT IS ABOUT, and it was the half nothing said. Everything
    # else here is about HOW to work -- sections, show each one, take
    # corrections -- and a tutor that has just spent three hours teaching, asked
    # to write it up, writes up the three hours. Stated as a refusal, because a
    # preference in a prompt is what produced the narration.
    #
    # TWO QUESTIONS, NOT ONE, and the refusal used to answer both with the same
    # word. HOW it reads is fixed: the subject, explained, never the evening
    # narrated. WHAT it covers is not: "a deck about the four things this
    # sitting covered" is a legitimate ask and the old wording refused it along
    # with the narration it was written against.
    "HOW IT READS IS FIXED, AND IT IS NEVER A NARRATION OF THIS SITTING. The "
    "document is an EXPLAINER: here is how this works, and here is the "
    "mathematics, written for somebody who was not in the room. So: no first "
    "person, no 'we covered', no 'the student then', no 'as we saw above', and "
    "no reference at all to this sitting, its cards, its questions, or the "
    "person answering them. If a concept was taught by hand-checking three "
    "examples, the document explains the concept and shows the examples -- it "
    "does not narrate the hand-check. A write-up of the evening is the one "
    "thing this sitting must not produce. "
    "WHAT IT COVERS IS A DIFFERENT QUESTION, and its scope may be THE BOX, THE "
    "CHAPTER, OR THE WHOLE EVENING. Where the machinery named below says which "
    "-- the part of the map this sitting is on, or the chapter it is labelled "
    "with -- that is the scope, and not everything else that came up while you "
    "were looking at it. WHERE THE SCOPE IS THE EVENING it is the concepts this "
    "sitting covered and nothing else about it: read the lesson back with "
    "`board recap --all`, take the list of topics off the cards, and explain "
    "each one from scratch. Not the order they were taught in, not the "
    "questions, not the answers, not who got what wrong. If nothing names a "
    "box, a chapter or the evening, ask in your first card what the document is "
    "to be about rather than drafting something and finding out. "
    "Work in sections: write one, put it on the board for them to read, take "
    "the corrections, then write the next -- a whole document dropped at once "
    "is the word dump this board exists to replace. "
    "KEEP IT IN `writeups/<slug>/`, one directory per document: `<slug>.tex` "
    "with its `figures/` and its `feedback/` beside it, `<slug>` being a short "
    "name that says what the document is. Say in every card where that file is "
    "so they can open it. A document already living somewhere else in this "
    "repository stays where it is; this is where a NEW one goes. "
    "When a section is ready to be READ rather than discussed, compile it and "
    "let them read it on the glass rather than pasting it into a card. ")


# WHAT A REVISION TURN IS WOKEN WITH, and it names both files.
#
# The turn's own instructions are in `bin/tutor` (`HEADLESS_REVISE_PROMPT`) and
# they say to read "the feedback file the text above names" -- this is that text.
# Two paths, both of them found by `course/library.py` in the workspace rather
# than built out of anything a browser sent.
#
# It says outright that this is not the lesson. A turn that reads "here is some
# feedback" on a board with a lesson on it writes a card about the feedback,
# which is the one thing this route exists not to do.
REVISE_SENSE = (
    "Feedback has been written on a document in this repository, from the "
    "LIBRARY rather than from the lesson. The document is `%s`. The feedback is "
    "`%s`. Read both, revise the document on what it says, and write what you "
    "changed at the bottom of that feedback file. "
    "THIS IS NOT PART OF THE LESSON: there may be a sitting open on this board "
    "that belongs to somebody else's evening. Write no card, do not open or "
    "archive a sitting, and leave live/state.json, live/cards/ and HANDOFF.md "
    "exactly as you found them."
)


def revise_sense(document_rel, feedback_rel):
    """The inbox line for one round of feedback on one document."""
    return REVISE_SENSE % (document_rel, feedback_rel)


# WHAT A REWORK TURN IS WOKEN WITH, and the difference from a revision is one
# word in the ask and the whole of what the turn may do.
#
# `REVISE_SENSE` above is a correction. A rework is an overhaul -- "that
# presentation needs an overhaul now that we plan to use colibri" -- and it
# carries the sentence saying what the document is FOR now, because an overhaul
# with no new purpose in it is a rewrite for its own sake.
#
# It names the purpose HERE as well as in the feedback file. The file is where
# the turn reads it in full; the inbox line is what the board paints while the
# turn runs, and "the tutor is doing something to a document" with no statement
# of what is the silence this whole surface exists to remove.
REWORK_SENSE = (
    "An OVERHAUL has been asked for on a document in this repository, from the "
    "LIBRARY rather than from the lesson. The document is `%s`. What was asked "
    "for is `%s`. This is not a correction: the document's purpose has changed, "
    "and it is now for this --\n\n%s\n\n"
    "Read both files, rework the document to that purpose, and write what you "
    "changed at the bottom of that feedback file. Its present structure, its "
    "order and its sections are yours to change. "
    "THIS IS NOT PART OF THE LESSON: there may be a sitting open on this board "
    "that belongs to somebody else's evening. Write no card, do not open or "
    "archive a sitting, and leave live/state.json, live/cards/ and HANDOFF.md "
    "exactly as you found them."
)


def rework_sense(document_rel, feedback_rel, purpose):
    """The inbox line for an overhaul of one document."""
    return REWORK_SENSE % (document_rel, feedback_rel, (purpose or "").strip())


# WHAT A SHIP TURN IS WOKEN WITH, and it names the mission rather than the diff.
#
# A mission was set going in this workspace from a board somewhere else, told to
# ship itself when it was done, and it is done. The turn's own instructions are
# in `bin/tutor` (`HEADLESS_SHIP_PROMPT`); this is what it is being asked about.
#
# IT SAYS WHO DID THE WORK, because that is the whole reason this is a different
# assistant from the one that did it. The local model is the only one allowed to
# read the fenced directory, so it is the wrong thing to push its own diff: this
# turn is a second pair of eyes that could not have read what it is checking.
SHIP_SENSE = (
    "A mission finished in this workspace and was told to ship itself. It was "
    "run by `%s`, and what it was asked to do was:\n\n%s\n\n"
    "The changes are sitting uncommitted in this repository. You are not the "
    "assistant that made them, and that is deliberate. "
    "THIS IS NOT PART OF THE LESSON: there may be a sitting open on this board "
    "that belongs to somebody else's evening. Write no card, do not open or "
    "archive a sitting, and leave live/state.json, live/cards/ and HANDOFF.md "
    "exactly as you found them."
)


def ship_sense(agent, task):
    """The inbox line for a mission that has been told to ship itself."""
    return SHIP_SENSE % (agent or "an assistant", (task or "").strip())


# WHAT A TURN WOKEN BY A MARK ON A MEETING SLIDE IS TOLD, and the whole of it
# is one word: PROPOSE.
#
# The marks on a meeting deck are not feedback on the deck. Said in these words:
# *"I want to be able to annotate these presentations, but NOT to give feedback
# on them in terms of the presentation -- they're just for a meeting to
# communicate what I've been working on. My mentors, seeing this presentation,
# will give me suggestions on new directions to take -- THAT'S what these
# annotations will serve as."* So the ink is input to what the workspace does
# next, and the slide it is on is which workspace, because there is one frame
# per workspace.
#
# IT MAY NOT APPLY THE DIRECTION, and that is the point of the whole route.
# `direction.write` at the root, a new sitting that ARCHIVES the lesson, the
# last turn's note forgotten and the assistant REPLACED -- two of those are
# destructive, and doing them unattended to five workspaces because somebody
# drew on five slides is the worst outcome available here. So this turn reads
# the marks, works out what is being suggested, and puts ONE card on the board
# saying what it would change. The person taps ⟳ rethink if they agree.
DIRECTION_MARK_SENSE = (
    "SOMEBODY MARKED UP A SLIDE ABOUT THIS WORKSPACE IN A MEETING, and those "
    "marks are a SUGGESTED NEW DIRECTION rather than a complaint about the "
    "slide. The deck is the one at `%(deck)s`; it is a throwaway communication "
    "tool and nothing about it is yours to fix.\n\n"
    "The slide was page %(pages)s, and it said what had landed in this "
    "workspace %(since)s. Their marks on it are here:\n%(images)s\n"
    "OPEN EVERY IMAGE. The marks are the suggestion; the page number alone "
    "says nothing about what they point at.\n\n"
    "DO THIS, AND STOP AT THE END OF IT:\n"
    "1. Read the marks, and read what this workspace is actually doing -- the "
    "plan file the briefing names, the map, and DIRECTION.md if there is one.\n"
    "2. `board write` ONE card, under 200 words, that says: what you read the "
    "marks as asking for, the ONE sentence of new direction you would set, what "
    "in the present plan it would make pointless, and the one thing you need "
    "from them to be sure. Plain words, no headings.\n"
    "3. End the turn.\n\n"
    "YOU ARE PROPOSING, NOT APPLYING. Do not write or edit DIRECTION.md, do not "
    "rewrite the plan, do not redraw the map, do not open or archive a sitting, "
    "and do not touch live/state.json. The direction changes when they tap "
    "⟳ rethink on this board and not before -- say so in the card, and put "
    "the sentence you would set in it in a form they can use as it stands. If "
    "the marks are illegible or say nothing you can act on, the card says that "
    "instead; guessing at a direction is worse than asking."
)


def direction_mark_sense(deck_rel, pages, images, since=""):
    """The inbox line for one workspace's marked slide.

    `pages` are the page numbers of this workspace's marked slides and `images`
    are the repository-relative pictures of the ink on them -- the picture, not
    the coordinates, because the coordinates are no use to a reader.
    """
    said = ", ".join(str(p) for p in pages) or "?"
    shown = "\n".join("  - page %s: `%s`" % (p, img) for p, img in images) \
        or "  - (no picture was saved of the marks)"
    return DIRECTION_MARK_SENSE % {
        "deck": deck_rel, "pages": said, "images": shown,
        "since": ("since %s" % since) if since else "recently",
    }


# WHAT A DOCUMENT ASKED FOR MID-SITTING IS WOKEN WITH, and the whole of the
# difference from a make sitting is WHERE IT LANDS.
#
# A make sitting puts the sections on the board one at a time, because there the
# document IS the evening. One asked for ALONGSIDE a lesson must not push the
# lesson off the glass: somebody is mid-proof, and streaming a deck's slides into
# their transcript is the interruption the whole library surface exists to avoid.
# So this turn writes the document, compiles it, and says nothing on the board --
# the library is where it appears, and correcting it is the library's own loop.
#
# IT TAKES THE MAKE METHOD WHOLE, because everything else about writing one is
# unchanged: the subject rather than the sitting, sections rather than a dump,
# `writeups/<slug>/`. `MAKE_SENSE` is that method and is appended by
# `writeup_sense` rather than restated, or the two drift.
#
# THE SCOPE IS THE EVENING UNLESS SOMETHING ELSE IS NAMED, and that is the
# difference from the map's own route. A box tapped on the map opens a make
# sitting scoped to the box; this is the ask that had no route at all -- "write up
# the four things we just covered" -- so the default is the concepts the cards
# covered, read back with `board recap --all`.
WRITEUP_ASK_SENSE = (
    "A DOCUMENT HAS BEEN ASKED FOR FROM THE SITTING ON THIS BOARD, and THIS "
    "TURN IS NOT PART OF THE LESSON. Nobody is waiting at a board for a card. "
    "What they asked for is %(what)s.\n\n"
    "WHAT IT IS ABOUT: %(about)s\n\n"
    "Write it, compile it, and end the turn. It appears in the LIBRARY, which is "
    "where they will read it and where they will say what is wrong with it -- so "
    "there is nothing to put on the board and nothing to show them a section at "
    "a time.\n\n"
    "HOW TO WRITE ONE FOLLOWS, AND EVERY LINE OF IT ABOUT THE DOCUMENT HOLDS. "
    "What follows is the method a make sitting is given, and it opens by calling "
    "itself one -- read it as the method for this document rather than as a "
    "statement about this sitting, which is unchanged and is not a make "
    "sitting. THE LINES ABOUT CARDS ARE THE ONES THAT DO NOT APPLY, and they "
    "are the only ones: showing it to them a section at a time, saying in every "
    "card where the file is, and asking in your first card what it should be "
    "about. You write no card at all, and what it is about is already named "
    "above. Everything else -- what the document IS, what it may cover, the "
    "directory it goes in -- holds exactly as written.\n\n"
    "**Write no card.** Do not run `board write`, do not run `board open`, do "
    "not touch `live/state.json`, `live/cards/` or `HANDOFF.md`, and do not run "
    "`board wait`. There is a lesson on this board, it belongs to somebody's "
    "evening, and the aim of it has not changed: leave every part of it exactly "
    "as you found it. End the turn when the document is written and built.\n\n"
)

# What the scope sentence says when nobody named one. The topic list is the card
# titles and `board recap` is the one call that reads them back -- see
# `cmd_recap` in `bin/board`, which exists so that a turn does not read a lesson
# one card at a time.
WRITEUP_EVENING = (
    "THE CONCEPTS THIS SITTING COVERED, and nothing else about the sitting. "
    "Read the lesson back with `board recap --all` -- one call, not one per "
    "card -- and take the list of topics off the cards. Explain each of them "
    "from scratch for somebody who was not in the room. Not the order they were "
    "taught in, not the questions asked, not the answers given, and not who got "
    "what wrong."
)


def writeup_sense(makes, about=""):
    """The inbox line for a paper or a deck asked for from any sitting.

    `about` is what they said it was about, where they said anything. Where they
    did not, the scope is the evening -- which is the ask this route exists for
    and is the one a make sitting cannot express.
    """
    said = (about or "").strip()
    return (WRITEUP_ASK_SENSE
            % {"what": ("a DECK of slides" if makes == "slides" else "a PAPER"),
               "about": said or WRITEUP_EVENING}) + MAKE_SENSE


def session_sense(repo, doing=None):
    """What this sitting is, wrapped in the two rules that hold for all of them.

    HOW IT READS comes first, because it governs every card this turn writes and
    a rule about writing is no use arriving after the thing to write about. WHAT
    ORDER TO WORK IN comes last, because it overrides a rule `live/TEACHING.md`
    states three times in capitals, and an override that arrives before the thing
    it overrides is an override nobody applies.

    Everything between them is `_session_sense`, which is the sitting itself.

    `doing` is answered from the sitting unless a CALLER knows better, and one
    does: a step handed over is a doing turn inside a coaching sitting, and the
    sitting is unchanged on purpose. Asking the state would say `teach`, which
    is right about the sitting and wrong about this turn.
    """
    st = repo.state()
    said = PLAIN_SENSE + _session_sense(repo)
    # A turn whose product is a CHANGE rather than a card: the code written for
    # them, a paper, a deck. Whether it says so through the sitting's aim, the
    # kind of sitting, or the stance -- all three mean the same thing about the
    # order the turn happens in.
    if doing is None:
        aim = config.clean_aim(st.get("aim"))
        doing = (st.get("session") == "make"
                 or (aim and config.AIM_STANCE.get(aim) == "do")
                 or (st.get("session") in (None, "", "lecture")
                     and config.stance_for(repo.root, st) == "do"))
    return said + (DOING_SENSE if doing else "")


def _session_sense(repo):
    """What this sitting is, in a sentence an assistant can act on.

    `board open` takes a label -- "Ch 1 -- groups, fields and vector spaces" --
    and it is the only thing on the board that says where a cold start should
    start. If nobody set one, say that too, and say where to look instead: a
    course orders itself somewhere, and guessing is how a course gets opened in
    the middle.

    One method, whatever is in the repository. What the repository decides is
    where the exercises come from -- `where_sense` -- and whether it asked for
    the work to be done rather than set -- `stance_sense`. Neither of those is a
    different sitting, and there is no longer any way to declare one.

    The stance now comes from the SITTING where the sitting names one, and from
    the repository otherwise. That is not a second mode either: every word about
    the shape of a turn is unchanged, and what moved is only which of two
    answers a repository with both kinds of work in it is giving today.
    """
    st = repo.state()
    kind = st.get("session") or "lecture"
    chapter = (st.get("chapter") or "").strip()

    # What the repository declared, and what THIS SITTING actually runs under --
    # which are the same thing until somebody says otherwise, and are allowed to
    # differ because a real project does not have one answer for all of its work.
    declared = config.read_config(repo.root).get("stance") or "teach"
    stance = config.stance_for(repo.root, st)
    doing = stance_sense(stance, chosen=bool(config.clean_stance(st.get("stance"))),
                         declared=declared)

    # The two sittings that are held over a scope the student chose are settled
    # first, because each says its own thing about where the work comes from --
    # and because neither of them is affected by a stance. A review asks and a
    # walkthrough reads; there is nothing to write either way, so a repository
    # that wants its code written does not get it written into one of these.
    if kind == "review":
        return review_sense(repo, st) + node_sense(repo, st) + aim_sense(st)
    if kind == "walk":
        return walk_sense(repo, st) + node_sense(repo, st) + aim_sense(st)

    # A sitting whose product is a document. It takes none of the method above:
    # there is no exercise, nothing is handed in, and the stance question -- who
    # writes the code -- does not arise when what is being written is prose.
    #
    # KEYED ON THE PRODUCT, NOT ON THE KIND OF SITTING. This used to be reached
    # only through `kind == "make"`, so an aim of `paper` chosen mid-lesson got
    # the one sentence in `AIM_MEANS` and none of the method: no sections, no
    # showing each one, no file kept in the repository. The aim is the thing a
    # person actually taps, so it is the thing this turns on.
    mine = config.clean_aim(st.get("aim"))
    if kind == "make" or mine in ("paper", "slides"):
        makes = (st.get("makes")
                 or ("slides" if mine == "slides" else "paper")).strip().lower()
        said = MAKE_SENSE
        said += ("What they asked for is %s."
                 % ("a DECK of slides" if makes == "slides" else "a PAPER"))
        if chapter:
            said += " It is about %r." % chapter
        return said + node_sense(repo, st) + aim_sense(st, mine or makes)

    # Whether this repository follows a book, which is the ONLY question about a
    # subject anything here still asks. A course with a syllabus has its
    # exercises written for it; one without has to be told where to look, and
    # being told is what stops it inventing chapters out of a README.
    book = syllabus.opening(repo.root)

    # In a headless session this line is the whole prompt, so it has to carry the
    # pointer to the method as well as the pointer to the place.
    how = (METHOD_SENSE if kind == "homework"
           else METHOD_SENSE + where_sense(book, repo.root))
    # Every sitting that reaches here hands something in, so every one of them
    # has a document to fill. The two that do not -- a review and a walkthrough
    # -- returned above, each saying in its own words that the lesson is the
    # record.
    how += WRITEUP_SENSE
    how += doing
    how += reading_sense(repo)
    how += results_sense(repo)

    # WHAT THIS SITTING IS FOR, RESOLVED: its own aim, the workspace's, or its
    # family's default in `atlas.json`. Everything from here down is a lecture or
    # a homework sitting -- the two a person reaches without going through the
    # map -- and before this they carried no style at all, so they ran on stance
    # alone, which is `teach` nearly everywhere and is the wrong answer for a
    # project. It is on every return below, or the sitting it is missing from is
    # the one that has no style.
    for_it = aim_sense(st, config.aim_for(repo.root, st))

    if kind == "homework":
        st_hw = homework.status(repo.root, st)
        if st_hw and st_hw.get("name"):
            sheet = st_hw.get("assignment") or []
            where = ("The assignment sheet is at %s -- read it and do exactly the "
                     "problems it assigns, all of them, in order." % sheet[0]) if sheet else (
                     "No assignment sheet is filed under %s; ask which problems are "
                     "assigned before teaching anything." % os.path.dirname(st_hw["rel"]))
            return (how + "This is a HOMEWORK sitting on %s (%s). The problems are "
                    "assigned, not yours to choose. %s Transcribe each statement "
                    "before you teach it." % (st_hw["name"], st_hw["rel"], where)
                    + for_it)

    if chapter:
        return (how + "This sitting is labelled %r and it is a %s. Start there."
                % (chapter, kind)) + node_sense(repo, st) + for_it
    # A course that follows a book says so on disk. Naming its actual first
    # chapter beats telling an assistant to work it out, which is what produced
    # a Galois course opened at field extensions -- chapter four.
    if book:
        every = syllabus.chapters(repo.root)
        return (how + "This sitting is a %s and carries no chapter label. This course "
                "follows a book and orders itself in %d chapters; the first is "
                "%s. Open there unless HANDOFF.md says otherwise, and name the "
                "chapter you are opening in your first card. Do not start from "
                "whatever you consider the foundation of the subject -- start "
                "where the book starts."
                % (kind, len(every), syllabus.label(book))) + for_it
    return (how + "This sitting is a %s and carries no label of its own, so the only "
            "thing that says where to start is what the repository points at -- "
            "read that before your first card, and say in that card what you are "
            "opening and why. Do not guess from the subject and do not survey the "
            "repository for an agenda of your own." % kind) + for_it
