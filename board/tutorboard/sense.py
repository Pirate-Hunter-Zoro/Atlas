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

from .course import config, homework, review, syllabus, walk


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
    "they are being asked to prove. One question per turn, then stop and wait. "
    "The only thing that counts is exercises answered. "
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
    "decision or check you need from them. Everything else above holds "
    "unchanged: still one card, still short, still written before the rest of "
    "the work, still one thing per turn, and it still stops and waits. Say what "
    "you did NOT verify -- a card claiming a job ran when it was only submitted "
    "is worse than no card. "
)


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


def where_sense(book):
    """Where the exercises come from, which is the only thing a subject decides.

    A course that follows a book has them at the end of a section. A repository
    that does not is not thereby a different kind of sitting -- it is the same
    lesson whose exercises come from wherever the repository says its work is
    planned. This used to be a whole second method, `code_sense`, and it carried
    a whole second interface with it.
    """
    if book:
        return ("Read the section's exercises before you teach anything and "
                "choose a manageable few -- three to five -- saying which and "
                "why in your first card. ")
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


def session_sense(repo):
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
        return review_sense(repo, st)
    if kind == "walk":
        return walk_sense(repo, st)

    # Whether this repository follows a book, which is the ONLY question about a
    # subject anything here still asks. A course with a syllabus has its
    # exercises written for it; one without has to be told where to look, and
    # being told is what stops it inventing chapters out of a README.
    book = syllabus.opening(repo.root)

    # In a headless session this line is the whole prompt, so it has to carry the
    # pointer to the method as well as the pointer to the place.
    how = METHOD_SENSE if kind == "homework" else METHOD_SENSE + where_sense(book)
    how += doing
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
        every = syllabus.chapters(repo.root)
        return (how + "This sitting is a %s and carries no chapter label. This course "
                "follows a book and orders itself in %d chapters; the first is "
                "%s. Open there unless HANDOFF.md says otherwise, and name the "
                "chapter you are opening in your first card. Do not start from "
                "whatever you consider the foundation of the subject -- start "
                "where the book starts."
                % (kind, len(every), syllabus.label(book)))
    return (how + "This sitting is a %s and carries no label of its own, so the only "
            "thing that says where to start is what the repository points at -- "
            "read that before your first card, and say in that card what you are "
            "opening and why. Do not guess from the subject and do not survey the "
            "repository for an agenda of your own." % kind)
