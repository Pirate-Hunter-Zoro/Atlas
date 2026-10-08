#!/usr/bin/env python3
"""The two-session harness: one server, two sessions bound to different
subjects, and no route reads or writes across them.

Every route each module answers is discovered from its source. A route in
COVERED is driven under both `/s/A/` and `/s/B/`: its writes must land only
in that session's directory or its subject's, and its reply must carry
nothing of the other session. Every other route is listed as pending; T17
moves them into COVERED module by module. The unprefixed table is driven
too: what it lists answers, and anything else unprefixed is 404.
"""

import hashlib
import http.client
import json
import os
import re
import shutil
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

tmp = tempfile.mkdtemp(prefix="tutor-routing-")
os.environ["BOARD_STATE_DIR"] = os.path.join(tmp, ".state")
os.environ["TUTORBOARD_TRASH"] = os.path.join(tmp, ".trash")

import threading                                              # noqa: E402

from tutorboard import sessions                               # noqa: E402
from tutorboard.course import repo as course_repo             # noqa: E402
from tutorboard.server import app, handler, registry, spawn   # noqa: E402

fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


# A closed stream is noticed at the next ping; make that quick.
handler.PING_SECONDS = 0.5
# Nothing here may start a tutor.
spawn.wake_tutor = lambda repo: False

# ---------------------------------------------------------------------------
# the fixture: an Atlas tree with two subjects and a session bound to each
# ---------------------------------------------------------------------------
atlas = os.path.join(tmp, "Atlas")
SUBJECT = {"A": "courses/Alpha", "B": "projects/Beta"}
for rel in SUBJECT.values():
    os.makedirs(os.path.join(atlas, rel))
    with open(os.path.join(atlas, rel, "tutorboard.json"), "w", encoding="utf-8") as fh:
        json.dump({"name": os.path.basename(rel), "phi": False}, fh)

SID = {}
DIR = {}
MARK = {"A": "alpha-marker-7f3c", "B": "beta-marker-91d2"}
for n, who in enumerate(("A", "B")):
    rec = sessions.new("session " + who, base=atlas, now=1.7e9 + n)
    SID[who] = rec["id"]
    DIR[who] = sessions.path(rec["id"], atlas)
    course_repo.Repo(atlas, session=DIR[who], create=False).set_state(subject=SUBJECT[who])
    with open(os.path.join(DIR[who], "cards", "0001-start.md"), "w", encoding="utf-8") as fh:
        fh.write("---\ntitle: start\n---\n\nThe card of %s.\n" % MARK[who])
    for sub, name in (("answers", "own.png"), ("uploads", "own.png"),
                      ("slate", "page-01.png"), ("tikzcache", "abc123.svg")):
        os.makedirs(os.path.join(DIR[who], sub), exist_ok=True)
        with open(os.path.join(DIR[who], sub, name), "w", encoding="utf-8") as fh:
            fh.write(MARK[who])
OTHER = {"A": "B", "B": "A"}

httpd = app.make_server(atlas, 0)
threading.Thread(target=httpd.serve_forever, daemon=True).start()
PORT = httpd.server_port


def ask(method, path, body=None, headers=None):
    conn = http.client.HTTPConnection("127.0.0.1", PORT, timeout=30)
    data = body
    if isinstance(body, (dict, list)):
        data = json.dumps(body).encode("utf-8")
        headers = dict(headers or {}, **{"Content-Type": "application/json"})
    conn.request(method, path, body=data, headers=headers or {})
    r = conn.getresponse()
    out = r.status, r.read()
    conn.close()
    return out


def snapshot():
    """{path relative to the fixture: digest} for every file in it."""
    out = {}
    for top, dirs, files in os.walk(atlas):
        for f in files:
            p = os.path.join(top, f)
            try:
                with open(p, "rb") as fh:
                    out[os.path.relpath(p, atlas)] = hashlib.sha1(fh.read()).hexdigest()
            except OSError:
                pass
    return out


def changed(before, after):
    keys = set(before) | set(after)
    return sorted(k for k in keys if before.get(k) != after.get(k))


def scope(who):
    """What a request in session `who` may write: its session and its subject."""
    return (os.path.relpath(DIR[who], atlas) + os.sep, SUBJECT[who] + os.sep)


def inside(rel, prefixes):
    return any(rel.startswith(p) for p in prefixes)


# ---------------------------------------------------------------------------
# every route, from the modules' own source
# ---------------------------------------------------------------------------
LITERAL = re.compile(r'path(?: ==|\.startswith\() ?"(/[^"]*)"')
TUPLE = re.compile(r'path in \(([^)]*)\)')


