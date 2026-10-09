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

A session's MODE says who writes the code: `TEACH_SENSE` or `DO_SENSE`, one
paragraph each (`mode_sense`). In teach mode the tutor picks the method from
the conversation, and board/TEACHING.md has a section for each: a lesson, a
homework set, a test review, a walkthrough, coaching, or a document.
"""

import os

from . import fenced, plain
from .course import config, homework, library, walk


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
    # ONE STEP HANDED OVER, AND THE SESSION STAYS IN TEACH. Asked for as *"in
    # coach coding mode, I still want to be able to have a 'fuck this, you do
    # this step' option."* `handover_sense` names the card and says what to
    # write; this is what the tap meant.
    "handover": "they do not want to type this one. You write it -- this step "
                "and no more -- and then carry on coaching. The mode has not "
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
    # THE GLASS TYPESETS. `board.js` hands every card to KaTeX with `$...$` and
    # `$$...$$` as its delimiters, and has since the board was written -- so a
    # turn that writes `sum_i w_i x trd_i` in prose has not avoided TeX, it has
    # shipped the ugly half of it. Reported off a doing turn's card in TRD-EHR:
    # "it should have rendered some things in LaTeX ... I just see some ugly
    # latex-esque coded math things when it gets into the weighting."
    "MATHEMATICS IN A CARD IS TeX, NOT ASCII. The board typesets `$...$` and "
    "`$$...$$`. A Greek letter spelled out, a sum written `sum_i`, a product "
    "written as the letter `x`: it reaches the glass as ugly source.\n"
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


# THE WORK IS ALREADY SCORED, and a turn that does not look cannot say whether
# it won -- nor can anybody reading its card. Most workspaces here keep a
# measure: the check they run, the number their plan quotes.
#
# In every briefing rather than in one kind of sitting, for `PLAIN_SENSE`'s
# reason: a lesson invents a number as readily as a change does.
#
# SCOPED, because plenty of sittings have no check to run. A chapter of group
# theory is scored by nothing, and a rule with no referent is answered anyway --
# a sentence of the card spent saying there is no measure.
#
# The verb is RUN. A number read off the plan is the number BEFORE, so a turn
# that quotes it twice has measured nothing.
MEASURE_SENSE = (
    "NAME THE MEASURE THIS WORK ALREADY HAS, where it has one -- the check the "
    "workspace runs, the number the plan quotes. RUN IT before and after, and "
    "say what it said. Name a gap you cannot fill; an invented number is worse "
    "than a hole. "
)


METHOD_SENSE = (
    "Follow board/TEACHING.md, and the rule it all follows from: THE LESSON IS "
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
# `board/TEACHING.md` has said so since it was written -- "once an answer is
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
# In every teach-mode session, whatever the method: a lesson, a homework set, a
# walkthrough, coached code, a review. Every agreed answer to a question the
# tutor posed goes in. `board writeup` makes the file the first time.
WRITEUP_SENSE = (
    "THE WRITE-UP IS PART OF THE TURN THAT AGREES AN ANSWER. The moment their "
    "answer to a question you posed is agreed correct -- not before, and before "
    "you pose the next one -- run `board writeup add <label>` with the "
    "STATEMENT, a line `---`, then THEIR agreed argument on stdin (a quoted "
    "heredoc). It writes both into the session's write-up (the bound homework "
    "set, else `docs/<session>/writeup.tex`), files their newest sent page into "
    "handwritten/ (`--turn tNNNN` for another), and rebuilds the PDF. A session "
    "bound to no subject is refused. Code goes in fenced ``` blocks. "
    "COMPILING IS YOURS, not theirs -- if the build fails, fix it, and put the "
    "LaTeX error on the board rather than the word 'failed'. Never write a "
    "solution they have not produced, and never leave the write-up for the "
    "end: a session is abandoned far more often than it is finished tidily. "
    # AND NEVER TELL THEM TO WRITE IT UP. A card in Galois Theory said "two
    # words to add when you write it up", which is two failures in one clause:
    # it hands over an errand that does not exist -- the document is the tutor's
    # -- and it DEFERS A CORRECTION, because the missing word was a fact about
    # the proof rather than a note for later. In headless this string is the
    # whole prompt, so the rule has to be here and not only in the document.
    "NEVER TELL THEM TO WRITE IT UP: the document is yours, so report what the "
    "file NOW SAYS rather than handing them an errand. Where the missing words "
    "are a CORRECTION, make it in the write-up in this same turn and say on the "
    "card what was wrong. "
)


# WHO WRITES THE CODE: the session's mode, one paragraph each. `session.json`
# `mode` is the only answer, and it changes only by `board mode`, `POST /mode`,
# or the tutor obeying "do it". Nothing infers `do`.
TEACH_SENSE = (
    "THIS SESSION IS IN TEACH MODE. You do not write the code or the proof "
    "being learned; they do. Pick the method from the conversation; "
    "board/TEACHING.md has a section for each: a lesson, a homework set, a "
    "test review, a walkthrough of code that already exists, coaching, or a "
    "document. You still "
    "write the plumbing yourself: figures, reshaping, serialization, "
    "scaffolding. When they tell you to do the work -- \"do it\", "
    "\"just write it\" -- run `board mode do` first, then do it. "
)

# Where a turn that changes the board's own code works: a git worktree here,
# never the main checkout (`.githooks/pre-commit` refuses that commit).
WORKTREES = "/Users/mikeyferguson/Developer/Atlas-wt/"

DO_SENSE = (
    "THIS SESSION IS IN DO MODE: you write the code yourself, run what needs "
    "running, and commit when it is right. Do not withhold an implementation "
    "and do not ask them to type it. The card is a report rather than an "
    "exercise -- what you changed, what it does now, what you ran and what came "
    "back, and the one decision or check you need from them. Still one card, "
    "still short, and it still stops and waits. Say what you did NOT verify -- "
    "a card claiming a job ran when it was only submitted is worse than no "
    "card. Run the subject's check as `board check`, from where you are. NEVER "
    "EDIT A FILE UNDER `board/` IN THE MAIN CHECKOUT, which serves the iPad "
    "live: make a git worktree under %s, change and test it there, then merge "
    "it (a commit touching board/ in the main checkout is refused). When they "
    "ask to be taught instead, run `board mode teach`. " % WORKTREES
)


# WHERE THE TUTOR MAY READ, in every session and both modes. `walk.resolve`
# falls back to the Atlas root, and `walk.READ_ONLY` is what it marks read-only.
TRACE_SENSE = (
    "YOU MAY TRACE ANY PATH IN ATLAS, not only this subject's: the board's own "
    "code, a vendor tree, another course or project. Read it where it is and "
    "quote it with its path. %s ARE READ-ONLY, in do mode too: never edit, "
    "create or commit a file under them in this checkout -- the board is "
    "changed only in a separate git worktree, and a vendor tree is pulled at "
    "a commit. Never look inside a "
    "directory named %s. "
    % (" and ".join(d + "/" for d in walk.READ_ONLY),
       ", ".join(fenced.NEVER))
)


def mode_sense(mode):
    """The paragraph for the session's mode: `DO_SENSE` for do, else
    `TEACH_SENSE`."""
    return DO_SENSE if mode == "do" else TEACH_SENSE


# THE SHAPE OF A TURN THAT DOES THE WORK, and it is the opposite shape to a
# teaching turn's.
#
# `board/TEACHING.md` says that a teaching turn's card is written before
# anything else happens. That rule is right and it is a TEACHING turn's
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
    "board/TEACHING.md says to write the card before anything else; that is a "
    "teaching turn's rule, where the card is the work. Here the work is the "
    "change, and a card written before it can only describe an intention. Do it "
    "in this order, and do not stop before the end:\n"
    "1. `board write pending` ONE sentence saying what you are about to do, in "
    "plain words. It lands at once, so the board is never blank. Keep the path "
    "it prints.\n"
    "2. DO THE WORK. Write the code. Run it. Read what came back. Fix what it "
    "showed you. If something cannot be run here, run what can and say which.\n"
    "3. `board write --over <that path>` with the REPORT: what you changed, "
    "which files, what you ran, what it said, and what is left. Name every "
    "file you changed and left uncommitted. Plain words, under 200, no "
    "headings. A turn that exits with the placeholder still up is woken to "
    "write it.\n"
    "4. Then stop. Ask something only if you are actually blocked -- if you can "
    "pick a reasonable answer and say which you picked, do that instead. A "
    "question is not how a doing turn ends by default.\n"
    "Never hand back a plan of what you would do as though it were the work. If "
    "the job is genuinely too big for one turn, do the FIRST PART OF IT and "
    "report that, rather than describing all of it and doing none.\n"
    "AND WHERE THE NEW THING GOES: a new thing goes in a module named for the "
    "one job it does, and if that means moving something first, move it first. "
    "Whoever traces this workspace reads its modules and what each imports -- "
    "so a module that does six unrelated things reads as one knot with eleven "
    "arrows into it and teaches nobody anything. The structure is a mirror, and "
    "the failure is the module rather than the reader. `helpers`, `utils`, "
    "`common` and `misc` are four spellings of nobody decided. Python will let "
    "you append anything to any file and it will run; getting away with it is "
    "not the test, and the test is whether a trace of the module can say what "
    "it is for. board/TEACHING.md says the same under `Where a new thing "
    "goes`. "
)


# WHAT A DOING TURN IS ALLOWED TO CHANGE, and it is the code rather than what
# the code printed. A wrong artifact is a wrong rule with a file under it, so
# the file is a symptom and hand-editing it treats the symptom: nobody can
# reproduce the edit, nobody without the inputs can review it, and the next run
# of the module puts the old answer back.
#
# Carried by every turn whose product is a change -- the code written for them,
# a paper, a deck, a revision -- because each of them can be
# finished by hand and each of them is worthless when it is.
RULE_SENSE = (
    "AND FIX THE RULE, NEVER ITS OUTPUT. Where a wrong thing was produced by "
    "code, the code is what is wrong: fix the module that produces it and run "
    "it again. Editing the output by hand is not a smaller version of the same "
    "fix -- nobody can reproduce it, nobody can review it without the inputs, "
    "and the next run wipes it. That holds however close to right you could get "
    "the file by hand. If the rule cannot be written, say so on the card and "
    "name what stops you. AND WRITE WHERE THE CODE ALREADY WRITES, never over "
    "an input you are scored against: overwrite it and the measure agrees with "
    "you for free. "
)


# WHAT A HANDED-OVER STEP IS, and the one thing it must not come back as.
#
# Coaching is one step per card, named in English, typed by them. The tap that
# reaches this hands over ONE of those steps and leaves the session in teach, so
# the turn it wakes is a doing turn inside a teach session -- `DOING_SENSE`
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
    "widen it into the rest of the job, and do not change the mode of this "
    "session -- they asked for one step, not for the wheel.\n"
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


def where_sense(book, root=None, st=None):
    """Where the exercises come from, which is the only thing a subject decides.

    A course that follows a book has them at the end of a section. A subject
    that does not takes them from its TUTOR.md, whose "Now" and "Open
    decisions" the brief carries. The subject's README.md is the owner's and
    is never the agenda (D13).
    """
    if book:
        return ("Read the section's exercises before you teach anything and "
                "choose a manageable few -- three to five -- saying which and "
                "why in your first card. ")
    return (
        "This subject does not follow a book, which changes only where the "
        "exercises come from. What comes next is TUTOR.md's \"Now\", in this "
        "brief; it outranks anything you would choose. Do not manufacture a "
        "curriculum out of the README or a survey of the repository. Set the "
        "three to five exercises that work needs, saying which and why in your "
        "first card; if \"Now\" names nothing, or the step needs their decision, "
        "ask in that card. "
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
        found = library.drawer(repo.root)
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
        found = library.figures(repo.root)
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
        "lesson. The most recently written ones are: %s. ANY OTHER FIGURE "
        "under this workspace's results can go in a card by its path relative "
        "to the workspace root instead of an id -- for example "
        "![the sweep](/result/results/some_dir/some_figure.png) -- and the board "
        "turns the path into the id. When you are asked to display a figure, "
        "find it, open it, and put it in the card; show it again in a later "
        "card whenever the question is about it. These are the "
        "pipeline's output, not yours: show one to ask about what it shows, "
        "and say what you are looking at UNDER it. Never show a figure you "
        "have not opened and read yourself, and never let one stand in place of "
        "the question. One figure per card at most. " % (found[0]["id"], named))


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


# HOW A DOCUMENT IS WRITTEN: the method a `[writeup]` turn is given for a deck
# or a paper asked for from the Make menu. `writeup_sense` appends it.
#
# TWO QUESTIONS, NOT ONE. HOW it reads is fixed: the subject, explained, never
# the session narrated -- stated as a refusal, because a preference in a prompt
# is what produced the narration. WHAT it covers is not: "a deck about the four
# things this session covered" is a legitimate ask.
MAKE_SENSE = (
    "THE PRODUCT IS A DOCUMENT, not an answer. "
    "HOW IT READS IS FIXED, AND IT IS NEVER A NARRATION OF THIS SITTING. The "
    "document is an EXPLAINER: here is how this works, and here is the "
    "mathematics, written for somebody who was not in the room. So: no first "
    "person, no 'we covered', no 'the student then', no 'as we saw above', and "
    "no reference at all to this session, its cards, its questions, or the "
    "person answering them. If a concept was taught by hand-checking three "
    "examples, the document explains the concept and shows the examples -- it "
    "does not narrate the hand-check. A write-up of the evening is the one "
    "thing this document must not be. "
    "WHAT IT COVERS IS A DIFFERENT QUESTION, and its scope may be A PART OF THE "
    "REPOSITORY, THE CHAPTER, OR THE WHOLE EVENING. Where the ask names which, "
    "that is the scope, and not everything else that came up while you were "
    "looking at it. WHERE THE SCOPE IS THE EVENING it is the concepts this "
    "sitting covered and nothing else about it: read the lesson back with "
    "`board recap --all`, take the list of topics off the cards, and explain "
    "each one from scratch. Not the order they were taught in, not the "
    "questions, not the answers, not who got what wrong. "
    "THE FILE IS THE ONE THIS LINE NAMES, under the subject's `docs/<slug>/`, "
    "with its `figures/` beside it: the board made that directory and its "
    "doc.json, and finds the document by that name and no other. ")


# WHAT A REVISION TURN IS WOKEN WITH, and it names both files.
#
# The turn's own instructions are in `runner/prompts/` (`HEADLESS_REVISE_PROMPT`) and
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
    "`%s`. Read both, and decide what each mark and line asks for: an edit to "
    "the document, which you make in its source, or where the work goes next, "
    "which you write in the subject's TUTOR.md with `board memo` -- your "
    "choice, made per request. Record what you did the way your instructions "
    "say: in the round's ledger where one is named below, and otherwise at the "
    "bottom of that feedback file. "
    "THIS IS NOT PART OF THE LESSON: there may be a sitting open on this board "
    "that belongs to somebody else's evening. Write no card, do not open or "
    "archive a sitting, and leave the session's state, its cards and HANDOFF.md "
    "exactly as you found them."
)


def revise_sense(document_rel, feedback_rel, brief="", ledger="", ids=(),
                 source=""):
    """The inbox line for one round of feedback on one document.

    `brief` is the deck's `_brief.md` where the document is a deck with a
    brief beside it (the meeting deck), and "" for everything else. See `DECK_BRIEF_SENSE`. `ledger` and
    `ids` are the round's requests; see `LEDGER_SENSE`. `source` is the `.tex`
    or `.md` the document is built from; see `BUILD_SENSE`.
    """
    return (REVISE_SENSE % (document_rel, feedback_rel) + _build(source)
            + _deck_brief(brief) + _ledger(ledger, ids) + MEASURE_SENSE
            + RULE_SENSE)


# HOW THE DOCUMENT IS REBUILT, named with its source. The PDF, and the `.docx`
# of a `.md`, are built from the source, so an edit made anywhere else is lost
# on the next build. One builder for every document: `board build`.
BUILD_SENSE = (
    " The source is `%s`: edit that file, then rebuild it with "
    "`board build %s`, which writes the built files beside it. "
)


def _build(source):
    source = (source or "").strip()
    if not source.lower().endswith((".tex", ".md")):
        return ""
    return BUILD_SENSE % (source, source)


# A ROUND IS A LIST OF REQUESTS, AND EVERY ONE OF THEM IS ANSWERED.
#
# The owner's words: *"I need some nifty way to keep track of what each edit
# request was, and what was done to address it, so that I don't have to read
# the whole fucking paper again."* So the round was split into requests when it
# was filed (`course/ledger.py`), each has an id, and the turn answers each id
# in the ledger beside the note. The line names the file and the ids, because
# the ids are the contract: the board validates that every one was answered and
# shows an unanswered one as exactly that.
LEDGER_SENSE = (
    " THIS ROUND IS %d REQUEST%s, BY ID: %s. They are listed in `%s`, the "
    "round's ledger, and under the same ids in the feedback file. Answer EVERY "
    "id in that ledger's `answers`: a disposition (done, partly, not done or "
    "pushed back), one sentence of what you did -- for not done and pushed "
    "back, the reply the owner reads beside their ink -- and for done and "
    "partly the "
    "new wording of the passage you changed, copied exactly from the source. A "
    "request you could not find is still answered -- not done, saying so. The "
    "board writes `## What was changed` from those answers. "
)


def _ledger(ledger, ids):
    ledger = (ledger or "").strip()
    ids = [str(i) for i in ids or ()]
    if not ledger or not ids:
        return ""
    shown = ids if len(ids) <= 40 else ids[:40] + ["and %d more" % (len(ids) - 40)]
    return LEDGER_SENSE % (len(ids), "" if len(ids) == 1 else "S",
                           ", ".join(shown), ledger)


# A DECK WITH A BRIEF IS CORRECTED WITH INK, AND THE INK MAY ASK FOR MORE.
#
# `HEADLESS_REVISE_PROMPT` says *do not widen it*, which is right for a paper
# whose scope somebody chose and wrong for this: the brief chose what goes in,
# the tutor planned the slides, and a ring with "add the ROC curve" beside it is
# the correction. So the turn is told where the deck's scope is written down --
# the brief the server wrote before the deck existed -- that an addition asked
# for in ink is the feedback rather than a widening, how to fetch a figure the
# brief only catalogues, and that a frame stays one page, because a mark finds
# its slide by page number.
DECK_BRIEF_SENSE = (
    " THIS DECK WAS COMPOSED FROM A BRIEF, and what it covers is written down "
    "in `%s`: read it before changing anything. Ink or a note asking for "
    "something to be ADDED is the feedback, not a widening -- add it, from the "
    "sources the brief names; the sessions' cards and transcripts it points "
    "at are yours to read for this. A figure its catalog lists and the deck "
    "does not have yet is fetched with `board deckfig %s <subject> <result id>`, "
    "which copies it into the deck's figures/ and prints the path to "
    "\\includegraphics; one the catalog does not list is found by giving a "
    "word from its file name in place of the id. Open the image before using "
    "it. Something asked to "
    "come OUT comes out. Keep one page per frame (no allowframebreaks): the next "
    "round of ink finds its slide by page number. "
)


def _deck_brief(brief):
    brief = (brief or "").strip()
    if not brief:
        return ""
    return DECK_BRIEF_SENSE % (brief, os.path.dirname(brief) or ".")


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
    "Read both files, rework the document to that purpose, and record what you "
    "did the way your instructions say: in the round's ledger where one is "
    "named below, and otherwise at the bottom of that feedback file. Its "
    "present structure, its "
    "order and its sections are yours to change. "
    "THIS IS NOT PART OF THE LESSON: there may be a sitting open on this board "
    "that belongs to somebody else's evening. Write no card, do not open or "
    "archive a sitting, and leave the session's state, its cards and HANDOFF.md "
    "exactly as you found them."
)


def rework_sense(document_rel, feedback_rel, purpose, brief="", ledger="",
                 ids=(), source=""):
    """The inbox line for an overhaul of one document. `brief`, `ledger`, `ids`
    and `source` as for `revise_sense`."""
    return (REWORK_SENSE % (document_rel, feedback_rel, (purpose or "").strip())
            + _build(source) + _deck_brief(brief) + _ledger(ledger, ids)
            + MEASURE_SENSE + RULE_SENSE)


# WHAT A DECK OR A PAPER ASKED FOR FROM A SESSION IS WOKEN WITH.
#
# The Make menu asks for one alongside a lesson, which must not be pushed off
# the glass: this turn writes the document, builds it, and writes no card. The
# strip says where it got to, and the library is where it is read and
# corrected. The method is `MAKE_SENSE`, appended rather than restated.
#
# THE SCOPE IS THE SESSION UNLESS SOMETHING ELSE IS NAMED: "write up the four
# things we just covered" -- read back with `board recap --all`.
WRITEUP_ASK_SENSE = (
    "A DOCUMENT HAS BEEN ASKED FOR FROM THIS SESSION, and THIS TURN IS NOT PART "
    "OF THE LESSON. Nobody is waiting at a board for a card. What they asked "
    "for is %(what)s.\n\n"
    "WHAT IT IS ABOUT: %(about)s\n\n"
    "Write it, build it, and end the turn. It appears in the LIBRARY, which is "
    "where they will read it and say what is wrong with it.\n\n"
    "**Write no card.** Do not run `board write`, do not run `board open`, and "
    "do not touch the session's state, its cards or `HANDOFF.md`. The lesson on "
    "this board belongs to somebody's evening, and its mode has not changed: "
    "leave every part of it exactly as you found it. End the turn when the "
    "document is written and built.\n\n"
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

# WHAT EACH PRODUCT IS ON DISK. A deck is a beamer `.tex`; a paper is Markdown,
# which `board build` turns into a .docx (and a PDF where an engine exists).
FILE_SENSE = {
    "slides": ("THE FILE IS `%(source)s` (from the Atlas root, where this turn "
               "runs), that name exactly. A DECK IS A BEAMER `.tex`: "
               "`\\documentclass{beamer}`, one page per frame, no \\pause and "
               "no overlays. "),
    "paper": ("THE FILE IS `%(source)s` (from the Atlas root, where this turn "
              "runs), that name exactly. A PAPER IS MARKDOWN: a `# ` title, "
              "sections, and maths in `$...$`; it is built to a .docx. "),
}
DOC_BUILD_SENSE = ("When it is written, run `board build %(source)s`, and fix "
                   "whatever error it reports before the turn ends. ")


def writeup_sense(makes, about="", source=None):
    """The inbox line for a paper or a deck asked for from any session.

    `about` is what they said it was about, where they said anything. Where they
    did not, the scope is this session. `source` is the file to write, from the
    Atlas root; where it is given, the line names it and `board build`.
    """
    said = (about or "").strip()
    kind = "slides" if makes == "slides" else "paper"
    line = (WRITEUP_ASK_SENSE
            % {"what": ("a DECK of slides" if kind == "slides" else "a PAPER"),
               "about": said or WRITEUP_EVENING}
            + MAKE_SENSE)
    if source:
        line += (FILE_SENSE[kind] + DOC_BUILD_SENSE) % {"source": source}
    return line + MEASURE_SENSE + RULE_SENSE


# WHAT THE MEETING DECK IS ABOUT. Said in these words: *"actually generate a
# professional coherent presentation on my most recent progress"* -- something
# the owner puts in front of their mentors without rewriting it.
# `briefs.write_brief` writes the period's commits, TUTOR.md diffs and ended
# sessions into `_brief.md`; this is the `about` that points at it, and
# `writeup_sense` wraps it in the document method.
#
# THE FILE NAME IS NOT THE WRITER'S TO CHOOSE: the deck is the artifact
# projects/Meetings/docs/meeting/, judged by its doc.json's source.
MEETING_ABOUT = (
    "THE MEETING DECK: a progress presentation to the MENTORS who supervise "
    "these projects, over %(period)s. Everything it may say is in "
    "`%(dir)s/_brief.md` -- read that file first, whole. It has each subject's "
    "commits with their whole messages, how its TUTOR.md changed, the sessions "
    "that ended, and the figures already copied into `%(dir)s/figures/`. The "
    "audience knows the field and saw none of the work. Tell them what was "
    "FOUND, with its number and its figure; what CHANGED in direction, and "
    "why; what is NEXT, in plain words; and what you need FROM THEM. A "
    "changelog is not a presentation: choose the findings, and leave the "
    "housekeeping out. "
    "THE SHAPE: a title slide saying the period exactly as the brief gives it; "
    "one summary slide with each project in one line and its headline number; "
    "then, per project, as many slides as it needs; then one closing slide of "
    "the decisions or asks for the mentors. ONE PAGE PER FRAME: no "
    "allowframebreaks, no \\pause, no overlays. "
    "NO INTERNAL NAMES ON A SLIDE: no commit hashes, no lines copied from "
    "TUTOR.md as typed, no 'his' or 'her' without saying whose (the senior "
    "author, a collaborator), and no links to the board. NUMBERS ONLY FROM THE "
    "SOURCES: every number on a slide must appear in the brief or a file it "
    "names; the board checks each one after the build and lists any it cannot "
    "find beside the deck. "
    "THE FILE IS `%(dir)s/meeting.tex` (`%(full)s/meeting.tex` from the Atlas "
    "root), that name exactly and no other, and it outranks any other file "
    "named above. Write it whole: it replaces the deck before it. Build it with "
    "`board build` on that file. A LaTeX error is yours to fix before the turn "
    "ends."
)


def meeting_about(deck_dir, period, full=None):
    """What the meeting deck is about: its brief, and the period it covers.
    `deck_dir` is relative to projects/Meetings; `full` to the Atlas root."""
    return MEETING_ABOUT % {"dir": deck_dir, "period": period,
                            "full": full or deck_dir}


def session_sense(repo, doing=None):
    """What this sitting is, wrapped in the two rules that hold for all of them.

    HOW IT READS comes first, because it governs every card this turn writes and
    a rule about writing is no use arriving after the thing to write about. WHAT
    ORDER TO WORK IN comes last, because it overrides the card-first rule of
    `board/TEACHING.md`, and an override that arrives before the thing
    it overrides is an override nobody applies.

    Everything between them is `_session_sense`, which is the sitting itself.

    `doing` is answered from the sitting unless a CALLER knows better: a
    `[repair]` turn is a doing turn whatever the session teaches under, and
    `board brief` passes it. Pass `True` or nothing: `False` would take the
    order away from a session whose standing answer is to write the code.
    """
    st = repo.state()
    said = PLAIN_SENSE + MEASURE_SENSE + _session_sense(repo)
    # A turn whose product is a CHANGE rather than a card: a session in do mode.
    if doing is None:
        doing = config.mode_of(st) == "do"
    return said + (DOING_SENSE + RULE_SENSE if doing else "")


def _session_sense(repo):
    """What this sitting is, in a sentence an assistant can act on.

    `board open` takes a label -- "Ch 1 -- groups, fields and vector spaces" --
    and it is the only thing on the board that says where a cold start should
    start. If nobody set one, say that too, and say where to look instead: a
    course orders itself somewhere, and guessing is how a course gets opened in
    the middle.

    One method, whatever is in the repository. What the repository decides is
    where the exercises come from -- `where_sense`. Who writes the code is the
    session's mode -- `mode_sense` -- and nothing else.
    """
    st = repo.state()
    kind = st.get("session") or "lecture"
    if kind not in ("lecture", "homework"):
        # A legacy review, walk or make sitting: the method is the tutor's to
        # pick in teach mode, so it reads as a lecture.
        kind = "lecture"
    chapter = (st.get("chapter") or "").strip()
    doing = mode_sense(config.mode_of(st))

    # Whether this repository follows a book, which is the ONLY question about a
    # subject anything here still asks. A course with a syllabus has its
    # exercises written for it; one without has to be told where to look, and
    # being told is what stops it inventing chapters out of a README.
    book = homework.opening(repo.root)

    # In a headless session this line is the whole prompt, so it has to carry the
    # pointer to the method as well as the pointer to the place.
    how = (METHOD_SENSE if kind == "homework"
           else METHOD_SENSE + where_sense(book, repo.root, st))
    # An agreed answer is written up, in every teach-mode session.
    if config.mode_of(st) != "do":
        how += WRITEUP_SENSE
    how += doing
    how += TRACE_SENSE
    how += reading_sense(repo)
    how += results_sense(repo)

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
                    "before you teach it." % (st_hw["name"], st_hw["rel"], where))

    if chapter:
        return (how + "This sitting is labelled %r and it is a %s. Start there."
                % (chapter, kind))
    # A course that follows a book says so on disk. Naming its actual first
    # chapter beats telling an assistant to work it out, which is what produced
    # a Galois course opened at field extensions -- chapter four.
    if book:
        every = homework.chapters(repo.root)
        return (how + "This sitting is a %s and carries no chapter label. This course "
                "follows a book and orders itself in %d chapters; the first is "
                "%s. Open there unless TUTOR.md says otherwise, and name the "
                "chapter you are opening in your first card. Do not start from "
                "whatever you consider the foundation of the subject -- start "
                "where the book starts."
                % (kind, len(every), homework.chapter_label(book)))
    return (how + "This sitting is a %s and carries no label of its own, so the only "
            "thing that says where to start is what the repository points at -- "
            "read that before your first card, and say in that card what you are "
            "opening and why. Do not guess from the subject and do not survey the "
            "repository for an agenda of your own." % kind)
