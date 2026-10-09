"""The lesson: what is on the board, the session's mode, and the typed half
of the conversation.

Every route here is a SESSION route, served under `/s/<id>/` by that
session's Repo and nothing else (`handler.UNPREFIXED` lists none of them).

    GET  /events              session   the payload stream
    GET  /board.json          session   the payload, once
    GET  /cards?before=<n>    session   the 40 cards below card n, and their ink
    GET  /subject.json        session   the subject's sets, results, jobs, Colibri
    GET  /archive             session   the session's filed lessons
    GET  /archive/<name>[/answers/<file>]
                              session   one of them, read only
    POST /mode                session   teach or do, from now on
    POST /bind                session   bind the session to a subject, from its chip
    POST /handover            session   one step written for them
    POST /dismiss-finish      session   the end-of-session offer waved off
    POST /session             session   label the sitting: a lecture on a
                                        chapter, or a homework set
    POST /text/save           session   a typed answer's draft
    POST /say                 session   a typed turn, into the session's inbox
    POST /poke                session   rebuild the payload now; queue a turn
                                        when a line that wakes is waiting
    POST /end                 session   End: `ended` set, and the wrap-up queued
"""

import re
import time
import json
import os
import urllib.parse

from . import NOT_MINE
from ...course import homework
from .. import hub
from .. import multipart
from ... import sessions
from ... import subjects
from ... import mode as session_mode
from ... import sense
from ...course import config
from ...lesson import archive
from ...lesson import cards
from ...lesson import inbox
from ...lesson import turns
from ...runner import service as runner


def get(h, repo, path):
    if path == "/events":
        return h.sse(h.hub)

    if path == "/board.json":
        return h.send_bytes(h.hub.payload.encode("utf-8"), "application/json")

    if path == "/cards":
        # OLDER CARDS, ON DEMAND. The payload carries the newest `hub.WINDOW`;
        # the board asks for the ones below its oldest when they are wanted.
        want = urllib.parse.parse_qs(urllib.parse.urlparse(h.path or "").query)
        try:
            before = int((want.get("before") or [""])[0])
        except ValueError:
            return h.send_json({"ok": False, "error": "before=<card number>"},
                               status=400)
        return h.send_json(hub.older_cards(repo, getattr(h.hub, "worker", None),
                                           max(0, before)))

    if path == "/subject.json":
        return h.send_json(hub.subject_info(repo))

    if path.startswith("/archive/"):
        # A past lesson, read only. The transcript is the point of keeping
        # them: a student coming back to a chapter should see what they
        # wrote at the time, not an empty board.
        rel = path[len("/archive/"):].strip("/")
        if not rel:
            return h.send_json({"sessions": archive.list_archive(repo)})
        name = multipart.safe_filename(rel.split("/")[0])
        folder = os.path.join(repo.archive, name)
        if not os.path.isdir(folder):
            return h.send_json({"ok": False, "error": "no such session"}, status=404)
        rest = rel.split("/")[1:]
        if rest and rest[0] == "answers" and len(rest) > 1:
            return h.send_file(os.path.join(folder, "answers",
                                               multipart.safe_filename(rest[1])))
        return h.send_json(archive.archived_session(repo, name))

    if path == "/archive":
        return h.send_json({"sessions": archive.list_archive(repo)})

    return NOT_MINE


def _begin(h, repo):
    """Ask the tutor to start, without anybody tapping anything.

    THE TAP WAS THE INSTRUCTION: a sitting opened with `begin` has said what
    it wants, and a second button that says "ask the tutor to begin" is the
    ceremony this whole tool exists to remove.

    The same three things `/say` does for a begin signal, in the same order and
    for the same reasons: a turn on the board so the transcript shows the ask, a
    line in the inbox carrying `session_sense` -- which in a turn IS the
    prompt, so a bare "[begin]" would tell it nothing -- and a turn queued on
    the runner.

    Called only AFTER the sitting is written, or the line would describe the
    sitting being left.
    """
    tid = turns.next_turn_id(repo)
    record = {
        "id": tid, "rev": turns.turn_revision(repo, tid), "kind": "text",
        "answers": None,
        "t": time.time(),
        "iso": time.strftime("%Y-%m-%d %H:%M:%S"),
        "from": "student", "text": "", "signal": "begin", "read": False,
    }
    turns.write_turn(repo, record)
    line = "[begin] " + sense.SIGNAL_SENSE.get("begin", "") + " " \
        + sense.session_sense(repo)
    with open(repo.messages_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(dict(record, text=line)) + "\n")
    runner.wake(repo)
    return tid


