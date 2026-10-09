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
    GET  /map/inside/<id>     session   one box of the subject's map
    GET  /map/thread/<id>     session   one thread's sheet
    POST /direction           session   a new direction, and a new sitting
    POST /thread/accept       session   a thread a card proposed
    POST /mode                session   teach or do, from now on
    POST /handover            session   one step written for them
    POST /dismiss-finish      session   the end-of-session offer waved off
    POST /session             session   open a sitting on the subject
    POST /text/save           session   a typed answer's draft
    POST /say                 session   a typed turn, into the session's inbox
    POST /poke                session   rebuild the payload now; queue a turn
                                        when a line that wakes is waiting
    POST /end                 session   End: `ended` set, and the wrap-up queued

`board` commands a route runs work on the session through
`TUTORBOARD_SESSION` (`_cli`), never on the subject's `live/`.
"""

import re
import time
import json
import os
import urllib.parse

from . import NOT_MINE
from ...course import syllabus
from ...course import plan
from ...course import homework
from .. import hub
from .. import multipart
from .. import spawn
from ... import sessions
from ... import direction
from ... import mode as session_mode
from ... import sense
from ...course import config
# `map` is a builtin; the module keeps the name the board calls the thing.
from ...course import map as mapping
from ...course import threads
from ...lesson import archive
from ...lesson import cards
from ...lesson import inbox
from ...lesson import turns
from ...runner import service as runner


def _cli(repo, args, **kw):
    """`board <args>` in the subject's root, on this session."""
    if repo.stored:
        kw["session"] = repo.live
    return spawn.board_cli(repo.root, args, **kw)


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

    if path.startswith("/map/inside/"):
        # ONE LEVEL DOWN THE MAP, ON A TAP AND NEVER ON THE PAYLOAD.
        #
        # The payload is rebuilt four times a second and already reads the head
        # of every source file in the repository for the top-level picture.
        # This parses files whole, which is affordable exactly because nobody
        # is looking inside a box until they ask.
        #
        # The id comes off the PATH the way an archived session's name does, and
        # it is looked up in what discovery found rather than turned into a
        # place: `map.inside` returns None for anything that is not a box or a
        # module of one, and a miss is a 404.
        want = path[len("/map/inside/"):].strip("/")
        found = mapping.inside(repo.root, want, repo.state())
        if not found:
            return h.send_json({"ok": False,
                                "error": "there is nothing inside that"},
                               status=404)
        found["ok"] = True
        return h.send_json(found)

    if path.startswith("/map/thread/"):
        # ONE THREAD'S SHEET, ON A TAP: its files, outputs, write-ups, jobs,
        # past sittings and documents. The id is looked up in the thread file
        # and never made into a path; a miss is a 404.
        want = path[len("/map/thread/"):].strip("/")
        found = mapping.thread_sheet(repo.root, want, repo.state(),
                                     archive.list_archive(repo))
        if not found:
            return h.send_json({"ok": False, "error": "no such thread"},
                               status=404)
        found["agents"] = kind_agents(repo.root)
        found["ok"] = True
        return h.send_json(found)

    return NOT_MINE


def kind_agents(root):
    """Who a sitting of each kind opened from the thread sheet is taught by.

    `{kind: {"agent": name, "why": sentence-or-""}}`: the machine's one
    provider setting for every kind alike -- who takes the next turn, and the
    resolver's sentence when that is the fallback or nobody. {} when the
    table could not be built: the sheet then draws no names.
    """
    from ... import assistants
    table = assistants.listing()
    if not table:
        return {}
    name = table.get("machine") or table.get("default") or ""
    why = str(table.get("why") or "")
    return {kind: {"agent": name, "why": why} for kind in mapping.SITTING_KINDS}


