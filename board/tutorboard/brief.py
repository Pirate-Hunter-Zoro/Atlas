"""Everything a cold turn has to know: the brief and the recap.

Every turn is a cold turn, so the brief is what a turn costs before it teaches.
It carries the method as `tutorboard.sense` states it, the subject's RULES.md
as committed at HEAD (flagging a working-tree edit), the subject's TUTOR.md,
what the owner did away from the board, and the work out on the cluster. It
points at board/TEACHING.md for a rule's detail. A subject's README.md is the
owner's and never enters the brief.

`recap` is the lesson so far: one line per card, the newest in full, the
student's turns. The runner renders both in-process and hands them to every
lesson turn (`turn_context`); `board brief` and `board recap` print the same
text for manual use.

`test/tokens.py` holds a fixture brief to `BUDGET` characters.
"""

import json
import os
import time

from . import jobs, memo, progress, reasoning
from .course import config
from .course import homework
from .lesson import git as lesson_git
from .lesson import inbox


# The method in full, for the one section a rule needs. Turns run from the
# Atlas root, so the relative name is the one to open.
METHOD = "board/TEACHING.md"

# What a fixture brief may cost, in characters (`test/tokens.py`).
BUDGET = 14000

# How many cards the recap names as lines. Every turn reads this, so it is the
# one part of the recap that must not grow with the lesson. Wide enough to hold
# a whole sitting's worth of shape, which is what a turn reasons about.
LINES = 40

# What a recap handed to a turn may cost, in characters. Past it the recap is
# rendered compact (`recap(compact=True)`): the newest card whole and one line
# per earlier card, without the student's earlier turns.
RECAP_LIMIT = 12000

# The most the book's chapter list may cost the brief, in characters.
BOOK_CHARS = 1500

# The mechanics of a turn. Here rather than in `tutorboard.sense` because a
# turn is the only thing that reads the brief.
TURN_SENSE = (
    "This turn is its own session; nothing you hold survives it but the lesson "
    "on disk (handed to every turn as its recap), RULES.md and TUTOR.md. When this turn changes "
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


def book_sense(root):
    """The book a course follows, as one line of its chapters, or "".

    `board writeup new chNN` takes these numbers.
    """
    try:
        every = homework.chapters(root)
    except Exception:                                        # noqa: BLE001
        return ""
    if not every:
        return ""
    head = "book: %d chapter%s -- " % (len(every), "" if len(every) == 1 else "s")
    said, n = [], len(head)
    for c in every:
        one = ("%s %s" % (str(c.get("num") or "").strip(),
                          (c.get("title") or c.get("slug") or "").strip())).strip()
        if n + len(one) + 2 > BOOK_CHARS:
            said.append("and %d more" % (len(every) - len(said)))
            break
        said.append(one)
        n += len(one) + 2
    return head + "; ".join(said)


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
    reaches into the course package for the chapters and the homework sheet and
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
    if not _unbound(repo):
        book = book_sense(root)
        if book:
            out.append(book)
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


# ---------------------------------------------------------------------------
# the recap
# ---------------------------------------------------------------------------
def card_meta(raw):
    """Front matter and body of a card, without pulling in a YAML parser."""
    meta, text = {}, raw
    if raw.startswith("---"):
        end = raw.find("\n---", 3)
        if end != -1:
            for line in raw[3:end].splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip().lower()] = v.strip()
            text = raw[end + 4:].lstrip("\n")
    return meta, text


