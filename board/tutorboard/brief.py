"""Everything a cold turn has to know, in one call: `board brief`.

Every turn is a cold turn, so the brief is what a turn costs before it teaches.
It carries the method as `tutorboard.sense` states it, the subject's RULES.md
as committed at HEAD (flagging a working-tree edit), the subject's TUTOR.md,
what the owner did away from the board, and the work out on the cluster. It
points at board/TEACHING.md for a rule's detail. A subject's README.md is the
owner's and never enters the brief.

`test/tokens.py` holds a fixture brief to `BUDGET` characters.
"""

import os
import time

from . import jobs, memo, progress
from .course import config
from .course import homework
from .lesson import git as lesson_git


# The method in full, for the one section a rule needs. Turns run from the
# Atlas root, so the relative name is the one to open.
METHOD = "board/TEACHING.md"

# What a fixture brief may cost, in characters (`test/tokens.py`).
BUDGET = 14000

# The mechanics of a turn. Here rather than in `tutorboard.sense` because a
# turn is the only thing that reads the brief.
TURN_SENSE = (
    "This turn is its own session; nothing you hold survives it but the lesson "
    "on disk (`board recap`), RULES.md and TUTOR.md. When this turn changes "
    "where things are, what is happening now, an open decision or what got "
    "done, rewrite that section with `board memo <section>` (its whole new text "
    "on stdin; TUTOR.md is capped at %d words). Never write RULES.md. Do not "
    "wait: the next message starts a fresh turn of its own." % memo.WORDS
)


def rules_sense(root):
    """The RULES.md section of the brief, or "" where the subject has none."""
    text, drift = memo.rules(root)
    if not text and not drift:
        return ""
    out = ["\n--- RULES.md: the owner's rules, as committed at HEAD ---"]
    out.append(text or "(none committed)")
    if drift == "edited":
        out.append("[RULES.md in the working tree differs from HEAD. The rules "
                   "above are HEAD's; the edit binds nobody until the owner "
                   "commits it.]")
    elif drift == "uncommitted":
        out.append("[RULES.md exists in the working tree but was never "
                   "committed; it binds nobody until the owner commits it.]")
    elif drift == "deleted":
        out.append("[RULES.md is deleted in the working tree but not at HEAD; "
                   "the rules above still bind.]")
    return "\n".join(out)


def tutor_sense(repo):
    """The TUTOR.md section of the brief."""
    if _unbound(repo):
        return ("\n--- TUTOR.md ---\nThis session is bound to no subject, so "
                "there is no TUTOR.md. Once the owner names the course or "
                "project, `board bind courses/<Name>` or `board bind "
                "projects/<Name>` (`--create` for a new one) binds it.")
    text = memo.tutor(repo.root)
    if not text:
        return ("\n--- TUTOR.md ---\nNone yet. Start it with `board memo "
                "<section>`; the sections are %s."
                % ", ".join('"%s"' % s for s in memo.SECTIONS))
    n = memo.word_count(text)
    return ("\n--- TUTOR.md: your own notes on this subject (%d of %d words) ---\n%s"
            % (n, memo.WORDS, text))


def _unbound(repo):
    """A stored session bound to no subject: its root is the Atlas root."""
    atlas = getattr(repo, "atlas", None)
    if not getattr(repo, "stored", False) or not atlas:
        return False
    return os.path.realpath(repo.root) == os.path.realpath(atlas)


def relay_sense(root):
    """The requests here the cluster has not ended, or ""."""
    try:
        waiting = jobs.outstanding(root)
    except Exception:                                        # noqa: BLE001
        return ""
    if not waiting:
        return ""
    out = ["\n--- out on the cluster ---",
           "Waiting on the cluster (the pull hears each ending as a [job] line):"]
    out.extend("  %s  %s  %s" % (r["request"], str(r.get("state") or "").lower(),
                                 r.get("cmd") or "")
               for r in waiting[:10])
    return "\n".join(out)


def sitting_sense(repo, st=None):
    """Any hold standing in the workspace, or ""."""
    out = []
    try:
        from . import holds
        out.extend(holds.standing_sense(repo.root))
    except Exception:                                        # noqa: BLE001
        pass
    if not out:
        return ""
    return "\n--- what this sitting is ---\n" + "\n".join(out)