def _mode(h, repo):
    """`POST /mode {mode: teach|do}`: who writes the code, from now on.

    `mode.set_mode` writes session.json, one transcript turn and one inbox
    line, and archives nothing. The line is written read, so no turn is
    woken: the next turn's brief carries the new mode.
    """
    try:
        payload = json.loads(h.read_body().decode("utf-8") or "{}")
    except Exception:
        return h.send_json({"ok": False, "error": "bad json"}, status=400)
    try:
        mode, changed = session_mode.set_mode(repo, payload.get("mode"))
    except ValueError:
        return h.send_json({"ok": False, "error": "mode is teach or do"},
                           status=400)
    h.hub.worker.dirty.set()
    return h.send_json({"ok": True, "mode": mode, "changed": changed})


def _bind(h, repo):
    """`POST /bind {subject}`: bind this session to a subject, from the
    header's chip. `sessions.bind` matches `subject` against the subjects
    that exist and appends a non-waking `[bind]` line; nothing moves.

    The registry is asked for the session again at once, so the Hub's Repo
    roots at the subject before the next payload is built, and the chip
    and the course name change without a reload.
    """
    if not repo.stored:
        return h.send_json({"ok": False, "error": "not a session"}, status=404)
    try:
        payload = json.loads(h.read_body().decode("utf-8") or "{}")
    except Exception:
        return h.send_json({"ok": False, "error": "bad json"}, status=400)
    if not isinstance(payload, dict):
        return h.send_json({"ok": False, "error": "bad json"}, status=400)
    sid = os.path.basename(repo.live)
    base = repo.atlas
    try:
        rec, changed = sessions.bind(sid, str(payload.get("subject") or ""),
                                     base=base)
    except sessions.Refused as exc:
        return h.send_json({"ok": False, "error": str(exc)}, status=400)
    except sessions.NoSession:
        return h.send_json({"ok": False, "error": "no such session"}, status=404)
    found = subjects.find(rec["subject"], base) or {}
    registry = getattr(h.server, "registry", None)
    if registry is not None:
        registry.get(sid)
    if changed:
        h.note("session %s bound to %s" % (sid, rec["subject"]))
    h.hub.worker.dirty.set()
    return h.send_json({"ok": True, "changed": changed, "subject": {
        "id": rec["subject"], "name": found.get("name") or rec["subject"],
        "kind": found.get("kind") or ""}})


def _card_here(repo, card):
    """Is `card` the id of a card on this board?

    Nothing here builds a path out of what a browser sent: the id is matched
    against the cards that exist, the same way `/session` looks a label up in
    what discovery found. A miss is a miss.
    """
    if not re.match(r"^\d{4}$", str(card or "")):
        return False
    try:
        names = os.listdir(repo.cards)
    except OSError:
        return False
    for name in names:
        m = cards.CARD_RE.match(name)
        if m and m.group(1) == card:
            return True
    return False


def _handover(h, repo):
    """ONE STEP WRITTEN FOR THEM, AND THE SESSION STAYS IN TEACH.

    **The want:** *"in coach coding mode, I still want to be able to have a
    'fuck this, you do this step' option."* `POST /mode` changes every card
    after it; this hands over one step. Nothing touches the session's state:

    1. **Their tap in the transcript**, as a turn of theirs, naming the card.
    2. **A line in the inbox** with a DOING turn's sense said outright, because
       the session still says teach, which is right about the session and wrong
       about this turn.
    3. **A turn queued**, because the tap is the instruction -- the same
       rule `_begin` follows.

    The turn carries the card in `card`, not in `answers`: a step handed over
    is not an answer to it. Refused in do mode, where nothing is withheld.
    """
    try:
        payload = json.loads(h.read_body().decode("utf-8") or "{}")
    except Exception:
        return h.send_json({"ok": False, "error": "bad json"}, status=400)
    card = str(payload.get("card") or "").strip()
    if not _card_here(repo, card):
        return h.send_json({"ok": False, "error": "no such card"}, status=404)

    if config.mode_of(repo.state()) != "teach":
        return h.send_json({"ok": False,
                            "error": "nothing to hand over; the tutor is "
                                     "already writing the code"}, status=400)

    tid = turns.next_turn_id(repo)
    record = {
        "id": tid, "rev": turns.turn_revision(repo, tid), "kind": "text",
        "answers": None, "card": card,
        "t": time.time(),
        "iso": time.strftime("%Y-%m-%d %H:%M:%S"),
        "from": "student", "text": "You write this step.",
        "signal": "handover", "read": False,
    }
    turns.write_turn(repo, record)
    line = ("[handover] " + sense.SIGNAL_SENSE.get("handover", "") + " "
            + sense.handover_sense(card) + "\n\n"
            + sense.session_sense(repo, doing=True))
    with open(repo.messages_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(dict(record, text=line)) + "\n")

    runner.wake(repo)
    h.hub.worker.dirty.set()
    return h.send_json({"ok": True, "card": card})


