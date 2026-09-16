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
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tutorboard import atlas, machines, news
from tutorboard.course import repo as course_repo
from tutorboard.lesson import notes, state
from tutorboard.server import handler, hub, tikz

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
    write(os.path.join(base, "atlas.json"), json.dumps(
        {"families": [{"id": "research", "name": "Research"},
                      {"id": "courses", "name": "Courses"}]}))
    psych = os.path.join(base, "research", "PSYCH-ASR")
    trd = os.path.join(base, "research", "TRD-EHR")
    galois = os.path.join(base, "courses", "Galois-Theory")
    for r in (psych, trd, galois):
        write(os.path.join(r, "tutorboard.json"), json.dumps({"name": os.path.basename(r)}))
        os.makedirs(os.path.join(r, "live", "cards"), exist_ok=True)
    atlas.forget()
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
          [n["id"] for n in got] == ["research/PSYCH-ASR"])
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
          [n["id"] for n in got] == ["research/TRD-EHR", "research/PSYCH-ASR"])

    # ------------------------------------------------------------------
    # and reading it is what clears it
    # ------------------------------------------------------------------
    news.mark_seen(psych)
    check("looking at a workspace clears its notification and nothing else's",
          [n["id"] for n in news.elsewhere(galois)] == ["research/TRD-EHR"])
    card(psych, "0015", "tie", "And here is the tie-break.", time.time())
    check("and the next card in it is news again",
          len(news.elsewhere(galois)) == 2)

    # ------------------------------------------------------------------
    # a lesson from last month is not tonight's news
    # ------------------------------------------------------------------
    old = os.path.join(base, "courses", "Probability")
    write(os.path.join(old, "tutorboard.json"), "{}\n")
    os.makedirs(os.path.join(old, "live", "cards"), exist_ok=True)
    atlas.forget()
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
          by_id["research/TRD-EHR"]["news"] is True
          and by_id["research/TRD-EHR"]["news_at"] > 0)

    # THE CACHE MUST NOT OUTLIVE THE FACT. The atlas is cached for half a minute
    # and this is the one field in it that a person acts on immediately: a badge
    # still up after the answer was read is a badge nobody trusts again.
    news.mark_seen(trd)
    news.forget()
    payload = machines.atlas_payload(here)          # a cache HIT, deliberately
    by_id = {c["id"]: c for c in payload["workspaces"]}
    check("and reading it takes the badge off even on a cached front door",
          by_id["research/TRD-EHR"]["news"] is False)

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
    check("the payload a board pushes carries what landed elsewhere",
          [n["id"] for n in payload["news"]] == ["research/PSYCH-ASR"])

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

    check("and a surface that polls rather than subscribes can ask for it",
          [n["id"] for n in ask("/news")["news"]] == ["research/PSYCH-ASR"])

    # And the page saying it is being read is what takes a notification down --
    # for THIS workspace, which is the only root this server may write into.
    before = news.seen_at(galois)
    time.sleep(1.1)
    check("a board can say that somebody is looking at it", ask("/seen", "POST")["ok"])
    check("and the marker moves", news.seen_at(galois) > (before or 0))
    check("and it marked its OWN workspace and nothing else",
          [n["id"] for n in ask("/news")["news"]] == ["research/PSYCH-ASR"])

    # The payload is rebuilt at once rather than up to `news.TTL` later: a
    # notification that survives being read is one nobody trusts again.
    news.mark_seen(psych)
    ask("/seen", "POST")
    check("and reading clears the list without waiting on the cache",
          ask("/news")["news"] == [])
    httpd.shutdown()

finally:
    if was_courses is None:
        os.environ.pop("TUTORBOARD_COURSES", None)
    else:
        os.environ["TUTORBOARD_COURSES"] = was_courses
    atlas.forget()
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
src = open(os.path.join(ROOT, "bin", "tutor"), encoding="utf-8").read()
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
