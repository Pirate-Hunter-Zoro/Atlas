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
    POST /problem             session   the write-up's problem on their screen
    POST /handover            session   one step written for them
    POST /dismiss-finish      session   the end-of-session offer waved off
    POST /session             session   label the sitting: a lecture on a
                                        chapter, or a homework set
    POST /text/save           session   a typed answer's draft
    POST /say                 session   a typed turn, into the session's inbox
    POST /poke                session   rebuild the payload now; queue a turn
                                        when a line that wakes is waiting
    POST /send                session   send it to a subject: bind, and file its
                                        uploads; for an ended session, the
                                        wrap-up queued late
    POST /end                 session   End: `ended` set, and the wrap-up queued;
                                        with `subject`, sent there first
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
        # Older cards on demand, below the payload's `hub.WINDOW`.
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
        # A past lesson, read only.
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
    """Ask the tutor to start: the tap was the instruction. Like `/say` for a
    begin signal: a transcript turn, an inbox line carrying `session_sense`
    (a bare "[begin]" tells a turn nothing), and a queued turn. Called only
    after the sitting is written.
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
    """`POST /bind {subject, force}`: bind this session from the header's
    chip. `sessions.bind` matches `subject` against existing subjects and
    appends a non-waking `[bind]` line. A move off a subject the session has
    left work in is a 409 with `confirm`, until `force` is true. The registry is asked again at once, so the
    next payload roots at the subject without a reload.
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
                                     base=base, force=payload.get("force") is True)
    except sessions.Unconfirmed as exc:
        # The chip asks the owner, then sends the same subject with `force`.
        return h.send_json({"ok": False, "error": str(exc), "confirm": True},
                           status=409)
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


def _problem(h, repo):
    """`POST /problem {label}`: switch the problem on their screen to one of
    the pinned write-up's, or clear it with no label. session.json `problem`
    and a non-waking `[problem]` line; the next turn reads it. Setting the
    label already pinned writes nothing.
    """
    try:
        payload = json.loads(h.read_body().decode("utf-8") or "{}")
    except Exception:
        return h.send_json({"ok": False, "error": "bad json"}, status=400)
    if not isinstance(payload, dict):
        return h.send_json({"ok": False, "error": "bad json"}, status=400)
    label = str(payload.get("label") or "").strip() or None
    st = repo.state()
    found = homework.bound(repo.root, st)
    if label is not None:
        labels = [p["label"] for p in homework.problems(found["tex"])] if found else []
        if label not in labels:
            return h.send_json({"ok": False, "error": "no problem %s in the write-up"
                                % label}, status=400)
    if (st.get("problem") or None) == label:
        return h.send_json({"ok": True, "problem": label, "changed": False})
    repo.set_state(problem=label)
    text = ("[problem] They are now on problem %s of %s. Pose it if it is not "
            "posed yet." % (label, found["name"]) if label
            else "[problem] They cleared the problem on their screen.")
    sessions.quiet_line(repo.messages_path, text, "problem")
    h.hub.worker.dirty.set()
    return h.send_json({"ok": True, "problem": label, "changed": True})