def _session(h, repo):
    """`POST /session {session, chapter?, hw?, begin?}`: label the sitting.

    A lecture, optionally on one of the book's chapters, or a homework set.
    Both names are looked up in what the subject has (`homework.chapters`,
    `homework.sets`), never carried through as typed. Nothing is filed away:
    a session keeps every card until the owner ends it. The mode is not a
    sitting's; only `POST /mode` changes it.
    """
    try:
        payload = json.loads(h.read_body().decode("utf-8") or "{}")
    except Exception:                                        # noqa: BLE001
        return h.send_json({"ok": False, "error": "bad json"}, status=400)
    kind = (payload.get("session") or "").strip().lower()
    if kind not in ("lecture", "homework"):
        return h.send_json({"ok": False, "error": "bad session"}, status=400)
    want = (payload.get("hw") or "").strip()
    chapter = (payload.get("chapter") or "").strip()
    if chapter and chapter not in [homework.chapter_label(c)
                                   for c in homework.chapters(repo.root)]:
        return h.send_json({"ok": False, "error": "no such chapter"},
                           status=400)
    chosen = None
    if kind == "homework" and want:
        chosen = dict((x["name"], x) for x in homework.sets(repo.root)).get(want)
        if not chosen:
            return h.send_json({"ok": False, "error": "no such set"}, status=400)
    change = {"session": kind, "finished": None, "hw": None,
              # Legacy sitting keys: a box, a thread, a rethink.
              "node": None, "thread": None, "rethink": None}
    if chapter:
        change["chapter"] = chapter
        change["opened"] = time.strftime("%Y-%m-%d %H:%M")
    if chosen:
        change["hw"] = chosen["rel"]
        change["chapter"] = chosen["name"]
    repo.set_state(**change)
    start = bool(payload.get("begin"))
    if start:
        _begin(h, repo)
    h.hub.worker.dirty.set()
    return h.send_json({"ok": True, "session": kind,
                        "hw": repo.state().get("hw"), "begun": start})