def routes_of(src, func):
    """The paths `def func(h, repo, path)` compares against."""
    at = src.find("\ndef %s(h, repo, path)" % func)
    if at < 0:
        return set()
    end = src.find("\ndef ", at + 1)
    body = src[at:end if end > 0 else len(src)]
    found = set(LITERAL.findall(body))
    for group in TUPLE.findall(body):
        found.update(re.findall(r'"(/[^"]*)"', group))
    return found


ROUTES = os.path.join(ROOT, "tutorboard", "server", "routes")
EVERY = set()
for name in sorted(os.listdir(ROUTES)):
    if not name.endswith(".py") or name == "__init__.py":
        continue
    src = open(os.path.join(ROUTES, name), encoding="utf-8").read()
    mod = name[:-3]
    EVERY.update(("GET", p, mod) for p in routes_of(src, "get"))
    EVERY.update(("POST", p, mod) for p in routes_of(src, "post"))
for p in ("/board", "/slate", "/library", "/meeting", "/slate/page-"):
    EVERY.add(("GET", p, "handler"))

# The routes this harness drives under both sessions.
COVERED = {
    ("GET", "/board", "handler"), ("GET", "/slate", "handler"),
    ("GET", "/slate/page-", "handler"),
    ("GET", "/events", "lesson"), ("GET", "/board.json", "lesson"),
    ("GET", "/slate/state", "writing"),
    ("GET", "/answers/", "pages"), ("GET", "/uploads/", "pages"),
    ("GET", "/figure/", "pages"),
    ("GET", "/health", "machines"),
    ("POST", "/say", "lesson"), ("POST", "/text/save", "lesson"),
    ("POST", "/slate/save", "writing"), ("POST", "/annotate/save", "writing"),
    ("POST", "/upload", "writing"),
}
# Served only unprefixed, and driven in part 3.
UNPREFIXED_ONLY = {("GET", "/static/", "pages"), ("GET", "/sw.js", "pages"),
                   ("GET", "/manifest.webmanifest", "pages")}

check("every covered route is one the modules really answer",
      COVERED <= EVERY)


# ---------------------------------------------------------------------------
# 1. each covered route, in each session
# ---------------------------------------------------------------------------
def multipart(name, data):
    b = "----routing"
    body = ("--%s\r\nContent-Disposition: form-data; name=\"file\"; filename=\"%s\"\r\n"
            "Content-Type: text/plain\r\n\r\n" % (b, name)).encode("utf-8")
    body += data + ("\r\n--%s--\r\n" % b).encode("utf-8")
    return body, {"Content-Type": "multipart/form-data; boundary=%s" % b}


def first_event(who):
    conn = http.client.HTTPConnection("127.0.0.1", PORT, timeout=30)
    conn.request("GET", "/s/%s/events" % SID[who])
    r = conn.getresponse()
    got = ""
    deadline = time.time() + 20
    while time.time() < deadline:
        line = r.fp.readline().decode("utf-8")
        if line.startswith("data: "):
            got = line[len("data: "):]
            break
    conn.close()
    return got


def drive(who):
    """[(route, status, reply bytes, files changed)] for one session."""
    pre = "/s/%s" % SID[who]
    out = []

    def one(route, method, path, body=None, headers=None):
        before = snapshot()
        status, reply = ask(method, pre + path, body, headers)
        out.append((route, status, reply, changed(before, snapshot())))

    one(("GET", "/board", "handler"), "GET", "/board")
    one(("GET", "/slate", "handler"), "GET", "/slate")
    one(("GET", "/slate/page-", "handler"), "GET", "/slate/page-01.png")
    one(("GET", "/board.json", "lesson"), "GET", "/board.json")
    one(("GET", "/answers/", "pages"), "GET", "/answers/own.png")
    one(("GET", "/uploads/", "pages"), "GET", "/uploads/own.png")
    one(("GET", "/figure/", "pages"), "GET", "/figure/abc123.svg")
    one(("GET", "/health", "machines"), "GET", "/health")
    one(("POST", "/say", "lesson"), "POST", "/say", {"text": "said " + MARK[who]})
    one(("POST", "/text/save", "lesson"), "POST", "/text/save",
        {"question": "1", "text": "typed " + MARK[who]})
    one(("POST", "/slate/save", "writing"), "POST", "/slate/save",
        {"page": 2, "w": 10, "h": 10, "strokes": [{"pts": [[1, 1]], "m": MARK[who]}]})
    one(("GET", "/slate/state", "writing"), "GET", "/slate/state")
    one(("POST", "/annotate/save", "writing"), "POST", "/annotate/save",
        {"card": "0001", "strokes": [{"pts": [[2, 2]], "m": MARK[who]}]})
    one(("POST", "/annotate/save", "writing"), "POST", "/annotate/save",
        {"card": "doc/notes/p1", "strokes": [{"pts": [[3, 3]], "m": MARK[who]}]})
    body, headers = multipart("hand-in.txt", MARK[who].encode("utf-8"))
    one(("POST", "/upload", "writing"), "POST", "/upload", body, headers)
    before = snapshot()
    event = first_event(who)
    out.append((("GET", "/events", "lesson"), 200 if event else 0,
                event.encode("utf-8"), changed(before, snapshot())))
    return out


