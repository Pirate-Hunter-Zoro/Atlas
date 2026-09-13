"""The lesson: what is on the board, what kind of sitting it is, and the
typed half of the conversation.
"""

import re
import time
import json
import os

from . import NOT_MINE
from ...course import syllabus
from ...course import review
from ...course import walk
from ...course import plan
from ...course import homework
from .. import multipart
from .. import spawn
from ... import sense
from ...course import config
# `map` is a builtin; the module keeps the name the board calls the thing.
from ...course import map as mapping
from ...lesson import archive
from ...lesson import turns


def get(h, repo, path):
    if path == "/events":
        return h.sse(h.server.hub)

    if path == "/board.json":
        return h.send_bytes(h.server.hub.payload.encode("utf-8"), "application/json")

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


def _mark(st, node, aim):
    """Which box of the map this sitting is about, and what it is for.

    Both belong to the SITTING and not to the repository, so both are cleared by
    opening one that does not name them -- the same rule a sitting stance
    follows, and for the same reason: a box chosen for an evening's work is not
    a statement about what the repository is.
    """
    if node:
        st["node"] = node["id"]
    else:
        st.pop("node", None)
    if aim:
        st["aim"] = aim
    else:
        st.pop("aim", None)


def post(h, repo, path):
    if path == "/dismiss-finish":
        st = repo.state()
        st.pop("finished", None)
        with open(repo.state_path, "w", encoding="utf-8") as fh:
            json.dump(st, fh, indent=2)
        h.server.hub.worker.dirty.set()
        return h.send_json({"ok": True})

    if path == "/session":
        # Which kind of sitting this is, chosen from the board. It was a
        # terminal-only decision, which meant a student who wanted help with
        # a problem set had to find a keyboard to say so.
        try:
            payload = json.loads(h.read_body().decode("utf-8") or "{}")
        except Exception:
            return h.send_json({"ok": False, "error": "bad json"}, status=400)
        kind = (payload.get("session") or "").strip().lower()
        if kind not in ("lecture", "homework", "review", "walk", "make"):
            return h.send_json({"ok": False, "error": "bad session"}, status=400)
        want = (payload.get("hw") or "").strip()
        chapter = (payload.get("chapter") or "").strip()

        # WHAT THIS SITTING IS ABOUT, AND WHAT IT IS FOR.
        #
        # A tap on the map sends the box's id and, where a numbered step was
        # tapped, that step's label -- and NEITHER is carried through as typed.
        # The box is looked up in what `course/map.py` discovered and the step in
        # what the plan actually says, exactly as a chapter name and a filename
        # are, because a name from a browser that reaches a prompt is a name that
        # can send the tutor to machinery that does not exist.
        #
        # The sitting's LABEL is then built here from what came back, rather than
        # sent. That is what lets a box be opened at all: "evaluate" is not a
        # chapter of anything and would fail the check below, and asking the
        # browser to send a label it invented is the same hole in a nicer coat.
        aim = config.clean_aim(payload.get("aim"))
        node = None
        node_id = str(payload.get("node") or "").strip()
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
        # This sitting's stance, where the person opening it chose one. A word
        # that is not a stance is dropped rather than refused: the request is
        # about which sitting to open, and failing the whole of it over a
        # spelling would leave them on the lesson they were trying to leave.
        stance = config.clean_stance(payload.get("stance"))

        # A test review is held over a scope the student picks, and a scope is
        # a list: a test is not one chapter. Every name in it is matched
        # against what this repository actually has before anything is
        # written, exactly as a problem set name is -- nothing typed reaches
        # the filesystem and nothing invented reaches the tutor's prompt.
        if kind == "review":
            over = payload.get("over")
            if not isinstance(over, list):
                over = [over] if over else []
            chosen, unknown = review.resolve(repo.root, [str(x) for x in over])
            if unknown:
                return h.send_json({"ok": False, "error": "no such chapter",
                                       "unknown": unknown[:8]}, status=400)
            if not chosen:
                # A review over nothing is not a sitting, and opening one
                # would archive the lesson they are in to no purpose.
                return h.send_json({"ok": False, "error": "nothing chosen"},
                                      status=400)
            names = [u["name"] for u in chosen]
            of = review.kind(repo.root) or "chapters"
            course = repo.state().get("course") or config.read_config(repo.root)["name"] or ""
            args = ["open", course, review.sitting_label(chosen, of), "--review"]
            for n in names:
                args += ["--over", n]
            spawn.board_cli(repo.root, args)
            st = repo.state()
            st["session"] = kind
            st["review"] = names
            _mark(st, node, aim)
            st.pop("hw", None)
            with open(repo.state_path, "w", encoding="utf-8") as fh:
                json.dump(st, fh, indent=2)
            h.server.hub.worker.dirty.set()
            return h.send_json({"ok": True, "session": kind, "review": names})

        # A walkthrough is the same shape of request as a review -- a scope the
        # student chose, checked against what the repository actually has before
        # a word of it reaches the filesystem or the tutor's prompt -- over a
        # different list. A file that is not in this repository is refused by
        # name rather than dropped, because a walkthrough over two files when
        # three were tapped teaches the wrong two.
        if kind == "walk":
            over = payload.get("over")
            if not isinstance(over, list):
                over = [over] if over else []
            chosen, unknown = walk.resolve(repo.root, [str(x) for x in over])
            if unknown:
                return h.send_json({"ok": False, "error": "no such file",
                                       "unknown": unknown[:8]}, status=400)
            if not chosen:
                # Opening one archives the lesson they are in, so a walkthrough
                # over nothing would file a lesson away to no purpose.
                return h.send_json({"ok": False, "error": "nothing chosen"},
                                      status=400)
            names = [u["name"] for u in chosen]
            course = repo.state().get("course") or config.read_config(repo.root)["name"] or ""
            args = ["open", course, walk.sitting_label(chosen), "--walk"]
            for n in names:
                args += ["--over", n]
            if stance:
                args += ["--stance", stance]
            spawn.board_cli(repo.root, args)
            st = repo.state()
            st["session"] = kind
            st["walk"] = names
            _mark(st, node, aim)
            st.pop("hw", None)
            st.pop("review", None)
            with open(repo.state_path, "w", encoding="utf-8") as fh:
                json.dump(st, fh, indent=2)
            h.server.hub.worker.dirty.set()
            return h.send_json({"ok": True, "session": kind, "walk": names})

        # A SITTING WHOSE PRODUCT IS A DOCUMENT rather than an answer.
        #
        # Every other sitting on this board ends with the student having
        # produced something -- a proof, a problem written up, an answer set
        # cold. "Write this up as a paper" and "build me a deck about it" are
        # neither a lecture nor an exercise, and asking for them meant a
        # terminal and a different tool. The scope is the box that was tapped,
        # which is the whole reason this can be one tap: the tutor is told what
        # to write about instead of being asked.
        if kind == "make":
            makes = str(payload.get("makes") or "").strip().lower()
            if makes not in ("paper", "slides"):
                return h.send_json({"ok": False, "error": "paper or slides"},
                                      status=400)
            course = repo.state().get("course") or config.read_config(repo.root)["name"] or ""
            label = chapter or ("A write-up" if makes == "paper" else "A deck")
            args = ["open", course, label, "--make", makes]
            if node:
                args += ["--node", node["id"]]
            if aim:
                args += ["--aim", aim]
            spawn.board_cli(repo.root, args)
            st = repo.state()
            st["session"] = kind
            st["makes"] = makes
            st.pop("hw", None)
            st.pop("review", None)
            st.pop("walk", None)
            _mark(st, node, aim)
            with open(repo.state_path, "w", encoding="utf-8") as fh:
                json.dump(st, fh, indent=2)
            h.server.hub.worker.dirty.set()
            return h.send_json({"ok": True, "session": kind, "makes": makes})

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
            if aim:
                args += ["--aim", aim]
            if stance:
                args += ["--stance", stance]
            spawn.board_cli(repo.root, args)
            # A chapter gets its own tutor.
            #
            # An assistant is long-lived on purpose -- one that survives being
            # left still has the lesson in its head when you come back -- and
            # across a chapter that is the wrong thing to have in its head.
            # Reported an hour into Chapter 3: "the tutor is telling me that
            # problems from chapter 1 are still incomplete. I don't like
            # that." Its own conversation held the whole of Chapter 1, and no
            # file on disk could have told it otherwise.
            #
            # On its own thread: stopping is a wrap-up TURN, which is a model
            # call, and the person tapping a chapter is not waiting a minute
            # to see the chapter change. The handoff that turn writes is
            # stamped with the chapter it was teaching, so it is filed under
            # that chapter rather than read as this one's.
            spawn.fresh_tutor(repo.root, course)

        st = repo.state()
        st["session"] = kind
        st.pop("review", None)
        st.pop("walk", None)
        st.pop("makes", None)
        _mark(st, node, aim)
        # A stance chosen on the board belongs to the sitting being opened, so
        # it is written when one is named and cleared when one is not -- which
        # is how tapping `lecture` gets the repository's own answer back
        # without anybody having to know there was an override in the first
        # place.
        if stance:
            st["stance"] = stance
        else:
            st.pop("stance", None)
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
                    spawn.board_cli(repo.root, ["open", course, chosen["name"],
                                          "--homework", "--set", chosen["name"]])
                    st = repo.state()
                    st["session"] = kind
                st["hw"] = chosen["rel"]
                st["chapter"] = chosen["name"]
        else:
            st.pop("hw", None)
        with open(repo.state_path, "w", encoding="utf-8") as fh:
            json.dump(st, fh, indent=2)
        h.server.hub.worker.dirty.set()
        return h.send_json({"ok": True, "session": kind, "hw": st.get("hw")})

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
        h.server.hub.worker.dirty.set()
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
        # What lands in the inbox is what `board wait` prints, and in a
        # headless session that string IS the prompt the assistant is woken
        # with. A bare "[begin]" tells it nothing, so a signal sent without a
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
        # Including "ask the tutor to begin", which is the one signal whose
        # whole purpose is a board with nobody on it. It used to put a line in
        # an inbox and hope: a tap on that button with no daemon running was a
        # tap that did nothing for ever, and the board went on saying "no tutor
        # attached" with the request sitting on disk beside it.
        if spawn.wake_tutor(repo):
            h.note("nothing was reading the board; starting a tutor")
        h.server.hub.worker.dirty.set()
        return h.send_json({"ok": True, "turn": tid, "rev": rev})
    return NOT_MINE
