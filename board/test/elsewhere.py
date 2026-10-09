#!/usr/bin/env python3
"""Work that came back while nobody was looking, and a turn that says what it is.

TWO REPORTS, ONE EVENING, AND THEY ARE THE SAME COMPLAINT FROM TWO DISTANCES.

    "I got left hanging for a bit while it was thinking and modifying the plan -
     I want a visual indication that the replanning is still happening like I get
     when waiting on a tutor response."

    "maybe something I give the agent to do or think about is going to take a
     while. I want to be able to go into a different section of a project, or a
     different fucking project completely, and put other agents to work on other
     things while the first one is working. We should set up a notification
     system where if a response that takes a while comes back in a session, I'll
     get notified somewhere in the app and can click that notification to take me
     back to that tutoring session."

The first is about a turn that is running in front of you and says nothing. The
second is about a turn that finished behind you and said nothing. What is
guarded here is the server's half of both: the daemon recording WHAT a turn was
woken for, and the walk that answers "has anything landed anywhere else" off a
shared filesystem with nothing registered anywhere.

The client's half is `test/notify.js` and `test/hanging.js`.
"""

import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tutorboard import (colibri, fenced, machine, machines, missions,
                        news, progress)
from tutorboard.course import repo as course_repo
from tutorboard.lesson import notes, state, turns
from tutorboard.server import handler, hub, tikz
from tutorboard.server.routes import machines as machines_route

fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def card(root, num, slug, body, when=None, title=""):
    p = os.path.join(root, "live", "cards", "%s-%s.md" % (num, slug))
    head = "---\nkind: lesson\ntitle: %s\n---\n" % title if title else ""
    write(p, head + body + "\n")
    if when:
        os.utime(p, (when, when))
    return p