def _card_here(repo, card):
    """Is `card` the id of a card on this board? Matched against the cards
    that exist, never made into a path."""
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
    """`POST /handover`: one step written for them; the session stays in teach.

    A transcript turn naming the card, an inbox line stating a doing turn's
    sense (the session still says teach), and a queued turn. The card rides
    in `card`, not `answers`. Refused in do mode.
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
    """`POST /session {session, chapter?, hw?, begin?}`: label the sitting, a
    lecture (optionally on a chapter) or a homework set, both looked up in
    what the subject has. Files nothing away and never changes the mode.
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
    change = {"session": kind, "finished": None, "hw": None, "problem": None,
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

    if path == "/problem":
        return _problem(h, repo)

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
        # A typed draft per question, so writing and typing can alternate.
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
        # Signals without a sentence: "begin" (the cold start, when there is
        # nothing to answer) and "skip". "done", "help" and "confused" are
        # still accepted, because a cached app shell may still offer them.
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
        # The draft became the answer; it must not return to the next prompt.
        a = record.get("answers")
        if a:
            try:
                os.remove(os.path.join(repo.text, str(a) + ".txt"))
            except OSError:
                pass
        # The inbox line is the turn's prompt, so a bare signal carries a
        # sentence.
        line = ("[%s] " % signal if signal else "") + text
        if signal and not text:
            line += (sense.skip_sense(repo) if signal == "skip"
                     else sense.SIGNAL_SENSE.get(signal, ""))
        if signal == "begin":
            # Where to begin, so the turn does not guess a chapter.
            line += " " + sense.session_sense(repo)
        with open(repo.messages_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(dict(record, text=line)) + "\n")
        # Queued on the runner, which answers it with a fresh turn.
        runner.wake(repo)
        h.hub.worker.dirty.set()
        return h.send_json({"ok": True, "turn": tid, "rev": rev})

    if path == "/poke":
        # Rebuild now; queue a waking line written outside this server.
        h.hub.worker.dirty.set()
        queued = bool(inbox.waiting(repo)) and runner.wake(repo)
        return h.send_json({"ok": True, "queued": bool(queued)})

    if path == "/send":
        return _send(h, repo)

    if path == "/end":
        return _end(h, repo)
    return NOT_MINE


def _body(h):
    """The request's JSON object, `{}` for an empty body, or None."""
    try:
        payload = json.loads(h.read_body().decode("utf-8") or "{}")
    except Exception:                                        # noqa: BLE001
        return None
    return payload if isinstance(payload, dict) else None


def _sent(h, sid, base, subject, late):
    """Send session `sid` to `subject` (`sessions.send`, `late` as there),
    and ask the registry again so the hub roots at the subject. The reply
    keys, or None once the refusal is answered, with nothing changed."""
    try:
        rec, filed, refused = sessions.send(sid, subject, base=base, late=late)
    except sessions.Refused as exc:
        h.send_json({"ok": False, "error": str(exc)}, status=400)
        return None
    except sessions.NoSession:
        h.send_json({"ok": False, "error": "no such session"}, status=404)
        return None
    found = subjects.find(rec["subject"], base) or {}
    registry = getattr(h.server, "registry", None)
    if registry is not None:
        registry.get(sid)
    h.note("session %s sent to %s (%d filed, %d refused)"
           % (sid, rec["subject"], len(filed), len(refused)))
    return {"sent": {"id": rec["subject"],
                     "name": found.get("name") or rec["subject"],
                     "kind": found.get("kind") or ""},
            "filed": filed, "refused": refused}


def _elsewhere(h, rec, base, subject):
    """An ended session bound to a subject other than `subject`: True once
    the 409 that says where it went is answered, else False."""
    was = rec.get("subject")
    if not rec.get("ended") or not was:
        return False
    found = subjects.find(subject, base) if subject else None
    if found and found["id"] == was:
        return False
    h.send_json({"ok": False, "error": "this session has ended and was "
                 "sent to %s" % was}, status=409)
    return True


def _send(h, repo):
    """`POST /send {subject}`: send this session to a subject -- bound, and
    every upload left in `uploads/` filed into its `materials/`. Open, it
    stays open. Ended while bound to nothing, the wrap-up is queued late, so
    the session is written up there and `sessions.end` commits it. Filing,
    not talking to the tutor, so an ended session answers it
    (`handler.ENDED_REFUSES`); an ended one already sent elsewhere, or whose
    wrap-up is still queued or running (it may be choosing the subject
    itself), is 409."""
    if not repo.stored:
        return h.send_json({"ok": False, "error": "not a session"}, status=404)
    payload = _body(h)
    if payload is None:
        return h.send_json({"ok": False, "error": "bad json"}, status=400)
    sid = os.path.basename(repo.live)
    base = repo.atlas
    subject = str(payload.get("subject") or "")
    with sessions.held(sid, base):
        rec = sessions.get(sid, base) or {}
        if _elsewhere(h, rec, base, subject):
            return None
        ended = bool(rec.get("ended"))
        if ended and runner.RUNNER and runner.RUNNER.busy(sid):
            return h.send_json({"ok": False, "error": "this session's wrap-up "
                                "is running; send it once that is done"},
                               status=409)
        late = ended and not rec.get("subject")
        out = _sent(h, sid, base, subject, ended)
        if out is None:
            return None
        queued = late and bool(runner.RUNNER and runner.RUNNER.end(sid))
    h.hub.worker.dirty.set()
    out.update(ok=True, session=sessions.get(sid, base), wrapup=queued)
    return h.send_json(out)


def _end(h, repo):
    """`POST /end {subject?}`: End this session. With `subject`, it is sent
    there first (`_sent`): a refused send is 400 and the session stays open.
    `sessions.end` sets `ended` and commits the subject's TUTOR.md and the
    session's artifacts; then the wrap-up turn is queued, the only thing that
    ever runs it. A second End changes nothing but retries the commit; one
    naming another subject than an ended session's is 409."""
    if not repo.stored:
        return h.send_json({"ok": False, "error": "not a session"}, status=404)
    payload = _body(h)
    if payload is None:
        return h.send_json({"ok": False, "error": "bad json"}, status=400)
    sid = os.path.basename(repo.live)
    base = os.path.dirname(os.path.dirname(repo.live))
    subject = str(payload.get("subject") or "")
    sent = {}
    with sessions.held(sid, base):
        if subject:
            rec = sessions.get(sid, base) or {}
            if _elsewhere(h, rec, base, subject):
                return None
            sent = _sent(h, sid, base, subject, True)
            if sent is None:
                return None
        try:
            rec, committed, said = sessions.end(sid, base=base)
        except sessions.NoSession:
            return h.send_json({"ok": False, "error": "no such session"},
                               status=404)
        queued = bool(runner.RUNNER and runner.RUNNER.end(sid))
    h.note("session %s ended (%s)" % (sid, said))
    h.hub.worker.dirty.set()
    out = {"ok": True, "session": rec, "committed": bool(committed),
           "detail": said, "wrapup": queued}
    out.update(sent)
    return h.send_json(out)