for who in ("A", "B"):
    other = OTHER[who]
    results = drive(who)
    for route, status, reply, wrote in results:
        label = "%s %s in session %s" % (route[0], route[1], who)
        stray = [w for w in wrote if not inside(w, scope(who))]
        check(label + " answers", status == 200)
        check(label + " writes only its own session and subject"
              + (" (stray: %s)" % stray if stray else ""), not stray)
        check(label + " reads nothing of the other session",
              MARK[other].encode("utf-8") not in reply)
    check("session %s's board.json carries its own card" % who,
          any(r[0][1] == "/board.json" and MARK[who].encode("utf-8") in r[2]
              for r in results))
    check("session %s's stream carries its own card" % who,
          any(r[0][1] == "/events" and MARK[who].encode("utf-8") in r[2]
              for r in results))

# ---------------------------------------------------------------------------
# 2. where the writes landed, and the ink routing
# ---------------------------------------------------------------------------
for who in ("A", "B"):
    sdir = DIR[who]
    with open(os.path.join(sdir, "turns.jsonl"), encoding="utf-8") as fh:
        turns = fh.read()
    check("a /say in %s is %s's turn" % (who, who), MARK[who] in turns
          and MARK[OTHER[who]] not in turns)
    check("card ink in %s stays in the session" % who,
          os.path.isfile(os.path.join(sdir, "annotations", "0001.json")))
    ink = os.path.join(atlas, SUBJECT[who], ".ink")
    held = sorted(os.listdir(ink)) if os.path.isdir(ink) else []
    check("document ink in %s goes to %s/.ink/" % (who, SUBJECT[who]),
          len(held) == 1 and held[0].startswith("doc-notes-p1-")
          and not any(n.startswith("doc-") for n in os.listdir(
              os.path.join(sdir, "annotations"))))
    check("an upload in %s lands in its uploads/" % who,
          any(n.endswith("hand-in.txt") for n in os.listdir(os.path.join(sdir, "uploads"))))

# A second session on Alpha sees Alpha's document ink, and none of its cards'.
rec = sessions.new("second on Alpha", base=atlas, now=1.7e9 + 5)
course_repo.Repo(atlas, session=sessions.path(rec["id"], atlas),
                 create=False).set_state(subject=SUBJECT["A"])
status, reply = ask("GET", "/s/%s/board.json" % rec["id"])
notes = json.loads(reply.decode("utf-8")).get("notes") or {}
check("a second session on one subject reads that subject's document ink",
      status == 200 and "doc/notes/p1" in notes and "0001" not in notes)

# An unbound session keeps document ink in its own annotations.
loose = sessions.new("unbound", base=atlas, now=1.7e9 + 6)
before = snapshot()
status, _ = ask("POST", "/s/%s/annotate/save" % loose["id"],
                {"card": "doc/notes/p1", "strokes": [{"pts": [[4, 4]]}]})
wrote = changed(before, snapshot())
check("an unbound session's document ink stays in the session",
      status == 200 and wrote and all(
          w.startswith(os.path.join("sessions", loose["id"], "annotations")) for w in wrote))

# ---------------------------------------------------------------------------
# 3. the unprefixed table, and nothing else unprefixed
# ---------------------------------------------------------------------------
for path in ("/", "/sw.js", "/manifest.webmanifest", "/static/board.js", "/health",
             "/sessions.json", "/subjects.json", "/notices.json", "/library",
             "/library.json?subject=courses/Alpha",
             "/library/stamp?subject=projects/Beta"):
    before = snapshot()
    status, reply = ask("GET", path)
    stray = [w for w in changed(before, snapshot())
             if not w.startswith("sessions" + os.sep)]
    check("unprefixed GET %s answers and writes no subject" % path,
          status == 200 and not stray)

