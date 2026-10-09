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

from . import jobs, memo, reasoning
from .course import config
from .course import homework
from .lesson import git as lesson_git
from .lesson import inbox


# The method in full, for the one section a rule needs. Turns run from the
# Atlas root, so the relative name is the one to open.
METHOD = "board/TEACHING.md"

# What a fixture brief may cost, in characters (`test/tokens.py`).
BUDGET = 14000

# Cards the recap names as lines: bounded, since every turn reads it.
LINES = 40

# Past this many characters the recap is compact: the newest card whole and
# one line per earlier card.
RECAP_LIMIT = 12000

# The most the book's chapter list may cost the brief, in characters.
BOOK_CHARS = 1500

# The mechanics of a turn; only a turn reads the brief.
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
    """The requests here the cluster has not ended, and the cluster's health
    where the relay looks down or this checkout is not synced; or ""."""
    try:
        waiting = jobs.outstanding(root)
    except Exception:                                        # noqa: BLE001
        waiting = []
    health = _health(root)
    if not waiting and not health:
        return ""
    out = ["\n--- out on the cluster ---"]
    out.extend(health)
    if waiting:
        out.append("Waiting on the cluster (the pull hears each ending as a "
                   "[job] line):")
        out.extend("  %s  %s  %s" % (r["request"],
                                     str(r.get("state") or "").lower(),
                                     r.get("cmd") or "")
                   for r in waiting[:10])
    return "\n".join(out)


def _health(root):
    """`relay.health`'s "relay looks down" and "not synced" lines: a request
    filed now would wait on either."""
    from . import cluster, relay
    try:
        got = relay.health(cluster.atlas_of(root))
    except Exception:                                        # noqa: BLE001
        return []
    return ["HEALTH: " + l for l in got.get("lines") or []
            if l.startswith(("relay looks down", "not synced"))]


def beside_sense(repo):
    """What somebody did to this workspace that you have not been told about.
    The wording says three times that it is the owner's work done elsewhere,
    because a turn claiming that work as its own is undetectable on the board.
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


def briefing(repo, sense, chapter=None, doing=None, repair=None):
    """The whole cold briefing as one string. `sense` is passed in, not
    imported (it reaches into the course package). `doing` goes to
    `sense.session_sense` (a repair is a doing turn); `repair` is the
    `[repair]` section (`jobs.repair_brief`), placed under the mode it
    overrides.
    """
    root = repo.root
    st = repo.state()
    out = []

    head = " — ".join(x for x in (st.get("course"), st.get("session"),
                                  st.get("chapter")) if x)
    out.append(head or "no session open")
    # An unbound session asks for its subject rather than guess.
    if getattr(repo, "stored", False) and not st.get("subject"):
        out.append("subject: none -- this session is not bound to a course or "
                   "project yet. Before any other work, ask the owner what this "
                   "session is for. Then `board bind courses/<Name>` or `board "
                   "bind projects/<Name>`; add `--create` for a new one (a "
                   "project also needs `--phi yes|no`).")
    # The write-up's counts every turn: a debt on the brief gets paid.
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
    # The check, always as `board check`, which runs from the subject's root.
    if cfg.get("check_line"):
        out.append("check: `board check` (runs `%s` from the subject's root; "
                   "before a push that changed code, and the report says "
                   "whether it passed)" % cfg["check_line"])
    if repair:
        out.append("\n" + "\n".join(repair))

    out.append("\n--- the method, and what this sitting is ---\n"
               + sense.session_sense(repo, doing=doing))

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
    """The lesson so far, as one string: the newest `LINES` cards as lines,
    the newest `full` in full, earlier turns one line each, the latest turn
    with its paths. `compact` drops the earlier turns."""
    names = repo.card_names()
    st = repo.state()
    out = []

    head = " — ".join(x for x in (st.get("course"), st.get("session"),
                                  st.get("chapter")) if x)
    out.append(head or "no session open")
    if st.get("hw"):
        out.append("homework set: %s" % st["hw"])

    # Newest revision per turn id.
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
            out.append("  (%d earlier card(s) not listed — TUTOR.md is what "
                       "carries the subject, `board recap --all` lists them)"
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
        # Read through the board's own gate, so leaked deliberation is not
        # the lesson.
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
    """The brief a turn woken for `signal` reads, from what the runner knows;
    a `[repair]` batch briefs a doing turn."""
    from . import sense            # reaches into the course package; see briefing
    fixing = None
    rids = [r for r in (repairs or []) if isinstance(r, str) and r]
    if rids:
        fixing = rids
    elif signal == jobs.REPAIR:
        fixing = [jobs.last_repair(repo.root)]
    return briefing(
        repo, sense, doing=True if fixing is not None else None,
        repair=jobs.repair_brief(repo.root, fixing) if fixing is not None else None)


def turn_context(repo, signal="", repairs=None, brief=True):
    """The brief and the recap, as one block above the prompt. `brief=False`
    gives the recap alone. A part that fails says so and names the command
    that prints it."""
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
