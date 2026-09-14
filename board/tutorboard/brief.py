"""Everything a cold turn has to know, in one call.

Every turn is a cold turn now, so what a cold start costs is what the course
costs. It used to cost three whole documents: `AI_INSTRUCTIONS.md` (9.1k
tokens in Galois Theory), `live/TEACHING.md` (9.5k) and `HANDOFF.md` (5.4k,
against a documented cap of 350 words), read in three round trips before a word
of teaching was written -- and on a resumed session they then sat in the
conversation for the rest of the evening.

None of that is what a turn actually uses. What it uses is: the method, which
`tutorboard.sense` already states in a paragraph because the board's own
begin-card needs it; the rules of this course that do not bend; where the
student got to; and what the last turn was thinking. That is this file, it is
one round trip, and it is about a tenth the size.

The full documents stay on disk and are named at the bottom of the briefing.
A rule that needs its detail is one grep away, which is the right price for
something a turn needs occasionally and the wrong price for something it needs
never.
"""

import os
import re
import time

from . import carry, direction, handoff
from .course import config
from .course import map as course_map
from .lesson import git as lesson_git


CONTRACT = "AI_INSTRUCTIONS.md"
METHOD = os.path.join("live", "TEACHING.md")

# The one section of a course's contract that every single turn is bound by.
# A contract is a long document written for a person reading it once; this is
# the part of it that decides what a turn may and may not do, and it is the
# only part worth paying for on every turn.
RULES_HEADING = re.compile(r"^(#{1,6})\s*(.*rules that do not bend.*)$",
                           re.IGNORECASE)

# The mechanics of a turn, which changed when a turn became its own session.
# This lives here rather than in `tutorboard.sense` because a turn is the only
# thing that reads the briefing: the method is the same for a person at a
# terminal, the machinery is not.
TURN_SENSE = (
    "This turn is its own session. Nothing you are holding now survives it -- "
    "not the cards, not this briefing, not what you worked out about their "
    "answer. Two things follow.\n"
    "- **Leave a note before you finish**: `board note`, at most 120 words on "
    "stdin, on what you actually READ in their answer and the one thing you are "
    "aiming at next. The lesson is on disk and `board recap` reads it back; your "
    "reading of the lesson is not, and the note is the only place it goes.\n"
    "- **Do not wait, and do not write the handoff.** `board wait` is the "
    "daemon's, not the turn's -- it is already blocked on the student's next "
    "message and will hand it to a fresh turn. `HANDOFF.md` belongs to the "
    "wrap-up turn at the end of the session, which writes it with `board "
    "handoff`; a teaching turn that edits it pays to read it first.\n"
    "Both of those refuse now rather than costing money quietly."
)


def _section(text, pattern):
    """A named section of a markdown document, heading included.

    Ends at the next heading of the same level or shallower, which is what a
    reader means by "that section" and is not what a naive scan to the next `#`
    gives you.
    """
    lines = text.splitlines()
    start = depth = None
    for i, line in enumerate(lines):
        m = pattern.match(line)
        if m:
            start, depth = i, len(m.group(1))
            break
    if start is None:
        return ""
    out = [lines[start]]
    for line in lines[start + 1:]:
        m = re.match(r"^(#{1,6})\s", line)
        if m and len(m.group(1)) <= depth:
            break
        out.append(line)
    return "\n".join(out).strip()