def beside_sense(repo):
    """What somebody did to this workspace that you have not been told about.

    THE WORDING IS THE FEATURE. A turn reading this has to come away certain
    that the work described is THE PERSON'S, done somewhere else, with no
    involvement from it -- because the alternative is a turn that reports having
    written code it has never seen, in a card, confidently, with nothing on the
    board able to contradict it.

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
        return ""                       # silent when there is nothing

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


def briefing(repo, sense, chapter=None, doing=None, mission=False,
             repair=None):
    """The whole cold briefing as one string.

    `sense` is `tutorboard.sense`, passed in rather than imported, because it
    reaches into the course package for the syllabus and the homework sheet and
    this module is imported by things that have already paid for that.

    `doing` goes straight to `sense.session_sense`: a mission or a repair is a
    doing turn even where the session's mode is teach. `None` leaves the
    session's mode to answer.

    `mission` is the mission record this turn is working, or None; its trail
    is carried below.

    `repair` is the section a `[repair]` turn reads (`jobs.repair_brief`). It
    sits under the mode it overrides, and comes with `doing=True`.
    """
    root = repo.root
    st = repo.state()
    out = []

    head = " — ".join(x for x in (st.get("course"), st.get("session"),
                                  st.get("chapter")) if x)
    out.append(head or "no session open")
    # A SESSION THAT IS ABOUT NOTHING YET. It starts unbound, and a turn that
    # guesses its subject files the work in the wrong place; so it asks.
    if getattr(repo, "stored", False) and not st.get("subject"):
        out.append("subject: none -- this session is not bound to a course or "
                   "project yet. Before any other work, ask the owner what this "
                   "session is for. Then `board bind courses/<Name>` or `board "
                   "bind projects/<Name>`; add `--create` for a new one (a "
                   "project also needs `--phi yes|no`).")
    held = sitting_sense(repo, st)
    if held:
        out.append(held)
    # THE WRITE-UP, on the brief, every turn. Counts and not just a name: "0 of
    # 11 written up, next 04.1" is a debt, and a debt on the brief gets paid.
    hw_set = homework.bound(root, st)
    if hw_set:
        try:
            hw_st = homework.status(root, st)
        except Exception:
            hw_st = None
        if hw_st and hw_st.get("total"):
            line = "writeup: %s (%s) -- %d of %d written up" % (
                hw_st["name"], hw_st["rel"], hw_st["written"], hw_st["total"])
            if hw_st.get("stated", 0) < hw_st["total"]:
                line += ", %d statement(s) not yet transcribed" % (
                    hw_st["total"] - hw_st["stated"])
            if hw_st.get("next"):
                line += ", next %s" % hw_st["next"]
            out.append(line + "; `board writeup add <label>` for each agreed answer")
        else:
            out.append("writeup: %s (%s) -- nothing written yet; `board writeup "
                       "add <label>` for each agreed answer"
                       % (hw_set["name"], hw_set["rel"]))
    elif config.mode_of(st) != "do":
        out.append("writeup: none yet -- the first `board writeup add <label>` "
                   "starts it%s" % (
                       "" if not (getattr(repo, "stored", False)
                                  and not st.get("subject"))
                       else ", once the session is bound to a subject"))
    # Who writes the code: the session's mode, and only that.
    cfg = config.read_config(root)
    out.append("mode: %s" % config.mode_of(st))
    # The subject's check, run before a push that changed code. Always as
    # `board check`, which runs it from the subject's root: a turn works in the
    # Atlas root, and `board *` is what it may run.
    if cfg.get("check_line"):
        out.append("check: `board check` (runs `%s` from the subject's root; "
                   "before a push that changed code, and the report says "
                   "whether it passed)" % cfg["check_line"])
    if repair:
        out.append("\n" + "\n".join(repair))

    out.append("\n--- the method, and what this sitting is ---\n"
               + sense.session_sense(repo, doing=doing, mission=mission))

    if not _unbound(repo):
        said = rules_sense(root)
        if said:
            out.append(said)
    out.append(tutor_sense(repo))

    beside = beside_sense(repo)
    if beside:
        out.append(beside)

    waiting = relay_sense(root)
    if waiting:
        out.append(waiting)

    # WHAT THIS MISSION HAS ALREADY DONE: `progress.py`'s trail, the lines a
    # person reads on the panel, so a picked-up turn does not repeat them.
    if mission:
        trail = progress.read(root, str(mission.get("id") or ""))
        if trail:
            out.append("\n--- what this mission has done so far (%d step%s) ---"
                       % (len(trail), "" if len(trail) == 1 else "s"))
            for one in trail:
                out.append("  %s  %s%s"
                           % (time.strftime("%H:%M", time.localtime(one["at"])),
                              "" if one["who"] == "agent" else "[board] ",
                              one["said"]))
            out.append("Do not do any of that again. Carry on from the last "
                       "line, and `board step` the next thing you finish.")

    out.append("\n--- how a turn works here ---\n" + TURN_SENSE)

    out.append("\n--- if a rule needs its detail ---\n"
               "The method in full is %s. Open the ONE section you need, not "
               "the whole file." % METHOD)
    return "\n".join(out) + "\n"