def read_turns(repo):
    """Every student turn, newest revision last. The file is append-only."""
    out = []
    try:
        with open(repo.path("turns.jsonl"), "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        out.append(json.loads(line))
                    except ValueError:
                        pass
    except OSError:
        pass
    return out


def recap(repo, full=1, compact=False):
    """The lesson so far, as one string.

    One line per card (the newest `LINES` of them), the newest `full` cards in
    full, the student's earlier turns one line each, and their latest turn with
    its file paths. `compact` drops the earlier turns and keeps the latest one
    short: what is left is the newest card whole and one line per earlier card.
    """
    names = repo.card_names()
    st = repo.state()
    out = []

    head = " — ".join(x for x in (st.get("course"), st.get("session"),
                                  st.get("chapter")) if x)
    out.append(head or "no session open")
    if st.get("hw"):
        out.append("homework set: %s" % st["hw"])

    # Newest revision per turn id: a correction supersedes in place, so an
    # older revision is not part of the lesson.
    newest = {}
    for t in read_turns(repo):
        tid = t.get("id")
        if tid and t.get("rev", 1) >= newest.get(tid, {}).get("rev", 0):
            newest[tid] = t
    turns = sorted(newest.values(), key=lambda t: t.get("t") or 0)
    answered = {t.get("answers") for t in turns if t.get("answers")}

    if not names:
        out.append("no cards yet — nothing has been taught in this session")
    else:
        out.append("%d card(s), %d student turn(s)\n" % (len(names), len(turns)))
        shown = names if full >= len(names) else names[-LINES:]
        if len(shown) < len(names):
            out.append("  (%d earlier card(s) not listed — HANDOFF.md is what "
                       "carries the chapter, `board recap --all` lists them)"
                       % (len(names) - len(shown)))
        for n in shown:
            with open(os.path.join(repo.cards, n), "r", encoding="utf-8") as fh:
                meta, _ = card_meta(fh.read())
            mark = ""
            kind = (meta.get("kind") or "lesson").lower()
            if kind == "question":
                mark = ("  <- answered" if n[:4] in answered or n in answered
                        else "  <- OPEN, not answered yet")
            out.append("  %s %-9s %s%s" % (n[:4], kind, meta.get("title", ""), mark))

    for n in names[len(names) - full:] if full else []:
        with open(os.path.join(repo.cards, n), "r", encoding="utf-8") as fh:
            raw = fh.read()
        # Read back through the gate the board reads through: a tutor's own
        # deliberation that ended up in a card is not the lesson so far.
        _meta, body = card_meta(raw)
        clean = reasoning.card_body(body)
        if clean != body:
            raw = raw[:len(raw) - len(body)] + clean
        out.append("\n--- %s, in full ---\n%s" % (n, raw.strip()))

    if len(turns) > 1 and not compact:
        out.append("\ntheir turns so far:")
        for t in turns[:-1]:
            what = (t.get("text") or "").strip().replace("\n", " ")
            if t.get("signal"):
                what = "[%s] %s" % (t["signal"], what)
            if t.get("png") and not what:
                what = "handwriting"
            out.append("  %-19s %-6s %s" % (
                t.get("iso") or "?",
                ("-> " + t["answers"]) if t.get("answers") else "", what[:96]))
    elif len(turns) > 1:
        out.append("\n(%d earlier turn(s) of theirs not listed; `board recap` "
                   "lists them)" % (len(turns) - 1))

    if turns:
        t = turns[-1]
        out.append("\n--- their most recent turn (%s) ---" % (t.get("iso") or "?"))
        if t.get("answers"):
            out.append("answers card %s" % t["answers"])
        if t.get("signal"):
            out.append("signal: %s" % t["signal"])
        text = (t.get("text") or "").strip()
        if text:
            out.append(text if not compact or len(text) <= 400
                       else text[:400] + " […]")
        if t.get("png"):
            out.append("handwriting: %s" % os.path.join(
                repo.session, str(t["png"]).lstrip("/")))
        for f in t.get("files", []) or []:
            out.append("file: %s" % os.path.join(repo.uploads, f))

    unread = inbox.unread(repo)
    if unread:
        out.append("\n%d unread message(s) in the inbox — `board inbox` has them"
                   % len(unread))
    return "\n".join(out) + "\n"


def guarded_recap(repo, limit=RECAP_LIMIT):
    """The recap a turn is handed: whole, or compact past `limit` characters."""
    text = recap(repo)
    if len(text) <= limit:
        return text
    return recap(repo, compact=True)


# ---------------------------------------------------------------------------
# what a turn is handed
# ---------------------------------------------------------------------------
def turn_brief(repo, signal="", repairs=None):
    """The brief a turn woken for `signal` reads: `board brief`'s, answered
    from what the runner knows rather than from `agent.json`.

    A running mission and a `[repair]` batch brief a doing turn, as
    `board brief` does inside one (`_repairing` in bin/board).
    """
    from . import sense            # reaches into the course package; see briefing
    try:
        from . import missions
        rec = missions.live_mission(repo.root)
    except Exception:                                        # noqa: BLE001
        rec = None
    fixing = None
    if not rec:
        rids = [r for r in (repairs or []) if isinstance(r, str) and r]
        if rids:
            fixing = rids
        elif signal == jobs.REPAIR:
            fixing = [jobs.last_repair(repo.root)]
    return briefing(
        repo, sense, doing=True if rec or fixing is not None else None,
        mission=rec,
        repair=jobs.repair_brief(repo.root, fixing) if fixing is not None else None)


def turn_context(repo, signal="", repairs=None, brief=True):
    """The brief and the recap, as one block a turn reads before its prompt.

    `brief=False` hands over the recap alone (the wrap-up). A part that fails
    to render says so in its place and names the command that prints it, so a
    turn is never told something is above that is not.
    """
    parts = []
    if brief:
        try:
            text = turn_brief(repo, signal, repairs)
        except Exception as exc:                             # noqa: BLE001
            text = ("(the brief could not be rendered here: %s. Run `board "
                    "brief` for it.)\n" % exc)
        parts.append("=== THE BRIEF: the method, RULES.md, TUTOR.md ===\n" + text)
    try:
        text = guarded_recap(repo)
    except Exception as exc:                                 # noqa: BLE001
        text = ("(the recap could not be rendered here: %s. Run `board "
                "recap` for it.)\n" % exc)
    parts.append("=== THE RECAP: the lesson so far ===\n" + text)
    parts.append("=== END OF %s ===" % ("THE BRIEF AND THE RECAP" if brief
                                        else "THE RECAP"))
    return "\n".join(parts)