def contract_rules(root):
    """This course's non-negotiables, or "" if it does not name any."""
    try:
        with open(os.path.join(root, CONTRACT), "r", encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return ""
    return _section(text, RULES_HEADING)


def contract_map(root):
    """The contract's top-level sections, one line each.

    Not the contract -- a map of it, so a turn that genuinely needs a rule's
    detail knows which section to open instead of reading the file or grepping
    around in it. Top level only: the `###` headings triple the size of this for
    something a turn reads and does not act on.
    """
    try:
        with open(os.path.join(root, CONTRACT), "r", encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return []
    return [re.sub(r"^##\s+", "", l).strip()
            for l in text.splitlines() if re.match(r"^##\s+\S", l)]



def map_sense(root):
    """One paragraph: is this project drawn, when, and is the drawing still true.

    KEEPING THE MAP TRUE IS PART OF FINISHING A PIECE OF WORK, exactly as
    updating the plan already is, and a rule nobody is reminded of is a rule
    that lasts about three weeks. So the reminder is in the briefing, where
    every turn sees it, rather than in a document a turn is told not to read.
    """
    try:
        info = course_map.written_status(root)
    except Exception:                                        # noqa: BLE001
        return ("the map could not be read, so treat the picture on the board "
                "as derived from the tree rather than as anybody's words.")

    if not info["has"]:
        return ("NOT DRAWN. The board is showing a picture derived from the "
                "directory tree -- honest, and nobody's words. It knows that "
                "directories exist and what imports what; it does not know what "
                "any of it is FOR, which stage of the work a box is, or what is "
                "blocked. If the person asks you to draw the map, or if you are "
                "about to explain this project back to them, write one with "
                "`board map < map.json` -- live/TEACHING.md says how. Name the "
                "boxes the way their README and their plan name them.")

    if info["problems"]:
        return ("live/map.json EXISTS AND IS NOT VALID, so the board has fallen "
                "back to the derived picture and the person cannot see what they "
                "wrote. `board map --show` prints the reason. Fix it before "
                "anything else that touches the map: %s"
                % "; ".join(info["problems"][:3]))

    when = ""
    try:
        when = time.strftime("%d %b", time.localtime(info["written"]))
    except (OSError, ValueError):
        when = ""
    lead = ("DRAWN%s, %d box%s%s. These are the person's own names for their "
            "own work -- use them. Saying `psych_asr/asr` where they wrote "
            "*the typist* is answering in a vocabulary they did not choose."
            % (" " + when if when else "", info["nodes"],
               "" if info["nodes"] == 1 else "es",
               (" -- \"%s\"" % info["title"]) if info["title"] else ""))
    if info["stale"]:
        lead += ("\n%d thing(s) on it no longer match the tree; `board map "
                 "--check` says which. Keeping the map true is part of "
                 "finishing a piece of work, the same way updating the plan is."
                 % info["stale"])
    return lead



def beside_sense(repo):
    """What somebody did to this workspace that you have not been told about.

    THE WORDING IS THE FEATURE. A turn reading this has to come away certain
    that the work described is THE PERSON'S, done somewhere else, with no
    involvement from it -- because the alternative is a turn that reports having
    written code it has never seen, in a card, confidently, with nothing on the
    board able to contradict it. That is the worst failure mode this board has:
    it is invisible from the outside and it makes everything else the tutor says
    worth less.

    So whose work it is, is said in the heading, said again in the sentence, and
    said a third time as an instruction about what to do with it.
    """
    try:
        rec = lesson_git.beside_the_lesson(repo)
    except Exception:                                        # noqa: BLE001
        return ""
    if not rec:
        return ""                       # not a git repository; nothing to say

    commits = rec.get("commits") or []
    files = rec.get("uncommitted") or []
    if not commits and not files:
        return ""                       # SILENT WHEN THERE IS NOTHING. A
                                        # heading over "no changes" is 40 tokens
                                        # of nothing, on every turn, for ever.

    out = ["\n--- what THEY did, away from the board ---"]
    out.append(
        "Work below was done by the PERSON, in their own editor, outside this "
        "board. YOU DID NOT DO ANY OF IT. Do not describe it as something you "
        "did, do not report it as progress you made, and do not assume you know "
        "what is in it -- read the files if the lesson touches them.")

    if commits:
        out.append("")
        out.append("They committed %d thing%s to this workspace:"
                   % (len(commits), "" if len(commits) == 1 else "s"))
        for c in commits[:lesson_git.BESIDE_COMMITS]:
            out.append("  - %s" % c["subject"])
        if len(commits) > lesson_git.BESIDE_COMMITS:
            out.append("  - …and %d more."
                       % (len(commits) - lesson_git.BESIDE_COMMITS))

    if files:
        out.append("")
        out.append("And %d file%s in this workspace %s uncommitted right now:"
                   % (rec["files"], "" if rec["files"] == 1 else "s",
                      "is" if rec["files"] == 1 else "are"))
        out.append("  " + ", ".join(files))
        if rec["files"] > len(files):
            out.append("  (%d more, and the lesson's own live/ is not counted)"
                       % (rec["files"] - len(files)))

    out.append("")
    out.append("If it bears on what you are teaching, open it and teach THAT. "
               "If it does not, say nothing about it at all.")
    return "\n".join(out)


def briefing(repo, sense, chapter=None):
    """The whole cold briefing as one string.

    `sense` is `tutorboard.sense`, passed in rather than imported, because it
    reaches into the course package for the syllabus and the homework sheet and
    this module is imported by things that have already paid for that.
    """
    root = repo.root
    st = repo.state()
    chapter = chapter if chapter is not None else (st.get("chapter") or "")
    out = []

    head = " — ".join(x for x in (st.get("course"), st.get("session"),
                                  st.get("chapter")) if x)
    out.append(head or "no session open")
    if st.get("hw"):
        out.append("homework set: %s" % st["hw"])
    # The stance of THIS SITTING, which is the repository's unless the sitting
    # said otherwise. Both are printed when they disagree: a turn reading
    # "stance: do" in a repository whose file says teach has to be able to see
    # that it is a choice somebody made this evening rather than the standing
    # answer, because the two are written down in different places and only one
    # of them survives the sitting.
    declared = config.read_config(root).get("stance") or "teach"
    stance = config.stance_for(root, st)
    if stance == declared:
        out.append("stance: %s" % stance)
    else:
        out.append("stance: %s  (this sitting only -- tutorboard.json says %s, "
                   "and that is what the next sitting goes back to)"
                   % (stance, declared))

    # WHAT THIS WORKSPACE IS FOR, when they have said so -- above the method,
    # above the contract, above everything. A direction is changed at the moment
    # somebody realises the whole shape of the work is wrong, so every document
    # under this line may have been written for the one it replaced. A turn that
    # reads it last has already believed three of them.
    said = direction.standing(root)
    if said:
        out.append(said)

    out.append("\n--- the method, and what this sitting is ---\n"
               + sense.session_sense(repo))

    rules = contract_rules(root)
    if rules:
        out.append("\n--- %s: the rules that do not bend ---\n%s" % (CONTRACT, rules))

    # The handoff, under the same chapter test the cold prompt used to apply.
    # A handoff about a chapter the student has closed is parked as a side
    # effect of asking, which is why this is asked here and not guessed.
    if handoff.handoff_applies(root, chapter):
        text, _ = handoff.read_handoff(root)
        n = carry.word_count(text)
        out.append("\n--- HANDOFF.md, from the last session (%d words) ---\n%s"
                   % (n, text.strip()))
        if n > handoff.HANDOFF_WORDS:
            out.append("\n[this handoff is %d words over its %d-word cap. It is read "
                       "at the start of every turn, so the next one you write with "
                       "`board handoff` must be inside the cap.]"
                       % (n - handoff.HANDOFF_WORDS, handoff.HANDOFF_WORDS))
    else:
        out.append("\n--- HANDOFF.md ---\nThere is no handoff for this chapter, and "
                   "that is deliberate: a chapter is its own thing and what was left "
                   "unfinished in an earlier one is not this chapter's business. Do "
                   "not go looking for it -- not in live/archive/, not in "
                   "live/handoffs/, not in an older chapter's write-up.")

    # WHOSE PICTURE OF THIS PROJECT THE BOARD IS SHOWING, and whether it is
    # still true. A turn that cannot tell a drawn map from a directory listing
    # will read `psych_asr/asr` back to the person as though it were how they
    # think about their own work. It is three lines and it decides whether the
    # turn is allowed to speak in the project's own vocabulary.
    out.append("\n--- the map ---\n" + map_sense(root))

    # WHAT CHANGED WHILE THE BOARD WAS NOT LOOKING. Placed after the map and
    # before the handoff on purpose: it is about the world the lesson sits in
    # rather than about the lesson, and a turn should have read what the
    # workspace IS before it is told what moved in it.
    beside = beside_sense(repo)
    if beside:
        out.append(beside)

    note = carry.read_note(root)
    if note:
        out.append("\n--- NEXT.md, from the turn just before this one ---\n" + note)
    else:
        out.append("\n--- NEXT.md ---\nnothing left by a previous turn (this is the "
                   "first turn of the lesson, or the last one left no note)")

    out.append("\n--- how a turn works here ---\n" + TURN_SENSE)

    sections = contract_map(root)
    out.append("\n--- if a rule needs its detail ---\n"
               "%s and %s are on disk. Open the ONE section you need; do not read "
               "either file. %s's sections: %s"
               % (CONTRACT, METHOD, CONTRACT,
                  "; ".join(sections) if sections else "(none found)"))
    return "\n".join(out) + "\n"