base = tempfile.mkdtemp(prefix="tutor-elsewhere-")
was_courses = os.environ.get("TUTORBOARD_COURSES")
try:
    psych = os.path.join(base, "projects", "PSYCH-ASR")
    trd = os.path.join(base, "projects", "TRD-EHR")
    galois = os.path.join(base, "courses", "Galois-Theory")
    for r in (psych, trd, galois):
        write(os.path.join(r, "tutorboard.json"), json.dumps({"name": os.path.basename(r)}))
        os.makedirs(os.path.join(r, "live", "cards"), exist_ok=True)
    os.environ["TUTORBOARD_COURSES"] = base

    now = time.time()
    # Where the person is sitting.
    here = course_repo.Repo(galois)
    card(galois, "0001", "fields", "A field is a ring in which every non-zero "
         "element has an inverse.", now - 3600)
    # And two workspaces they are not.
    card(psych, "0013", "plan", "About to run the four typists.", now - 3000)
    card(trd, "0007", "packet", "The packet builds.", now - 2000)

    # ------------------------------------------------------------------
    # nothing is news until somebody has looked once
    # ------------------------------------------------------------------
    # With no marker at all every lesson on the machine is "newer than never",
    # so the first board to come up would announce every workspace it can see,
    # each about something that happened last week. The first sight starts the
    # clock instead.
    check("a workspace nobody has opened since this shipped is not news",
          news.elsewhere(galois) == [])
    check("and it has a marker now, so the NEXT card in it is",
          news.seen_at(psych) is not None)
    check("and the workspace being read is never in the list about itself",
          all(n["id"] != "courses/Galois-Theory" for n in news.elsewhere(galois)))

    # ------------------------------------------------------------------
    # a turn finishes somewhere else
    # ------------------------------------------------------------------
    card(psych, "0014", "typists", "All four typists agree on every turn but "
         "two.", now - 240, title="the four typists agree")
    got = news.elsewhere(galois)
    check("a card written while nobody was looking is news",
          [n["id"] for n in got] == ["projects/PSYCH-ASR"])
    check("and it says which card, so the notification can point at the answer",
          got and got[0]["card"] == "0014")
    check("and what the card calls itself, when it calls itself anything",
          got and got[0]["title"] == "the four typists agree")
    check("and when it landed, which is what the row counts from",
          got and abs(got[0]["when"] - (now - 240)) < 2)

    # Two at once, newest first, because the whole point is that more than one
    # turn can be running.
    card(trd, "0008", "results", "The grid finished.", now - 30)
    got = news.elsewhere(galois)
    check("two of them are two rows, newest first",
          [n["id"] for n in got] == ["projects/TRD-EHR", "projects/PSYCH-ASR"])

    # ------------------------------------------------------------------
    # and reading it is what clears it
    # ------------------------------------------------------------------
    news.mark_seen(psych)
    check("looking at a workspace clears its notification and nothing else's",
          [n["id"] for n in news.elsewhere(galois)] == ["projects/TRD-EHR"])
    card(psych, "0015", "tie", "And here is the tie-break.", time.time())
    check("and the next card in it is news again",
          len(news.elsewhere(galois)) == 2)

    # ------------------------------------------------------------------
    # a lesson from last month is not tonight's news
    # ------------------------------------------------------------------
    old = os.path.join(base, "courses", "Probability")
    write(os.path.join(old, "tutorboard.json"), "{}\n")
    os.makedirs(os.path.join(old, "live", "cards"), exist_ok=True)
    card(old, "0004", "bayes", "Bayes.", now - 40 * 24 * 3600)
    check("a card from last month is history rather than news",
          all(n["id"] != "courses/Probability" for n in news.elsewhere(galois)))

    # ------------------------------------------------------------------
    # the marker is a marker, and it cannot lose a lesson
    # ------------------------------------------------------------------
    check("the marker lives in the lesson directory, which no repository tracks",
          os.path.basename(news.SEEN).startswith(".")
          and os.path.isfile(os.path.join(psych, "live", news.SEEN)))
    with open(os.path.join(psych, "live", news.SEEN), "w", encoding="utf-8") as fh:
        fh.write("{ this is not json")
    check("a marker something corrupted reads as never seen rather than throwing",
          news.seen_at(psych) is None)
    check("and the walk still answers", isinstance(news.elsewhere(galois), list))

    # ------------------------------------------------------------------
    # the front door draws the same fact
    # ------------------------------------------------------------------
    news.forget()
    machines._ATLAS["value"] = None
    payload = machines.atlas_payload(here)
    by_id = {c["id"]: c for c in payload["workspaces"]}
    check("every workspace card says whether it is holding an unread answer",
          all("news" in c for c in payload["workspaces"]))
    check("and the one the board is serving is never marked unread",
          by_id["courses/Galois-Theory"]["news"] is False)
    check("and one that is says when, so the card can say how long ago",
          by_id["projects/TRD-EHR"]["news"] is True
          and by_id["projects/TRD-EHR"]["news_at"] > 0)

    # THE CACHE MUST NOT OUTLIVE THE FACT. The atlas is cached for half a minute
    # and this is the one field in it that a person acts on immediately: a badge
    # still up after the answer was read is a badge nobody trusts again.
    news.mark_seen(trd)
    news.forget()
    payload = machines.atlas_payload(here)          # a cache HIT, deliberately
    by_id = {c["id"]: c for c in payload["workspaces"]}
    check("and reading it takes the badge off even on a cached front door",
          by_id["projects/TRD-EHR"]["news"] is False)

    # ------------------------------------------------------------------
    # and the same two facts over HTTP, which is how the pages get them
    # ------------------------------------------------------------------
    # The board pushes `news` on its stream, and the page says `/seen` when
    # somebody is actually looking -- which is the one fact a server cannot
    # derive, because a board is a long-lived process that goes on running in an
    # empty room.
    # One answer outstanding, put there deliberately: everything above has been
    # read, marked seen, or corrupted and re-started, so the state going in is
    # "nothing waiting" and this is the only thing that can be found.
    card(psych, "0016", "grid", "The grid finished; two cells failed.",
         time.time())
    worker = tikz.TikzWorker(here)
    worker.start()
    board = hub.Hub(here, worker)
    news.forget()
    payload = board.build()
    check("the payload a board pushes carries no news: its key is null (D27)",
          "news" in payload and payload["news"] is None)

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), handler.Handler)
    httpd.daemon_threads = True
    httpd.repo = here
    httpd.hub = board
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    BASE = "http://127.0.0.1:%d" % port

    def ask(path, method="GET"):
        req = urllib.request.Request(BASE + path, method=method,
                                     data=b"" if method == "POST" else None)
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode("utf-8"))

    def ask_json(path):
        """`(status, payload)` for a GET, refusals included.

        A 404 is the answer to "is that a workspace this machine has" and to
        "is that a turn id", and a route that is not there answers the same
        way -- so all three have to be readable as a status rather than
        raising past the check that is about them.
        """
        try:
            with urllib.request.urlopen(BASE + path, timeout=20) as r:
                return r.status, json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            try:
                return exc.code, json.loads(exc.read().decode("utf-8"))
            except ValueError:
                return exc.code, {}

    check("and a surface that polls rather than subscribes can ask for it",
          [n["id"] for n in ask("/news")["news"]] == ["projects/PSYCH-ASR"])

    # And the page saying it is being read is what takes a notification down --
    # for THIS workspace, which is the only root this server may write into.
    before = news.seen_at(galois)
    time.sleep(1.1)
    check("a board can say that somebody is looking at it", ask("/seen", "POST")["ok"])
    check("and the marker moves", news.seen_at(galois) > (before or 0))
    check("and it marked its OWN workspace and nothing else",
          [n["id"] for n in ask("/news")["news"]] == ["projects/PSYCH-ASR"])

    # The payload is rebuilt at once rather than up to `news.TTL` later: a
    # notification that survives being read is one nobody trusts again.
    news.mark_seen(psych)
    ask("/seen", "POST")
    check("and reading clears the list without waiting on the cache",
          ask("/news")["news"] == [])

    # ------------------------------------------------------------------
    # and the OTHER half of the same sentence: putting one to work over there
    # ------------------------------------------------------------------
    # "I want to be able to go into a different section of a project, or a
    # different fucking project completely, and put other agents to work on
    # other things while the first one is working." The notification above is
    # how it comes back. This is how it goes out, from the board you happen to
    # have open, without leaving it.
    from tutorboard.server import spawn as _spawn            # noqa: E402
    from tutorboard.course import repo as _repo              # noqa: E402

    ran = []
    real_tutor_cli = _spawn.tutor_cli
    _spawn.tutor_cli = lambda args, timeout=30: (
        ran.append(list(args)) or (0, "colibri starting in PSYCH-ASR"))

    def there():
        """Where a dispatch to PSYCH-ASR lands: the newest open session bound
        to it, which `runner_route` picks (or opens). Before the first, its
        own `live/`, which holds no turn."""
        from tutorboard import sessions as _sessions         # noqa: E402
        from tutorboard.server import registry as _registry  # noqa: E402
        sid = _registry.newest_open(base, "projects/PSYCH-ASR")
        return _sessions.repo(sid, base) if sid else _repo.Repo(psych)

    def send(body):
        req = urllib.request.Request(
            BASE + "/elsewhere", method="POST",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.status, json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read().decode("utf-8"))

    try:
        status, body = send({"repo": "PSYCH-ASR", "agent": "colibri",
                             "task": "reproduce the corrected transcript"})
        check("a board can put an assistant to work in another workspace",
              status == 200 and body.get("ok") is True)
        check("and nothing is started or stopped there: the turn is queued on "
              "the runner, in the session the task went to",
              not ran and body.get("session"))
        over = there()
        said = turns.load_turns(over)
        check("the task is a turn of THEIRS over there, because they asked for it",
              said and said[-1]["text"] == "reproduce the corrected transcript"
              and said[-1]["from"] == "student")
        with open(over.messages_path, encoding="utf-8") as fh:
            lines = [json.loads(l) for l in fh if l.strip()]
        check("and it is in that session's inbox, which is what the turn is "
              "handed",
              lines and lines[-1]["text"] == "reproduce the corrected transcript"
              and lines[-1]["read"] is False)
        # AND THE LINE IS THEIR WORDS AND NOTHING ELSE. What kind of turn this
        # is comes out of `board brief`, in one place: a rule stated in the line
        # as well would reach a do-stance workspace twice.
        check("and it carries no standing rules of its own, because the "
              "briefing is where a turn is told what kind it is",
              "THIS IS A DOING TURN" not in lines[-1]["text"])
        check("and nothing landed in the workspace the board is serving",
              not os.path.exists(here.messages_path)
              or not open(here.messages_path, encoding="utf-8").read().strip())

        status, body = send({"repo": "PSYCH-ASR", "task": ""})
        check("a start with nothing to do is refused rather than woken",
              status == 400 and "what to do" in (body.get("error") or ""))
        status, body = send({"repo": "../../etc", "task": "anything"})
        check("and a workspace this machine has not got is refused by name, "
              "never built into a path",
              status == 404)

        agent_json = os.path.join(psych, "live", "agent.json")

        def attach(**over):
            """A headless daemon listening over there, as the board sees one."""
            rec = {"agent": "claude", "state": "listening", "pid": os.getpid(),
                   "turns": 1, "mode": "headless",
                   "host": machine.node_name(), "last_seen": time.time()}
            rec.update(over)
            write(agent_json, json.dumps(rec))

        def quiet():
            """The ordinary idle workspace: nothing unread, nothing running,
            and no browser on it.

            All three are what the guards below are ABOUT, so every case that is
            not about one of them starts from a workspace that has none.
            """
            open(_repo.Repo(psych).messages_path, "w").close()
            mdir = os.path.join(psych, "live", "missions")
            for f in (os.listdir(mdir) if os.path.isdir(mdir) else []):
                os.remove(os.path.join(mdir, f))
            missions.forget()
            news.mark_seen(psych, time.time() - 65)
            news.forget()

        # ------------------------------------------------------------------
        # AND THE PANEL CAN SEE ALL OF THAT COMING
        # ------------------------------------------------------------------
        # The atlas row carries the holder, so a panel can say who is there.
        #
        # ASKED FOR RATHER THAN SENT. It is an `agent.json` per workspace off a
        # shared filer and the front door polls this same route every 20
        # seconds without drawing it.
        attach()
        rows = {c["repo"]: c for c in ask("/atlas.json?holders=1")["workspaces"]}
        check("the atlas row says which assistant is listening in that "
              "workspace, so a dispatch panel knows before the tap what the "
              "tap will stop",
              rows["PSYCH-ASR"].get("holder") == "claude")
        check("and a workspace with nothing attached says so, rather than "
              "leaving the field off and reading as unknown",
              rows["TRD-EHR"].get("holder") == ""
              and rows["Galois-Theory"].get("holder") == "")
        plain = {c["repo"]: c for c in ask("/atlas.json")["workspaces"]}
        check("while the front door, which polls this every twenty seconds and "
              "draws none of it, is not charged a read per workspace for it",
              all("holder" not in c for c in plain.values()))
        os.remove(agent_json)
        rows = {c["repo"]: c for c in ask("/atlas.json?holders=1")["workspaces"]}
        check("and the answer is read rather than remembered, because the "
              "atlas payload is cached for half a minute and a name somebody "
              "taps on may not be half a minute old",
              rows["PSYCH-ASR"].get("holder") == "")

        _spawn.tutor_cli = lambda args, timeout=30: (
            ran.append(list(args)) or (0, "colibri starting in PSYCH-ASR"))

        # ------------------------------------------------------------------
        # A MISSION IS A THING, AND CLOSING THE IPAD DOES NOT END IT
        # ------------------------------------------------------------------
        # "when I put colibri or anything on a mission, just because I close the
        # iPad doesn't mean that should end. Next time I open the iPad and access
        # the board, that mission should still be going or notify me somewhere if
        # it's done."
        #
        # The daemon already survived the lid -- it is `setsid` with stdin on
        # DEVNULL. What is checked here is the RECORD, which is the half that did
        # not exist: on disk in the workspace the mission is about, readable from
        # a board serving a different one, and carrying an ending that outlives
        # the evidence it was derived from.
        _spawn.tutor_cli = lambda args, timeout=30: (0, "colibri starting")
        status, body = send({"repo": "PSYCH-ASR", "agent": "colibri",
                             "task": "grade the four typists against the gold",
                             "ship": True})
        one = body.get("mission")
        check("a dispatched mission is a file in the workspace it is ABOUT, "
              "under live/, which no repository tracks",
              status == 200 and one
              and os.path.isfile(os.path.join(psych, "live", "missions",
                                              one + ".json")))
        rec = [m for m in missions.stored(psych) if m["id"] == one]
        rec = rec[0] if rec else {}
        check("and it carries what was asked, which assistant, and when",
              rec.get("task") == "grade the four typists against the gold"
              and rec.get("agent") == "colibri" and rec.get("at") > 0)
        check("and whether it is to ship itself, which is the switch HANDOFF "
              "item 2 honours and this one only has to keep",
              rec.get("ship") is True)
        check("and which workspace it was sent from, which is the one field "
              "nobody can reconstruct a day later",
              rec.get("from") == "courses/Galois-Theory")
        # AND THE BRIEF THE DAEMON READS IS A DOING TURN'S. The task goes into
        # the inbox as a plain sentence of the student's, so `board brief` is
        # the whole of what a mission reads -- and PSYCH-ASR teaches. This is
        # the question that briefing asks; `test/teaching.py` has the text it
        # gets back for it.
        check("and a live mission is what `board brief` asks about, so a "
              "workspace that teaches briefs one as a doing turn",
              missions.running(psych))
        # AND THE RECORD IS ON DISK BEFORE THE WAKING. The inbox line is what
        # `board wait` is watching, so a record written after it is a record a
        # fast daemon reaches `board brief` without -- briefed as a lesson,
        # silently. Read off the source because the window is a race and a
        # passing run proves nothing about the order.
        _route = open(os.path.join(ROOT, "tutorboard", "server", "routes",
                                   "machines.py"), encoding="utf-8").read()
        # The record is made in the `before` hook `runner_route` runs ahead
        # of the turn and the inbox line.
        _dispatched = _route.find('made["rec"] = missions.dispatch(')
        _woken = _route.find("before=mission", _dispatched)
        check("and the mission record is written before the inbox line that "
              "wakes the daemon that reads it",
              0 < _dispatched < _woken)

        # READABLE FROM A BOARD SERVING SOMEWHERE ELSE, which is the whole point:
        # this server is Galois-Theory and the mission is in PSYCH-ASR.
        missions.forget()
        got = ask("/missions")["missions"]
        mine = [m for m in got if m["id"] == one]
        check("and a board serving a DIFFERENT workspace reads it off disk",
              len(mine) == 1 and mine[0]["ws"] == "projects/PSYCH-ASR")
        check("and says it is running, which is the state to leave alone",
              mine and mine[0]["state"] == "running")
        check("and that it is not in the workspace being read, so the row can "
              "carry a way back to it",
              mine and mine[0]["here"] is False)

        # ------------------------------------------------------------------
        # WHAT IT HAS BEEN DOING, WHICH IS NOT THE SAME QUESTION AS WHETHER
        # ------------------------------------------------------------------
        # "Whenever an agent is dispatched in some way, make it so that if I
        # click on that box that says 'A Mission is still going' I can see what
        # has been going on and been accomplished thus far."
        #
        # The three states above are what somebody DOES about a mission. After
        # the first hour they are not what somebody wants to know: one mission
        # ran five hours, took a pick-up, and had put nothing anywhere at all,
        # because a doing turn's report lands at the END and this model prefills
        # for hours. So there are two halves, and the first one has to be true
        # of a mission that has said nothing.
        first = progress.read(psych, one)
        check("a mission has a trail from second zero, and the machinery writes "
              "the first line rather than waiting for a model that prefills for "
              "hours",
              len(first) == 1 and first[0]["who"] == "board"
              and "dispatched" in first[0]["said"]
              and "colibri" in first[0]["said"])
        said = progress.of(psych, mine[0], working=False)
        check("and the facts a person wants are derived from the record, so a "
              "mission that has reported nothing still says how long it has "
              "been going, which turn it is on and how much budget is left",
              said["elapsed"] >= 0 and said["turns"] == 1
              and said["carries"] == 0 and said["stalls"] == 0
              and said["budget"] > 0 and said["agent"] == "colibri")
        check("and which node it is on, which is the thing a colibri mission "
              "lives and dies by",
              said["host"] == machine.node_name())
        check("and whether a client is actually running right now, which is the "
              "one fact no card can answer",
              said["working"] is False
              and progress.of(psych, mine[0], working=True)["working"] is True)

        # AND THE ASSISTANT'S OWN HALF: a line per finished thing, not one
        # report at the end.
        progress.add(psych, one, "read the error log: 74 rows, 6 disagree")
        progress.forget()
        trail = progress.read(psych, one)
        check("and a turn can report a finished thing as it goes, which lands "
              "at once instead of at the end of a nine-hour turn",
              len(trail) == 2 and trail[-1]["who"] == "agent"
              and "74 rows" in trail[-1]["said"])
        check("the newest of those rides on the ROW, because 'still going' is a "
              "state and 'read the error log' is progress",
              [m for m in missions.listing(galois) if m["id"] == one][0]["step"]
              == "read the error log: 74 rows, 6 disagree")
        check("and so does the count, so the row can offer the rest",
              [m for m in missions.listing(galois) if m["id"] == one][0]["steps"]
              == 2)
        # AND THE FRONT DOOR'S CARD CARRIES IT TOO, because that is the surface
        # that is open when somebody comes back to the app.
        missions.forget()
        machines._ATLAS["value"] = None
        _cards = {c["id"]: c for c in machines.atlas_payload(here)["workspaces"]}
        check("and the card on the front door says the same, because that is "
              "what is open when somebody comes back to the app",
              (_cards["projects/PSYCH-ASR"]["mission"] or {}).get("step")
              == "read the error log: 74 rows, 6 disagree")

        # AND IT IS ONE TAP, WHICH IS WHAT THE ASK SAYS. `/missions` is the list
        # and is pushed four times a second; this is the panel, and it is asked
        # for once, by a thumb.
        _st, panel = ask_json("/mission?ws=projects%%2FPSYCH-ASR&id=%s" % one)
        check("a running mission can be asked what it has done, over HTTP, from "
              "a board serving a different workspace",
              panel.get("ok") is True and panel["id"] == one
              and panel["ws"] == "projects/PSYCH-ASR")
        check("and the answer carries the trail and the derived facts together, "
              "because either half alone is half a panel",
              len(panel.get("steps") or []) == 2
              and panel.get("turns") == 1
              and str(panel.get("task") or "").startswith(
                  "grade the four typists"))
        # NEITHER NAME REACHES THE FILESYSTEM. A workspace is matched against
        # what the server already discovered and a mission id is matched against
        # `missions.ID_RE` -- the same rule `/elsewhere` follows.
        check("a workspace this machine has not got is refused by name rather "
              "than built into a path",
              ask_json("/mission?ws=../../etc&id=%s" % one)[0] == 404)
        check("and so is a mission id that is not a turn id",
              ask_json("/mission?ws=projects%2FPSYCH-ASR&id=../../passwd")[0]
              == 404)
        check("and a turn-shaped id no mission has is refused rather than "
              "answered with an empty panel",
              ask_json("/mission?ws=projects%2FPSYCH-ASR&id=t9999")[0] == 404)

        # AND A NAME UNDER A FENCE IS COUNTED, NEVER LISTED. `projects/PSYCH-ASR`
        # keeps 308 MB of identifiable therapy audio under `phi/`, and its own
        # `.gitignore` says why this matters here: *filenames themselves contain
        # participant IDs*. So a list of what a mission touched is content even
        # though nothing was opened to build it.
        subprocess.run(["git", "init", "-q", base], check=False,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                        "commit", "-q", "--allow-empty", "-m", "start"],
                       cwd=base, check=False,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        write(os.path.join(psych, "phi", "community-1", "turns.csv"), "id,at\n")
        write(os.path.join(psych, "psych_asr", "repair.py"), "x = 1\n")
        fenced.forget()
        changed = progress.changes_since(psych, 0)
        check("the fence holds for the progress panel too: a path under it is "
              "counted and never named",
              changed["withheld"] == 1
              and not any(fenced.refused(f) for f in changed["files"]))
        check("and the work that is not fenced is named, so the panel is not "
              "silent about a mission that changed something",
              any("psych_asr" in f for f in changed["files"]))
        # AND A FILE THAT WAS ALREADY DIRTY IS NOT THE MISSION'S. `git status`
        # has no clock, so without the mtime the panel credits a mission with
        # whatever somebody was editing in their own editor -- the same lie
        # `brief.beside_sense` exists to stop, pointing the other way.
        old = os.path.join(psych, "psych_asr", "repair.py")
        os.utime(old, (time.time() - 86400, time.time() - 86400))
        check("and a file somebody was already editing when the mission "
              "started is not credited to it, because `git status` has no clock",
              not any("psych_asr" in f for f in
                      progress.changes_since(psych, time.time() - 60)["files"])
              and any("psych_asr" in f
                      for f in progress.changes_since(psych, 0)["files"]))
        check("and the trail itself is under live/, which every workspace's "
              ".gitignore excludes wholesale -- test/tracked.py holds the "
              "other end of that",
              os.path.relpath(progress.steps_path(psych, one),
                              psych).startswith("live" + os.sep))
        progress.forget()

        # A MISSION WHOSE DAEMON HAS GONE IS FAILED, NOT RUNNING. A failed turn
        # is reported in the busy strip of the board nobody is looking at.
        gone = json.dumps({"agent": "colibri", "state": "listening",
                           "pid": 999999999, "turns": 1,
                           "last_seen": time.time(),
                           "host": machine.node_name(), "mode": "headless"})
        write(os.path.join(psych, "live", "agent.json"), gone)
        old_rec = dict(rec)
        old_rec["at"] = time.time() - missions.START_GRACE - 60
        missions.write(psych, old_rec)
        missions.forget()
        judged = [m for m in missions.listing(galois) if m["id"] == one]
        check("a mission whose daemon has gone reads as failed rather than as "
              "running, which is the difference between sending it again and "
              "waiting all evening",
              judged and judged[0]["state"] == "failed")
        check("and says so in words, rather than leaving a state word to guess "
              "from",
              judged and "attached" in judged[0]["reason"])
        check("and a start that was asked for seconds ago is NOT that, because "
              "`agent start` forks and the daemon is not up yet",
              missions.judge(psych, dict(old_rec, at=time.time()),
                             said={})["state"] == "running")

        # AND AN ENDING OUTLIVES THE EVIDENCE IT CAME FROM. A daemon that is
        # started again, or any later turn at all, would otherwise turn last
        # night's failure into "running" on every board that looked.
        alive = json.dumps({"agent": "colibri", "state": "listening",
                            "pid": os.getpid(), "turns": 2,
                            "last_seen": time.time(),
                            "host": machine.node_name(), "mode": "headless"})
        write(os.path.join(psych, "live", "agent.json"), alive)
        missions.forget()
        judged = [m for m in missions.listing(galois) if m["id"] == one]
        check("a mission that ended stays ended once something has read it, "
              "because the evidence expires and the ending must not",
              judged and judged[0]["state"] == "failed")

        # A MISSION THAT LANDED A CARD IS DONE, and it is the card that says so
        # -- the same rule `news` is built on, because a card IS the answer.
        status, body = send({"repo": "PSYCH-ASR", "agent": "colibri",
                             "task": "and now write the comparison up"})
        two = body.get("mission")
        card(psych, "0017", "typists", "Two of the four agree.",
             time.time() + 1, title="the comparison")
        missions.forget()
        judged = [m for m in missions.listing(galois) if m["id"] == two]
        check("a mission that has landed a card reads as done",
              judged and judged[0]["state"] == "done")
        check("and says which card, so the row can point AT the answer",
              judged and judged[0]["card"] == "0017")

        # AND A CARD WRITTEN MID-TURN IS NOT AN ENDING. A doing turn writes one
        # sentence before the work and the report over the top of it, so the
        # first card lands seconds in. Read as an ending it reports `done` over
        # an assistant that has hours left, and `looked` then takes the row off
        # the list while the work is still running.
        status, body = send({"repo": "PSYCH-ASR", "agent": "colibri",
                             "task": "repair the diarization"})
        three = body.get("mission")
        busy = json.dumps({"agent": "colibri", "state": "working",
                           "pid": os.getpid(), "turns": 1,
                           "last_seen": time.time(),
                           "host": machine.node_name(), "mode": "headless"})
        write(os.path.join(psych, "live", "agent.json"), busy)
        card(psych, "0018", "starting", "Reading the error log.",
             time.time() + 1, title="what I am about to do")
        missions.forget()
        judged = [m for m in missions.listing(galois) if m["id"] == three]
        check("a card written while the assistant is mid-turn leaves the "
              "mission running, because the first card of a doing turn is "
              "written before the work",
              judged and judged[0]["state"] == "running")
        # A LOOK IS WHAT FILES A FINISHED MISSION AWAY, so the look is the
        # assertion: going to the workspace mid-turn must not take the row.
        missions.looked(psych)
        missions.forget()
        check("and a look at that workspace does not file it away, because "
              "filing is for work that is over",
              three in [m["id"] for m in missions.listing(galois)])

        # AND IT ENDS WHEN THE TURN DOES, off the same card.
        write(os.path.join(psych, "live", "agent.json"), alive)
        missions.forget()
        judged = [m for m in missions.listing(galois) if m["id"] == three]
        check("and the same card ends it once the turn is over",
              judged and judged[0]["state"] == "done"
              and judged[0]["card"] == "0018")

        # AND A RECORD LEFT SAYING `working` BY A DEAD DAEMON IS NOT A TURN.
        # Nobody is taking it, so the card is the ending it looks like.
        status, body = send({"repo": "PSYCH-ASR", "agent": "colibri",
                             "task": "and the arms after it"})
        four = body.get("mission")
        dead = json.dumps({"agent": "colibri", "state": "working",
                           "pid": 999999, "turns": 1,
                           "last_seen": time.time(),
                           "host": machine.node_name(), "mode": "headless"})
        write(os.path.join(psych, "live", "agent.json"), dead)
        card(psych, "0019", "gone", "Half an answer.", time.time() + 2)
        missions.forget()
        judged = [m for m in missions.listing(galois) if m["id"] == four]
        check("a card counts as the ending where the record says working and "
              "nothing is attached, because that turn is nobody's",
              judged and judged[0]["state"] == "done")
        write(os.path.join(psych, "live", "agent.json"), alive)
        missions.forget()

        # AND COMES OFF THE LIST WHEN IT IS LOOKED AT -- which means going there,
        # and the board serving that workspace is what stamps it.
        check("a finished mission comes off the list when somebody looks at "
              "the workspace holding it",
              missions.looked(psych) >= 1
              and [m["id"] for m in missions.listing(galois)] == [])
        check("and it is still recorded as having FINISHED, because a look is "
              "not what ended it",
              [m["ended"] for m in missions.stored(psych) if m["id"] == two]
              == ["done"])
        check("and a RUNNING one does not, because it is still running and "
              "that is the fact being reported",
              missions.dispatch(trd, task="hold the grid", turn="t0101")
              and [m["id"] for m in missions.listing(galois)] == ["t0101"])

        # `/seen` IS THE FAR END OF THE ROW, and it stamps THIS workspace only.
        missions.dispatch(galois, task="finish the proof", turn="t0202")
        card(galois, "0002", "done", "The proof closes.", time.time() + 2)
        missions.forget()
        ask("/seen", "POST")
        check("the page saying somebody is looking at this board is what takes "
              "its own finished missions off, and nowhere else's",
              [m["id"] for m in missions.listing(galois)] == ["t0101"])

        # THE ONE ASSISTANT WITH A CEILING. A colibri TURN runs inside the
        # serve job's allocation, so it cannot outlive that job's walltime --
        # and an allocation ending leaves no process anywhere to record it.
        # The MISSION outlives it: the chain brings another generation up and
        # the pick-up crosses to it, so a passed ceiling with carry budget left
        # is a hop rather than an ending.
        ceiling = missions.dispatch(trd, task="decode the long one",
                                    turn="t0303", agent="colibri",
                                    ceiling=time.time() - 5)
        missions.forget()
        judged = [m for m in missions.listing(galois) if m["id"] == "t0303"]
        check("a mission past its generation's walltime with pick-ups left is "
              "still running, because the chain brings another generation up",
              judged and judged[0]["state"] == "running")
        missions.write(trd, dict(missions.stored(trd)[0],
                                 carries=missions.CARRY_HOPS))
        missions.forget()
        judged = [m for m in missions.listing(galois) if m["id"] == "t0303"]
        check("and with the pick-ups spent it has failed, and says so rather "
              "than saying nothing",
              judged and judged[0]["state"] == "failed"
              and "picked up six times" in judged[0]["reason"])
        missions.write(trd, dict(missions.stored(trd)[0], agent="claude",
                                 ended="", ended_at=0.0, reason=""))
        missions.forget()
        judged = [m for m in missions.listing(galois) if m["id"] == "t0303"]
        check("an assistant with no chain under it is failed by the ceiling "
              "itself, because nothing is going to bring its allocation back",
              judged and judged[0]["state"] == "failed"
              and "allocation" in judged[0]["reason"])
        check("and the ceiling is read off Slurm's own time-left rather than "
              "guessed from a default",
              colibri.time_left("2:03:04") == 7384
              and colibri.time_left("UNLIMITED") is None)

        # ------------------------------------------------------------------
        # A MISSION CAN BE TOLD TO SHIP ITSELF, AND SOMEBODY ELSE PUSHES IT
        # ------------------------------------------------------------------
        # "when I put anything on a mission, I should have the option to tell it
        #  to ship its changes once it is done - I don't know if colibri is
        #  capable of doing that, but the tutor certainly should be once colibri
        #  is done."
        #
        # The switch is set at dispatch and carried in the record. What is
        # guarded here is what happens when the mission ends: a turn is woken in
        # a workspace nobody is looking at, and it is NOT the assistant that did
        # the work -- the local model is the only one that may read the fenced
        # directory, so its own diff is the one thing it must not push.
        import tutorboard.assistants as _assist                # noqa: E402

        # Recording again: the launcher is what a ship drives, and which
        # commands it drives is half of what is being checked here.
        _spawn.tutor_cli = lambda args, timeout=30: (
            ran.append(list(args)) or (0, "started"))

        REGISTRY = {"default": "claude", "agents": [
            {"name": "claude", "headless": True, "missing": None,
             "private": None, "exclusive": None},
            {"name": "colibri", "headless": True, "missing": None,
             "private": "it is the only assistant allowed to read `phi`",
             "exclusive": "one KV slot"},
            {"name": "aider", "headless": False, "missing": "aider",
             "private": None, "exclusive": None},
        ]}
        _assist._CACHE["was"] = REGISTRY
        _assist._CACHE["at"] = time.time()

        check("the assistant that pushes is one that could not have read the "
              "fenced content it is checking the diff for",
              _spawn.shipper() == "claude")
        from tutorboard import jobs as _jobs_mod
        _had = _jobs_mod.has_slurm
        _jobs_mod.has_slurm = lambda: True
        try:
            check("where Slurm is, nothing ships: every shipper is hosted",
                  _spawn.shipper() is None)
        finally:
            _jobs_mod.has_slurm = _had

        # A mission that FAILED is not shipped. Its changes may well be in the
        # tree and pushing them is the opposite of what "failed" means to the
        # person who set it going.
        _spawn._SHIPS["at"] = 0.0
        missions.forget()
        check("a mission that failed is never shipped, whatever its switch said",
              [m for _, m in missions.due() if m["id"] == one] == [])

        # And one that finished. The daemon over there is the LOCAL model,
        # listening, which is what a colibri mission leaves behind.
        write(os.path.join(trd, "live", "agent.json"), json.dumps(
            {"agent": "colibri", "state": "listening", "pid": os.getpid(),
             "turns": 1, "last_seen": time.time(),
             "host": machine.node_name(), "mode": "headless"}))
        missions.dispatch(trd, task="repair the diarization on the pilot",
                          turn="t0404", agent="colibri", ship=True)
        card(trd, "0009", "repaired", "Two arms agree now.", time.time() + 3)
        missions.forget()
        check("a finished mission that was told to ship itself is owed one",
              [m["id"] for _, m in missions.due()] == ["t0404"])

        ran[:] = []
        _spawn._SHIPS["at"] = 0.0
        handed = _spawn.ship_missions()
        check("and it is handed over exactly once, to a hosted tutor rather "
              "than to the assistant that did the work",
              [h["mission"] for h in handed] == ["t0404"]
              and handed[0]["agent"] == "claude")
        check("the local model listening there is stopped first, because a "
              "start will not swap one assistant for another",
              ["agent", "stop", "TRD-EHR", "--wait"] in ran)
        check("and the hosted one is started in its place, named for that "
              "daemon only, and without moving the one address to a workspace "
              "the sweep happened to finish on",
              ["agent", "start", "TRD-EHR", "--respawn",
               "--agent", "claude"] in ran)
        with open(_repo.Repo(trd).messages_path, encoding="utf-8") as fh:
            lines = [json.loads(l) for l in fh if l.strip()]
        check("the turn it is woken with is a [ship] line in that workspace's "
              "inbox, which is what `board wait` watches",
              lines and lines[-1]["signal"] == "ship"
              and lines[-1]["text"].startswith("[ship]"))
        check("and it names what the mission was asked to do, and who did it",
              "repair the diarization on the pilot" in lines[-1]["text"]
              and "colibri" in lines[-1]["text"])
        check("and nothing of it is written into the lesson's transcript, "
              "because a ship is not part of a lesson",
              not any(t.get("signal") == "ship"
                      for t in turns.load_turns(_repo.Repo(trd))))

        # ONCE, ACROSS EVERY BOARD ON THE MACHINE. Every board reads every
        # workspace's missions, so without a claim two of them wake two turns to
        # push the same diff.
        ran[:] = []
        _spawn._SHIPS["at"] = 0.0
        missions.forget()
        check("a second board sweeping the same finished mission hands over "
              "nothing, because the ship was already claimed",
              _spawn.ship_missions() == [] and ran == [])
        check("and the record says so, so a person can read that it went",
              [m.get("shipped", 0) > 0 for m in missions.stored(trd)
               if m["id"] == "t0404"] == [True])

        # A DAEMON MID-TURN IS DOING SOMETHING SOMEBODY ASKED FOR. The ship
        # waits for the next pass rather than killing it.
        write(os.path.join(trd, "live", "agent.json"), json.dumps(
            {"agent": "colibri", "state": "working", "pid": os.getpid(),
             "turns": 2, "turn_started": time.time(),
             "last_seen": time.time(),
             "host": machine.node_name(), "mode": "headless"}))
        missions.dispatch(trd, task="and the second pass", turn="t0505",
                          agent="colibri", ship=True)
        card(trd, "0010", "second", "The second pass is in.", time.time() + 4)
        ran[:] = []
        _spawn._SHIPS["at"] = 0.0
        missions.forget()
        check("a mission whose workspace is mid-turn is left for the next pass "
              "rather than having its daemon killed under it",
              _spawn.ship_missions() == []
              and not any(a[:2] == ["agent", "stop"] for a in ran))

        # AND AN ORDINARY TUTOR ALREADY THERE IS THE RIGHT KIND OF ASSISTANT.
        # The rule is not "the default one": it is that whoever pushes could not
        # have read the fenced content, and evicting a daemon to prove that is
        # a restart for nothing.
        write(os.path.join(trd, "live", "agent.json"), json.dumps(
            {"agent": "codex", "state": "listening", "pid": os.getpid(),
             "turns": 1, "last_seen": time.time(),
             "host": machine.node_name(), "mode": "headless"}))
        ran[:] = []
        _spawn._SHIPS["at"] = 0.0
        missions.forget()
        handed = _spawn.ship_missions()
        check("a tutor already listening there that may not read the fence "
              "ships it where it stands",
              [h["agent"] for h in handed] == ["codex"]
              and not any(a[:2] == ["agent", "stop"] for a in ran))

        # ------------------------------------------------------------------
        # A DISPATCH RECORDS WHETHER IT BROUGHT THE ASSISTANT
        # ------------------------------------------------------------------
        # An assistant started for a mission and one a person chose are the
        # same name in the same `agent.json` afterwards, so `brought` is
        # written when one is started.

        from tutorboard.runner import daemon

        # Off the missions every check above left on disk, so what is guarded
        # here is one workspace at a time.
        for _r in (psych, trd, galois):
            _d = os.path.join(_r, "live", "missions")
            for _n in (os.listdir(_d) if os.path.isdir(_d) else []):
                os.remove(os.path.join(_d, _n))

        held = os.path.join(base, "projects", "HELD")
        write(os.path.join(held, "tutorboard.json"),
              json.dumps({"name": "HELD"}))
        os.makedirs(os.path.join(held, "live", "cards"), exist_ok=True)
        machines._ATLAS["value"] = None

        def attach(who, **kw):
            rec = {"agent": who, "state": "listening", "pid": os.getpid(),
                   "turns": 1, "last_seen": time.time(),
                   "host": machine.node_name(), "mode": "headless"}
            rec.update(kw)
            write(os.path.join(held, "live", "agent.json"), json.dumps(rec))
            return rec

        def detach():
            """What `agent_stop` leaves behind, written by the line that writes
            it: the daemon's own last act, merged over the record it was
            listening under. Not a record shaped like one by hand -- the whole
            claim being made is about what `bin/tutor` actually leaves."""
            return daemon.agent_state(os.path.join(held, "live"),
                                      state="stopped", stopped_at=time.time())

        attached = [""]
        left = {}

        def launcher(configured="claude"):
            def run(args, timeout=30):
                ran.append(list(args))
                if args[:2] == ["agent", "which"]:
                    return 0, configured + "\n"
                if args[:2] == ["agent", "stop"]:
                    left["rec"] = detach()
                    attached[0] = ""
                    return 0, "wrapping up"
                if args[:2] == ["agent", "start"]:
                    who = (args[args.index("--agent") + 1]
                           if "--agent" in args else configured)
                    attached[0] = who
                    attach(who, state="waking", waking_at=time.time())
                    return 0, "%s starting" % who
                return 0, ""
            return run

        # A DISPATCH STARTS NO ASSISTANT, so it brings none for the mission's
        # end to release, named or not.
        _spawn.tutor_cli = launcher()
        attached[0] = ""
        try:
            os.remove(os.path.join(held, "live", "agent.json"))
        except OSError:
            pass
        ran[:] = []
        status, body = send({"repo": "HELD", "agent": "colibri",
                             "task": "repair the diarization"})
        first = body.get("mission")
        check("a dispatch records that it brought no assistant, because the "
              "runner takes the turn and nothing was started",
              status == 200
              and [m["brought"] for m in missions.stored(held)
                   if m["id"] == first] == [""]
              and not any(a[:2] == ["agent", "start"] for a in ran))

        _assist.forget()
    finally:
        _spawn.tutor_cli = real_tutor_cli
    httpd.shutdown()