status, reply = ask("GET", "/sessions.json")
listed = [r["id"] for r in json.loads(reply.decode("utf-8"))["sessions"]]
check("/sessions.json lists both sessions", SID["A"] in listed and SID["B"] in listed)
status, reply = ask("GET", "/subjects.json")
check("/subjects.json lists both subjects",
      sorted(s["id"] for s in json.loads(reply.decode("utf-8"))["subjects"])
      == sorted(SUBJECT.values()))
check("a library route without ?subject= is refused",
      ask("GET", "/library.json")[0] == 400)
check("a library route naming no subject is 404",
      ask("GET", "/library.json?subject=courses/Nope")[0] == 404)

before = snapshot()
status, reply = ask("POST", "/sessions/new", {"title": "fresh"})
made = json.loads(reply.decode("utf-8"))
wrote = changed(before, snapshot())
check("POST /sessions/new opens an unbound session in teach, and touches no other",
      status == 200 and made.get("url") == "/s/%s/board" % made.get("id")
      and made["session"]["subject"] is None and made["session"]["mode"] == "teach"
      and wrote and all(w.startswith(os.path.join("sessions", made["id"])) for w in wrote))

for method, path in (("GET", "/board.json"), ("GET", "/events"), ("POST", "/say"),
                     ("GET", "/slate/state"), ("POST", "/annotate/save"),
                     ("GET", "/answers/own.png"), ("GET", "/archive")):
    before = snapshot()
    status, _ = ask(method, path, {"text": "x"} if method == "POST" else None)
    check("unprefixed %s %s is 404 and writes nothing" % (method, path),
          status == 404 and not changed(before, snapshot()))
check("a session that does not exist is 404",
      ask("GET", "/s/20990101-000000/board.json")[0] == 404
      and ask("GET", "/s/../board.json")[0] == 404)

# ---------------------------------------------------------------------------
# 4. the registry: a bind moves the root, idle sessions are dropped
# ---------------------------------------------------------------------------
reg = httpd.registry
entry = reg.get(loose["id"])
hub_was = entry.hub
check("an unbound session roots at the Atlas root", entry.repo.root == atlas)
course_repo.Repo(atlas, session=sessions.path(loose["id"], atlas),
                 create=False).set_state(subject=SUBJECT["B"])
entry = reg.get(loose["id"])
check("binding it moves its root to the subject and keeps its hub",
      entry.repo.root == os.path.join(atlas, SUBJECT["B"]) and entry.hub is hub_was
      and entry.repo.doc_ink == os.path.join(atlas, SUBJECT["B"], ".ink"))

# A closed stream leaves its hub at the next ping, within 15 s.
deadline = time.time() + 30
while time.time() < deadline and any(e.hub.clients for e in list(reg.entries.values())):
    time.sleep(0.2)
served = reg.loaded()
gone = reg.sweep(now=time.monotonic() + registry.IDLE_SECONDS + 1)
check("after IDLE_SECONDS with no stream, every session is dropped",
      sorted(gone) == served and reg.loaded() == [] and hub_was.stopped.is_set())
status, reply = ask("GET", "/s/%s/board.json" % SID["A"])
check("and the next request builds it again",
      status == 200 and MARK["A"].encode("utf-8") in reply and SID["A"] in reg.loaded())

conn = http.client.HTTPConnection("127.0.0.1", PORT, timeout=30)
conn.request("GET", "/s/%s/events" % SID["B"])
r = conn.getresponse()
r.fp.readline()
deadline = time.time() + 10
while time.time() < deadline and not reg.entries.get(SID["B"]):
    time.sleep(0.05)
while time.time() < deadline and not reg.entries[SID["B"]].hub.clients:
    time.sleep(0.05)
kept = reg.sweep(now=time.monotonic() + registry.IDLE_SECONDS + 1)
check("a session with a stream open is kept", SID["B"] not in kept
      and SID["B"] in reg.loaded())
conn.close()

sessions.delete(SID["A"], base=atlas)
check("a deleted session is 404 and leaves the registry",
      ask("GET", "/s/%s/board.json" % SID["A"])[0] == 404
      and SID["A"] not in reg.loaded())

# ---------------------------------------------------------------------------
# 5. what is still pending, for T17
# ---------------------------------------------------------------------------
pending = sorted(EVERY - COVERED - UNPREFIXED_ONLY, key=lambda r: (r[2], r[1], r[0]))
print()
print("pending for T17: %d routes not yet driven under two sessions" % len(pending))
for method, path, mod in pending:
    print("  pending  %-8s %-5s %s" % (mod, method, path))

httpd.shutdown()
shutil.rmtree(tmp, ignore_errors=True)
print()
if fails:
    print("%d FAILURES" % len(fails))
    sys.exit(1)
print("two sessions, one server, and neither reads or writes the other")