def post(h, repo, path):
    if path == "/mode":
        return _mode(h, repo)

    if path == "/bind":
        return _bind(h, repo)

    if path == "/handover":
        return _handover(h, repo)

    if path == "/dismiss-finish":
        st = repo.state()
        st.pop("finished", None)
        with open(repo.state_path, "w", encoding="utf-8") as fh:
            json.dump(st, fh, indent=2)
        h.hub.worker.dirty.set()
        return h.send_json({"ok": True})

    if path == "/session":
        return _session(h, repo)

    if path == "/text/save":
        # A typed answer in progress, kept per question so the panel can flip
        # between writing and typing without losing either.
        try:
            payload = json.loads(h.read_body().decode("utf-8"))
        except Exception:
            return h.send_json({"ok": False, "error": "bad json"}, status=400)
        qid = str(payload.get("question") or "")
        if not re.match(r"^\d{1,4}$", qid):
            return h.send_json({"ok": False, "error": "bad question"}, status=400)
        text = payload.get("text") or ""
        stem = os.path.join(repo.text, qid + ".txt")
        if text.strip():
            with open(stem, "w", encoding="utf-8") as fh:
                fh.write(text)
        else:
            try:
                os.remove(stem)
            except OSError:
                pass
        h.hub.worker.dirty.set()
        return h.send_json({"ok": True, "question": qid})

    if path == "/say":
        try:
            payload = json.loads(h.read_body().decode("utf-8"))
        except Exception:
            return h.send_json({"ok": False, "error": "bad json"}, status=400)
        text = (payload.get("text") or "").strip()
        # A signal carries meaning without a sentence, and two are still sent:
        # "begin" and "skip". "begin" is the cold start -- an empty board owes
        # no answer, so the slate never opens and there is nothing to type in,
        # which left the iPad with no way to say the first thing of a session.
        # "skip" declines a prompt.
        #
        # "done", "help" and "confused" were the three buttons a `code` course
        # got instead of an answer, and both the buttons and the mode are gone.
        # They are STILL ACCEPTED, because an installed app serves a cached
        # shell: a device that has not picked up the new one yet still has the
        # buttons on it, and a 400 in reply to a tap is a lesson that stops. The
        # sentences behind them are unchanged, so such a tap still reaches the
        # tutor and still means what it always meant.
        signal = (payload.get("signal") or "").strip().lower() or None
        if signal not in (None, "done", "help", "confused", "begin", "skip"):
            return h.send_json({"ok": False, "error": "bad signal"}, status=400)
        if not text and not signal:
            return h.send_json({"ok": False, "error": "empty"}, status=400)

        tid = payload.get("turn") or turns.next_turn_id(repo)
        rev = turns.turn_revision(repo, tid)
        record = {
            "id": tid, "rev": rev, "kind": "text",
            "answers": payload.get("answers") or turns.newest_question(repo),
            "t": time.time(),
            "iso": time.strftime("%Y-%m-%d %H:%M:%S"),
            "from": payload.get("from") or "student",
            "text": text[:8000],
            "signal": signal,
            "read": False,
        }
        turns.write_turn(repo, record)
        # The typed draft for this question is now the answer itself; it has
        # been said and should not come back to haunt the next prompt.
        a = record.get("answers")
        if a:
            try:
                os.remove(os.path.join(repo.text, str(a) + ".txt"))
            except OSError:
                pass
        # What lands in the inbox is what the runner hands the turn, and
        # that string IS the prompt the assistant is woken with. A bare "[begin]" tells it nothing, so a signal sent without a
        # sentence carries its own.
        line = ("[%s] " % signal if signal else "") + text
        if signal and not text:
            line += (sense.skip_sense(repo) if signal == "skip"
                     else sense.SIGNAL_SENSE.get(signal, ""))
        if signal == "begin":
            # Where to begin, not merely that they are waiting. Without this
            # the assistant has a blank board, no handoff, and a signal that
            # says nothing -- so it guesses, and the first guess opened a
            # course at chapter four.
            line += " " + sense.session_sense(repo)
        with open(repo.messages_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(dict(record, text=line)) + "\n")
        # Queued on the runner, which answers it with a fresh turn.
        runner.wake(repo)
        h.hub.worker.dirty.set()
        return h.send_json({"ok": True, "turn": tid, "rev": rev})

    if path == "/poke":
        # `board write` says a card landed, so the payload is rebuilt now
        # rather than on the next sentinel pass. A line that wakes and that
        # nothing has queued (written by a command outside this server) is
        # queued here.
        h.hub.worker.dirty.set()
        queued = bool(inbox.waiting(repo)) and runner.wake(repo)
        return h.send_json({"ok": True, "queued": bool(queued)})

    if path == "/end":
        return _end(h, repo)
    return NOT_MINE


def _end(h, repo):
    """`POST /end`: End this session. `sessions.end` sets `ended` and commits
    the subject's TUTOR.md and the session's artifacts; then the wrap-up turn
    is queued, the only thing that ever runs it. A second End changes
    nothing but retries the commit."""
    if not repo.stored:
        return h.send_json({"ok": False, "error": "not a session"}, status=404)
    sid = os.path.basename(repo.live)
    base = os.path.dirname(os.path.dirname(repo.live))
    try:
        rec, committed, said = sessions.end(sid, base=base)
    except sessions.NoSession:
        return h.send_json({"ok": False, "error": "no such session"}, status=404)
    queued = bool(runner.RUNNER and runner.RUNNER.end(sid))
    h.note("session %s ended (%s)" % (sid, said))
    h.hub.worker.dirty.set()
    return h.send_json({"ok": True, "session": rec, "committed": bool(committed),
                        "detail": said, "wrapup": queued})