finally:
    if was_courses is None:
        os.environ.pop("TUTORBOARD_COURSES", None)
    else:
        os.environ["TUTORBOARD_COURSES"] = was_courses
    machines._ATLAS["value"] = None
    news.forget()


# ---------------------------------------------------------------------------
# what a turn was woken FOR
# ---------------------------------------------------------------------------
# The board's ordinary rule is that a card landing is the answer, so the strip
# stops talking. A re-planning turn breaks that rule by design: it is told to
# write one sentence FIRST so the board is not blank, and then to spend several
# minutes rewriting the plan. Without a word for what the turn is, the indicator
# goes away ten seconds into a job that takes minutes.
src = open(os.path.join(ROOT, "tutorboard", "runner", "turn.py"),
           encoding="utf-8").read()
ns = {"re": re}
exec(compile(re.search(r"_SIGNAL_TAG = .*?\n    return \"\"\n", src, re.S).group(0),
             "<tutor>", "exec"), ns)
turn_signal = ns["turn_signal"]

check("the signal of an inbox message is what the turn is woken for",
      turn_signal("[2026-09-16 10:04:11] [direction] THEY HAVE JUST CHANGED "
                  "THE DIRECTION OF THIS WORK") == "direction")
check("an ordinary message carries none",
      turn_signal("[2026-09-16 10:04:11] here is my working") == "")
