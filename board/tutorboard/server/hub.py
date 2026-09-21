"""One payload, built once, pushed to every browser that has the board open.
"""

import hashlib
import json
import os
import threading
import time

from .. import assistants, colibri, direction, fenced, missions, news, writeups
from . import spawn
from ..course import config, homework
from ..lesson import archive, cards, git, notes, slate, state, turns, uploads

# How often the worker looks for a change nothing told it about. The board is
# pushed to, not polled, so this is the safety net rather than the mechanism.
POLL_SECONDS = 0.25


class Hub:
    def __init__(self, repo, worker):
        self.repo = repo
        self.worker = worker
        self.lock = threading.Lock()
        self.clients = []
        self.payload = "{}"
        self.digest = ""
        self.seq = 0

    def subscribe(self):
        q = []
        cv = threading.Condition()
        client = (q, cv)
        with self.lock:
            self.clients.append(client)
        return client

    def unsubscribe(self, client):
        with self.lock:
            if client in self.clients:
                self.clients.remove(client)

    def build(self):
        jobs = []
        on_board = cards.load_cards(self.repo, jobs)
        if jobs:
            self.worker.submit(jobs)
        board_state = self.repo.state()
        cfg = config.read_config(self.repo.root)
        board_state.setdefault("course", cfg["name"])
        # WHAT THE REPOSITORY ITSELF SAYS about who writes the code, which is
        # not always what this sitting says. The board needs both: the chooser
        # shows which is in force, and the busy strip has to know whether the
        # turn running now is one that DOES the work -- because in one of those
        # a card landing means the work is starting rather than finished. It was
        # a constant `"teach"` in the client until now, which is a guess that is
        # wrong in exactly the repositories this matters most in.
        board_state["declared_stance"] = cfg.get("stance") or "teach"
        # AND WHAT THIS SITTING IS ACTUALLY RUNNING UNDER, resolved once, here.
        # A sitting nobody opened from the map names no aim, and the answer then
        # comes from the workspace or from its family's default in `atlas.json` --
        # which the client cannot read and must not re-derive. The chooser shows
        # `aim_now`, and the busy strip asks `stance_now` whether the turn running
        # is one that DOES the work. See `course/config.aim_for`.
        board_state["aim_now"] = config.aim_for(self.repo.root, board_state)
        board_state["stance_now"] = config.stance_for(self.repo.root, board_state)
        data = {
            "state": board_state,
            "cards": on_board,
            "turns": turns.load_turns(self.repo),
            "messages": notes.load_messages(self.repo),
            "uploads": uploads.load_uploads(self.repo),
            "slate": slate.load_slate(self.repo),
            "notes": notes.load_notes(self.repo),
            "notes_sent": notes.load_notes_sent(self.repo),
            "text_drafts": notes.load_text_drafts(self.repo),
            "unsaved": git.repo_dirty(self.repo),
            "push": state.load_push(self.repo),
            "export": state.load_export(self.repo),
            # Which documents can be taken off the board, or read on it, RIGHT
            # NOW -- not which one was just built. A document is a file, not an
            # event, and the controls for it were living in the banner of the
            # build that produced it. See `state.load_papers`.
            "papers": state.load_papers(self.repo),
            "agent": state.load_agent(self.repo),
            # What is in the inbox that nothing has taken. The board's answer to
            # "I sent that and nothing is happening", and it comes off disk
            # rather than out of the browser's memory so it is still true after
            # a reload. See `notes.waiting`.
            "waiting": notes.waiting(self.repo),
            "history": len(archive.list_archive(self.repo)),
            # WHO CAN BE ASKED TO TUTOR THIS SITTING, and what the local model's
            # server is doing right now. Both are here rather than behind a
            # request of their own because the chooser is drawn from the payload
            # like everything else on the page, and because the second one has a
            # state that CHANGES while nobody taps anything -- a job pending for
            # ten minutes and then loading for eight.
            #
            # Neither costs a poll. `assistants.listing` shells out once per
            # board process and `colibri.status` caches its `squeue` for fifteen
            # seconds, which is the rule `machines.held_nodes` already follows.
            "assistants": assistants.listing(),
            "colibri": colibri.status(),
            # AND WHETHER THIS WORKSPACE HOLDS A FENCE, which is the third
            # thing the chooser needs and the one nothing said. The registry
            # above carries which assistant may read one -- the recipe with
            # `private` on it -- so naming it is a lookup in what is already
            # here rather than a second list. The names, so the row can say
            # what a hosted pick will not be able to open. See `fenced.holds`.
            "fenced": list(fenced.holds(self.repo.root)),
        }
        # Only in a homework sitting, and read from the .tex itself rather than
        # from a record the board keeps: the file is the truth, the assistant
        # edits it directly, and two sources of truth drift.
        # In a homework sitting, always. In a lecture, once a set has been bound
        # to it -- a lecture that works through a section's exercises is writing
        # them up into the same file, and the state of that file is exactly as
        # invisible from an iPad either way.
        # Bound means pinned OR named by the session label. Requiring the pin
        # made the panel depend on somebody having run `board hw use`, so a
        # sitting opened as "Ch 4" filled no file and said nothing about it.
        bound = None
        try:
            bound = homework.bound(self.repo.root, board_state)
        except Exception:
            bound = None
        if board_state.get("session") == "homework" or bound:
            data["hw"] = state.load_hw(self.repo)
        # The names alone, always: the board offers them when switching, and a
        # lecture has no `hw` block to carry them in. A glob, not a parse.
        try:
            data["sets"] = [x["name"] for x in homework.sets(self.repo.root)][:40]
        except Exception:
            data["sets"] = []
        data["contents"] = state.load_contents(self.repo)
        # Always, in both kinds of repository: a review is chosen from the board
        # and the chooser needs something to offer before the sitting exists.
        data["review"] = state.load_review(self.repo)
        # And the same for a walkthrough, whose scope is a file in this
        # repository. A repository with no source at all -- a narrative one, all
        # prose and no machinery -- sends nothing rather than an empty list, and
        # the board does not offer the sitting.
        data["walk"] = state.load_walk(self.repo)
        # What this project says comes next, and what it can be shown. Both are
        # what a book course gets from its chapter table, arriving from the two
        # places a project actually keeps them: the plan its README points at,
        # and the documents somebody already wrote about how it works.
        data["plan"] = state.load_plan(self.repo)
        data["reading"] = state.load_reading(self.repo)
        # And what it PRODUCED, which is the other half and had no route to the
        # glass at all. A figure a pipeline wrote could only reach a lesson by
        # somebody copying it into the inbox -- a second copy of a file the next
        # job overwrites. See `course/results.py`.
        data["results"] = state.load_results(self.repo)
        # And the picture the whole lot hangs on. A course opens on this rather
        # than on an empty board: the working parts, what is done and what is
        # not, and a tap on any of them to start work there. Every repository
        # has one, drawn or derived. See `course/map.py`.
        data["map"] = state.load_map(self.repo)
        # WHAT THIS WORKSPACE IS FOR, when they have changed it. The panel that
        # changes it opens showing what is in force -- a person about to replace
        # a direction should be able to read the one they are replacing, and on
        # a device that has been closed since they set it there is nowhere else
        # it could come from. None where nothing is set, so the board can tell
        # "never changed" from "changed to nothing".
        said, when = direction.read(self.repo.root)
        data["direction"] = {"text": said, "when": when} if said else None
        # AN ANSWER THAT LANDED SOMEWHERE ELSE. A turn set going in one
        # workspace goes on running while its person works in another, and until
        # this there was nothing anywhere that said it had finished -- the only
        # way to find out was to switch back and look. `news.waiting` is cached
        # hard; see the module.
        data["news"] = news.waiting(self.repo)
        # AND WHAT IS STILL RUNNING THERE. The same sentence in the present
        # tense: `news` is a card that landed, a mission is a job that was set
        # going and has not come back yet. A closed lid does not end one, so the
        # board that comes up tomorrow reads them off disk rather than out of a
        # browser's memory. Cached hard; see `missions.py`.
        data["missions"] = missions.waiting(self.repo)
        # AND A DOCUMENT ASKED FOR FROM THE SITTING THAT IS OPEN. The turn that
        # writes one is told to write no card, so it is invisible on the board by
        # construction -- which leaves "I asked for a deck and nothing happened"
        # with nowhere to be answered. The record says it is being written and
        # then says it is in the library. Cheap when there is nothing to say,
        # which is nearly always; see `tutorboard/writeups.py`.
        data["writeups"] = writeups.waiting(self.repo)
        return data

    def poll_loop(self):
        while True:
            # A MISSION THAT WAS TOLD TO SHIP ITSELF, AND HAS FINISHED.
            #
            # Here because this loop is the only thing in the tool that runs
            # without anybody asking it to and outlives the request that started
            # it: a mission ends in a workspace with no board and no browser on
            # it, so nothing there is going to notice. Throttled inside
            # `ship_missions` to one walk every twenty seconds, and the ship is
            # claimed with an exclusive create, so every board on the machine
            # running this loop still hands each mission over exactly once.
            try:
                spawn.ship_missions()
            except Exception:
                pass

            # AND A MISSION WHOSE NODE WENT AWAY UNDER IT.
            #
            # Here for the same reason as the line above: this loop is the only
            # thing in the tool that runs without anybody asking it to and
            # outlives the request that started it. A colibri client is a step of
            # the serve job's allocation and dies with it, and where the board
            # went at the same moment there is nothing left anywhere to notice.
            # Throttled inside `carry_missions`, and each pick-up is claimed with
            # an exclusive create, so every board running this loop still picks
            # each mission up exactly once.
            try:
                spawn.carry_missions()
            except Exception:
                pass
            try:
                data = self.build()
                # The digest covers content only; seq is stamped afterwards, or
                # every poll would look like a change and loop forever.
                blob = json.dumps(data, sort_keys=True)
                digest = hashlib.sha1(blob.encode("utf-8")).hexdigest()
                if digest != self.digest:
                    self.digest = digest
                    self.seq += 1
                    data["seq"] = self.seq
                    self.payload = json.dumps(data)
                    self.push(self.payload)
            except Exception:
                pass
            if self.worker.dirty.wait(POLL_SECONDS):
                self.worker.dirty.clear()

    def push(self, payload):
        with self.lock:
            targets = list(self.clients)
        for q, cv in targets:
            with cv:
                q.append(payload)
                cv.notify()


# ---------------------------------------------------------------------------
# multipart parsing (hand rolled; cgi.FieldStorage is deprecated)
# ---------------------------------------------------------------------------
