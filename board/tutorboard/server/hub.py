"""One payload, built once, pushed to every browser that has the board open.
"""

import hashlib
import json
import os
import stat
import threading
import time

from .. import coursemacros, paths
from .. import (assistants, colibri, direction, fenced, missions, news,
                writeups)
from .. import jobs as slurm_jobs
from ..course import config, homework
from ..lesson import archive, cards, git, notes, slate, state, turns, uploads

# The payload is rebuilt only when something says it changed: a route's dirty
# mark (`worker.dirty`), a change the sentinel sees in the session files it
# stats every SENTINEL_SECONDS, or SLOW_SECONDS passing, for sources nothing
# marks (git status, built papers, missions, Colibri).
SENTINEL_SECONDS = 1.0
SLOW_SECONDS = 30.0

# Keys of the payload that are carried but never pushed on their own. See `tick`.
QUIET = ("notes", "notes_sent")


def sentinel(live):
    """The mtime and size of every watched path under `live`, and of each entry
    of a watched directory. Equal answers mean nothing watched changed."""
    out = []
    for rel in paths.SESSION_WATCHED:
        where = os.path.join(live, rel)
        try:
            st = os.stat(where)
        except OSError:
            out.append((rel, None, None))
            continue
        out.append((rel, st.st_mtime_ns, st.st_size))
        if not stat.S_ISDIR(st.st_mode):
            continue
        try:
            entries = list(os.scandir(where))
        except OSError:
            continue
        for e in entries:
            try:
                es = e.stat()
            except OSError:
                continue
            out.append((rel + "/" + e.name, es.st_mtime_ns, es.st_size))
    out.sort(key=lambda t: t[0])
    return out


class Hub:
    """No lock: each subscriber is a (queue, condition) pair, and appending to,
    removing from or copying the list of them is one atomic step."""

    def __init__(self, repo, worker):
        self.repo = repo
        self.worker = worker
        self.clients = []
        self.payload = "{}"
        self.digest = ""
        self.ink = ""
        self.seq = 0
        # Set by `stop`: the session registry dropped this hub, so its loop
        # ends and any stream still on it closes, to reconnect to a new one.
        self.stopped = threading.Event()

    def stop(self):
        self.stopped.set()
        self.worker.dirty.set()

    def subscribe(self):
        client = ([], threading.Condition())
        self.clients.append(client)
        return client

    def unsubscribe(self, client):
        try:
            self.clients.remove(client)
        except ValueError:
            pass

    def build(self):
        jobs = []
        on_board = cards.load_cards(self.repo, jobs)
        if jobs:
            self.worker.submit(jobs)
        board_state = self.repo.state()
        cfg = config.read_config(self.repo.root)
        board_state.setdefault("course", cfg["name"])
        # WHO WRITES THE CODE: the session's mode, teach unless session.json
        # says do. `stance_now` carries the same word for the client's busy
        # strip until T51 deletes the old sitting UI.
        board_state["mode"] = config.mode_of(board_state)
        board_state["stance_now"] = board_state["mode"]
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
            # THE MACROS THIS COURSE WRITES IN. The board typesets twice and
            # only one of the two engines was being told: LaTeX loads the
            # course's own `latex/coursemacros.sty` and then the board's
            # `\providecommand` gap-filler, so the course wins there; KaTeX had
            # `web/macros.js` and nothing else, so a macro the course defines and
            # the board does not reached the glass as source -- or, worse, at the
            # board's arity with the argument silently dropped. Same rule on both
            # sides now: the course's definition wins. See
            # `tutorboard/coursemacros.py`.
            "macros": coursemacros.for_workspace(self.repo.root),
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
        # AND THE SLURM JOBS REGISTERED HERE THAT HAVE NOT ENDED, so the busy
        # strip says "running" between turns as well as the box. A read of one
        # small file; the daemon's poll is what moves it. See `jobs.py`.
        data["jobs"] = slurm_jobs.running(self.repo.root)
        # AND A DOCUMENT ASKED FOR FROM THE SITTING THAT IS OPEN. The turn that
        # writes one is told to write no card, so it is invisible on the board by
        # construction -- which leaves "I asked for a deck and nothing happened"
        # with nowhere to be answered. The record says it is being written and
        # then says it is in the library. Cheap when there is nothing to say,
        # which is nearly always; see `tutorboard/writeups.py`.
        data["writeups"] = writeups.waiting(self.repo)
        return data

    def poll_loop(self):
        """Rebuild on a dirty mark, a sentinel change, or every SLOW_SECONDS.

        The mark is cleared before the sentinel is read and the sentinel before
        the build, so a change landing mid-build triggers one more pass.
        """
        seen = None
        built = 0.0
        dirty = self.worker.dirty
        while not self.stopped.is_set():
            marked = dirty.is_set()
            if marked:
                dirty.clear()
            now = sentinel(self.repo.live)
            if marked or now != seen or time.monotonic() - built >= SLOW_SECONDS:
                seen = now
                built = time.monotonic()
                try:
                    self.tick()
                except Exception:
                    pass
            dirty.wait(SENTINEL_SECONDS)

    def tick(self):
        """Build the payload, and push it if the lesson changed."""
        data = self.build()
        # The digest covers content only; seq is stamped afterwards, or every
        # poll would look like a change and loop forever.
        #
        # INK ALONE IS NOT A CHANGE WORTH PUSHING. Every autosave of a card's
        # marks rewrites `notes`, and pushing that re-sends the whole lesson and
        # re-renders it on the tablet about a second after each stroke -- the
        # middle of the next one, which then stutters or is lost. The page that
        # drew the ink already has it, and `Annotate.load` adopts only cards it
        # has never seen. The payload is still rebuilt, so a reload or the next
        # real push carries the ink as it is on disk.
        lesson = {k: v for k, v in data.items() if k not in QUIET}
        blob = json.dumps(lesson, sort_keys=True)
        digest = hashlib.sha1(blob.encode("utf-8")).hexdigest()
        ink = json.dumps([data.get(k) for k in QUIET], sort_keys=True)
        ink = hashlib.sha1(ink.encode("utf-8")).hexdigest()
        if digest != self.digest:
            self.digest = digest
            self.ink = ink
            self.seq += 1
            data["seq"] = self.seq
            self.payload = json.dumps(data)
            self.push(self.payload)
        elif ink != self.ink:
            self.ink = ink
            data["seq"] = self.seq
            self.payload = json.dumps(data)

    def push(self, payload):
        targets = list(self.clients)
        for q, cv in targets:
            with cv:
                q.append(payload)
                cv.notify()


# ---------------------------------------------------------------------------
# multipart parsing (hand rolled; cgi.FieldStorage is deprecated)
# ---------------------------------------------------------------------------