check("and a student who writes a bracket is not sending a signal",
      turn_signal("[2026-09-16 10:04:11] I tried it and got [help] from the "
                  "docs") == "")
check("nothing at all is not a crash", turn_signal("") == ""
      and turn_signal(None) == "")

# And the record it is written into is cleared by the reader rather than by the
# five paths out of a turn, because a stale one is a strip saying "re-planning"
# over a tutor that has been listening for an hour.
tmp2 = tempfile.mkdtemp(prefix="tutor-signal-")
r2 = course_repo.Repo(tmp2)
write(os.path.join(tmp2, "live", "agent.json"), json.dumps(
    {"agent": "claude", "state": "working", "pid": os.getpid(),
     "turns": 3, "turn_started": time.time(), "turn_signal": "direction",
     "last_seen": time.time(), "host": "", "mode": "headless"}))
got = state.load_agent(r2) or {}
check("a working turn keeps the word for what it is doing",
      got.get("turn_signal") == "direction")
write(os.path.join(tmp2, "live", "agent.json"), json.dumps(
    {"agent": "claude", "state": "listening", "pid": os.getpid(),
     "turns": 3, "turn_signal": "direction",
     "last_seen": time.time(), "host": "", "mode": "headless"}))
got = state.load_agent(r2) or {}
check("and a tutor that is merely listening has no turn, so it has no word",
      not got.get("turn_signal"))

# ---------------------------------------------------------------------------
# and what is WAITING says what it is
# ---------------------------------------------------------------------------
# A direction change replaces the tutor it was sent to, so the minutes before
# anything picks it up are expected rather than wrong -- and a board that cannot
# tell those apart reports the expected one in the words of a stall: "no tutor is
# reading the board", which is true, alarming and beside the point.
write(os.path.join(tmp2, "live", "inbox", "messages.jsonl"),
      json.dumps({"id": "t0004", "t": time.time() - 30, "read": False,
                  "signal": "direction", "text": "Drop the bake-off."}) + "\n")
waiting = notes.waiting(r2)
check("the inbox says what kind of thing is waiting, not merely that something is",
      waiting and waiting["signal"] == "direction" and waiting["count"] == 1)

print()
if fails:
    print("%d FAILURES" % len(fails))
    sys.exit(1)
print("work that came back while you were elsewhere is found by looking, and a "
      "turn says what it was woken for")