def _mark(st, node, agent=None, root=None):
    """Which box of the map this sitting is about, and which assistant writes it.

    Both belong to the sitting and are cleared by opening one that does not
    name them. A box of a thread file is a thread, and the sitting carries
    `thread` in place of `node`. The mode is not touched: it changes only by
    `POST /mode` or `board mode`.
    """
    on = None
    if node and root:
        clean, _bad = threads.read(root)
        on = threads.thread(clean, node["id"])
    st.pop("node", None)
    st.pop("thread", None)
    if on:
        st["thread"] = on["id"]
    elif node:
        st["node"] = node["id"]
    if agent:
        st["agent"] = agent
    else:
        st.pop("agent", None)


def _begin(h, repo):
    """Ask the tutor to start, without anybody tapping anything.

    THE TAP WAS THE INSTRUCTION. Somebody who chose "write the code for me" on
    the map has said what they want as plainly as they are going to; making them
    then find a second button that says "ask the tutor to begin" is the ceremony
    this whole tool exists to remove. Reported as a question, which is the worst
    way to find a defect like this: *"do I ask the tutor to begin?"*

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


def _direction(h, repo):
    """They have changed what this work is FOR. Everything below it is stale.

    THE POINT OF THE BUTTON IS THAT IT IS ONE TAP, FROM ANYWHERE, MID-EVENING.
    Asked for in these words: *"we may be balls deep in a project and I might
    realize we need a massive direction change and overhaul... I want maximum
    power, minimum pain."* Three things have to happen for that to be true, and
    doing two of them is worse than doing none -- a direction written down that
    the assistant never reads is a direction the person believes is in force.
    The tutor that reads it is new by construction: every turn is a fresh
    process, so nothing holds the old direction in a conversation.

    1. **Write it down**, at the root, where it crosses machines and is read at
       the start of every turn from now on. `tutorboard.direction`.
    2. **Open a new sitting**, which archives the lesson they are in -- still
       readable under the history button -- parks the handoff under the chapter
       it was about, and puts the new direction in the title bar. The lesson that
       was open was about the old direction; carrying it forward is the thing
       they just said to stop.
    3. **Queue the turn** that answers it, on the runner.
    """
    try:
        payload = json.loads(h.read_body().decode("utf-8") or "{}")
    except Exception:
        return h.send_json({"ok": False, "error": "bad json"}, status=400)
    text = (payload.get("text") or "").strip()
    if not text:
        return h.send_json({"ok": False,
                            "error": "say what the new direction is"}, status=400)

    was = repo.state()
    course = was.get("course") or config.read_config(repo.root)["name"] or ""
    # A RETHINK IN A WORKSPACE WITH A THREAD FILE IS ABOUT THE THREAD THE
    # SITTING IS ON. Their sentence goes to that thread, not to DIRECTION.md:
    # it rides in the inbox line and in the new sitting's `rethink`, and the
    # woken turn rewrites the thread's tasks with `board thread`. The sitting is
    # named after the thread, never after the first words of the sentence.
    clean, _bad = threads.read(repo.root)
    on = threads.thread(clean, str(was.get("thread") or "").strip())
    if on:
        kept, when = text[:direction.MAX_CHARS], time.strftime("%Y-%m-%d %H:%M")
        label = on["title"]
    else:
        kept, when = direction.write(repo.root, text)
        label = direction.label(kept)
    # THE BOX AND THE SITTING'S OWN CHOICES CARRY OVER. A direction replaces what
    # the work is about, not where on the map it is or who writes it. A sitting
    # opened without its box is one the board asks a box for on the next load,
    # and answering that files the lesson the direction just started.
    opening = ["open", course, label, "--lecture"]
    for flag, key in (("--node", "node"), ("--thread", "thread"),
                      ("--agent", "agent")):
        if was.get(key):
            opening += [flag, str(was[key])]
    _cli(repo, opening)
    if on:
        st = repo.state()
        st["rethink"] = kept
        with open(repo.state_path, "w", encoding="utf-8") as fh:
            json.dump(st, fh, indent=2)

    # Their own words, in the transcript, as a turn of theirs -- because that is
    # what it is. The card that comes back is an answer to something they said,
    # and a transcript that starts with the answer reads as the tutor deciding to
    # change direction on its own.
    tid = turns.next_turn_id(repo)
    record = {
        "id": tid, "rev": turns.turn_revision(repo, tid), "kind": "text",
        "answers": None,
        "t": time.time(),
        "iso": time.strftime("%Y-%m-%d %H:%M:%S"),
        "from": "student", "text": kept, "signal": "direction", "read": False,
    }
    turns.write_turn(repo, record)
    line = ("[direction] "
            + ((direction.RETHINK % {"id": on["id"], "title": on["title"]})
               if on else direction.CHANGED)
            + "\n\nTHEIR WORDS:\n" + kept
            + "\n\n" + sense.session_sense(repo))
    with open(repo.messages_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(dict(record, text=line)) + "\n")

    runner.wake(repo)
    h.note("the %s changed; the lesson is archived"
           % ("thread `%s`" % on["id"] if on else "direction"))
    h.hub.worker.dirty.set()
    return h.send_json({"ok": True, "chapter": label, "set": when,
                        "thread": on["id"] if on else None})


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


def _accept_thread(h, repo):
    """`POST /thread/accept {card, thread}`: add a thread a card proposed.

    The browser names the card and the id, and nothing else. The thread is read
    back off that card's own file (`cards.proposed`) and handed to `board thread
    add`, which validates it against the file like any other edit.
    """
    try:
        payload = json.loads(h.read_body().decode("utf-8") or "{}")
    except Exception:                                        # noqa: BLE001
        return h.send_json({"ok": False, "error": "bad json"}, status=400)
    card = str(payload.get("card") or "").strip()
    tid = str(payload.get("thread") or "").strip()
    one = cards.proposed(repo.cards, card, tid) if threads.ID_RE.match(tid) else None
    if not one:
        return h.send_json({"ok": False, "error": "card %s proposes no thread %r"
                            % (card, tid)}, status=404)
    state, problems = threads.proposal(repo.root, one)
    if state == "there":
        return h.send_json({"ok": True, "thread": tid, "detail": "already there"})
    if problems:
        return h.send_json({"ok": False, "error": problems[0]}, status=400)
    code, out = _cli(repo, ["thread", "add", "--repo", repo.root],
                     timeout=60, given=json.dumps(one))
    threads.forget(repo.root)
    h.hub.worker.dirty.set()
    if code != 0:
        return h.send_json({"ok": False, "error": (out or "").strip()[-300:]
                            or "board thread add refused it"}, status=400)
    return h.send_json({"ok": True, "thread": tid,
                        "detail": (out or "").strip().splitlines()[0]
                        if (out or "").strip() else "added"})


def post(h, repo, path):
    if path == "/direction":
        return _direction(h, repo)

    if path == "/thread/accept":
        return _accept_thread(h, repo)

    if path == "/mode":
        return _mode(h, repo)

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
        # A lecture or a homework sitting, chosen from the board: a chapter, a
        # problem set, or a box of the map. The mode is not a sitting's: it is
        # the session's, and only `POST /mode` changes it.
        try:
            payload = json.loads(h.read_body().decode("utf-8") or "{}")
        except Exception:
            return h.send_json({"ok": False, "error": "bad json"}, status=400)
        kind = (payload.get("session") or "").strip().lower()
        if kind not in ("lecture", "homework"):
            return h.send_json({"ok": False, "error": "bad session"}, status=400)
        want = (payload.get("hw") or "").strip()
        chapter = (payload.get("chapter") or "").strip()

        # A tap on the map sends the box's id and, where a numbered step was
        # tapped, that step's label -- and NEITHER is carried through as typed.
        # Both are looked up in what the map and the plan actually hold, and
        # the sitting's label is built here from what came back.
        #
        # An assistant named for this sitting is recorded and never consulted:
        # who takes a turn is the machine's one provider setting.
        agent = config.clean_agent(payload.get("agent"))
        # Whether the request also means "and get on with it". Sent by the map's
        # own sheet, where choosing a way to work IS the instruction; not by the
        # contents drawer.
        start = bool(payload.get("begin"))
        node = None
        node_id = str(payload.get("node") or payload.get("thread") or "").strip()
        if node_id:
            node = mapping.find(repo.root, node_id, repo.state())
            if not node:
                return h.send_json({"ok": False, "error": "no such part of the map"},
                                      status=400)
        step = None
        step_label = str(payload.get("step") or "").strip()
        if step_label:
            for x in plan.steps(repo.root):
                if x["label"] == step_label:
                    step = x
                    break
            if not step:
                return h.send_json({"ok": False, "error": "no such step"},
                                      status=400)
        if not chapter and (step or node):
            chapter = step["label"] if step else node["name"]

        # THE BOX WHOSE SITTING IS ALREADY OPEN IS A WAY BACK INTO IT, NOT A NEW
        # ONE. Opening files the lesson away, so a tap on the box you are already
        # working in must not empty the board. A different step on the same box
        # is still a new sitting.
        here = repo.state()
        if (kind == "lecture" and node and not step
                and config.sitting_box(here) == node["id"]
                and (here.get("session") or "lecture") == "lecture"
                and not here.get("finished")):
            begun = start and not cards.load_cards(repo, [])
            if begun:
                _begin(h, repo)
            h.hub.worker.dirty.set()
            return h.send_json({"ok": True, "session": kind, "resumed": True,
                                "begun": begun})

        # Moving to a different chapter is starting a different lesson, and
        # `board open` is what starts one: it files the current lesson away
        # whole -- cards, turns and answers together -- so the one being left
        # is still readable under the history button rather than being
        # overwritten by the next.
        if chapter:
            # A chapter in a book course, or a STEP in a project's plan -- which
            # is the same tap on the same drawer and has to be checked the same
            # way: against what the repository actually has, never constructed
            # from the request. A project has no chapters and its steps are not
            # invented here either; they are the lines of the file its README
            # points at, which is the only thing that says what comes next.
            known = [syllabus.label(c) for c in syllabus.chapters(repo.root)]
            known += [x["label"] for x in plan.steps(repo.root)]
            # ...unless this label was BUILT here, out of a box or a step that
            # has already been looked up. Checking it again against the chapter
            # list would refuse every part of the map, none of which is a
            # chapter of anything.
            if chapter not in known and not (node or step):
                return h.send_json({"ok": False, "error": "no such chapter"},
                                      status=400)
            course = repo.state().get("course") or config.read_config(repo.root)["name"] or ""
            args = ["open", course, chapter,
                    "--lecture" if kind == "lecture" else "--homework"]
            if node:
                args += ["--node", node["id"]]
            if agent:
                args += ["--agent", agent]
            # A chapter gets a tutor that knows only it: every turn is a fresh
            # process, so nothing carries Chapter 1 into Chapter 3.
            _cli(repo, args)

        st = repo.state()
        st["session"] = kind
        _mark(st, node, agent, repo.root)
        if kind == "homework":
            # Only a set this repository actually has. A name from the
            # request never reaches the filesystem.
            every = {x["name"]: x for x in homework.sets(repo.root)}
            chosen = every.get(want)
            if want and not chosen:
                return h.send_json({"ok": False, "error": "no such set"}, status=400)
            if chosen:
                if not chapter and st.get("hw") != chosen["rel"]:
                    course = st.get("course") or config.read_config(repo.root)["name"] or ""
                    # `--agent` goes through `open`, because this call REPLACES
                    # the state `_mark` has just written: it re-reads from disk
                    # below, so anything patched on above it is lost here.
                    args = ["open", course, chosen["name"],
                            "--homework", "--set", chosen["name"]]
                    if agent:
                        args += ["--agent", agent]
                    _cli(repo, args)
                    st = repo.state()
                    st["session"] = kind
                    _mark(st, node, agent, repo.root)
                st["hw"] = chosen["rel"]
                st["chapter"] = chosen["name"]
        else:
            st.pop("hw", None)
        with open(repo.state_path, "w", encoding="utf-8") as fh:
            json.dump(st, fh, indent=2)
        if start:
            _begin(h, repo)
        h.hub.worker.dirty.set()
        return h.send_json({"ok": True, "session": kind, "hw": st.get("hw"),
                            "begun": start})

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
