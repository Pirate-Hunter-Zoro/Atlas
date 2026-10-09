#!/usr/bin/env python3
"""The two-session harness: one server, two sessions bound to different
subjects, and no route reads or writes across them.

Every route each module answers is discovered from its source, and every one
is in DRIVE with its class -- the class the module's own table gives it:

    session   driven under `/s/A/` and `/s/B/`: its writes land only in that
              session or its subject, its reply and the commands it runs carry
              nothing of the other, and unprefixed it is 404
    subject   the same under both prefixes, and unprefixed with `?subject=`
              it writes only that subject, or the session `runner_route`
              chose, and nothing of the other session
    atlas     unprefixed only: it writes into neither session (unless it is an
              ask, checked by name below), and under `/s/A/` it is 404
    both      a session route that the handler also answers unprefixed with an
              answer of its own (`/health`, the library page, `/paper/`)

A route the modules answer that DRIVE does not list fails the harness.

The unprefixed table is driven too, and the asks that reach another subject's
tutor are followed into the session they land in.
"""

import hashlib
import http.client
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

tmp = tempfile.mkdtemp(prefix="tutor-routing-")
atlas = os.path.join(os.path.realpath(tmp), "Atlas")
os.environ["BOARD_STATE_DIR"] = os.path.join(tmp, ".state")
os.environ["TUTORBOARD_TRASH"] = os.path.join(tmp, ".trash")
os.environ["XDG_CONFIG_HOME"] = os.path.join(tmp, ".config")
os.environ["TUTORBOARD_COURSES"] = atlas
os.environ["TUTORBOARD_PAGES"] = os.path.join(tmp, ".pages")

import threading                                              # noqa: E402

from tutorboard import sessions                               # noqa: E402
from tutorboard.course import repo as course_repo             # noqa: E402
from tutorboard.server import app, handler, registry, spawn   # noqa: E402
from tutorboard.runner import service as runner_service  # noqa: E402

fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


# A closed stream is noticed at the next ping; make that quick.
handler.PING_SECONDS = 0.5

# ---------------------------------------------------------------------------
# nothing here starts a process: every command a route would run is recorded
# ---------------------------------------------------------------------------
CALLS = []


def _wake(repo):
    CALLS.append({"fn": "wake", "session": repo.live, "root": repo.root})
    return False


def _board(where, args, timeout=90, given=None, session=None):
    CALLS.append({"fn": "board", "cwd": where, "args": list(args), "session": session})
    return 0, "ok"


def _tutor(args, timeout=30):
    CALLS.append({"fn": "tutor", "args": list(args)})
    return 0, "ok"


from tutorboard.course import document as course_document   # noqa: E402
from tutorboard.course import screenshot as course_shot       # noqa: E402
from tutorboard.lesson import git as lesson_git               # noqa: E402

runner_service.wake = _wake
spawn.board_cli = _board
spawn.tutor_cli = _tutor
spawn.wake_colibri = lambda timeout=1800: (CALLS.append({"fn": "colibri"}) or (False, "fake"))


def recorder(name, answer):
    """A stand-in for a builder or a push: records what it was handed."""
    def run(*args, **kw):
        CALLS.append({"fn": name, "args": [getattr(a, "live", a) for a in args
                                           if isinstance(a, str) or hasattr(a, "live")],
                      "root": [getattr(a, "root", None) for a in args]})
        return dict(answer)
    return run


lesson_git.run_push = recorder("push", {"ok": True, "detail": "pushed"})
lesson_git.run_hw_build = recorder("hw", {"ok": True, "detail": "built"})
course_document.build = recorder("export", {"ok": True, "detail": "exported"})
course_shot.build = recorder("shot", {"ok": True, "detail": "shot"})

# ---------------------------------------------------------------------------
# the fixture: an Atlas tree with three subjects and a session on two of them
# ---------------------------------------------------------------------------
SUBJECT = {"A": "courses/Alpha", "B": "projects/Beta"}
LONE = "projects/Gamma"          # a subject with no session open on it
MARK = {"A": "alpha-marker-7f3c", "B": "beta-marker-91d2"}
DOC = {"A": "alpha-notes", "B": "beta-notes"}


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


# The meeting deck's subject, as the repository tracks it.
write(os.path.join(atlas, "projects", "Meetings", "tutorboard.json"),
      json.dumps({"name": "Meetings", "phi": True}))
for who, rel in list(SUBJECT.items()) + [("G", LONE)]:
    write(os.path.join(atlas, rel, "tutorboard.json"),
          json.dumps({"name": os.path.basename(rel), "phi": False}))
    if who in DOC:
        d = os.path.join(atlas, rel, "docs", DOC[who])
        write(os.path.join(d, "doc.json"), json.dumps(
            {"title": "notes " + MARK[who], "source": DOC[who] + ".md",
             "sessions": [], "asked_at": "2026-10-01 10:00:00"}))
        write(os.path.join(d, DOC[who] + ".md"), "# Notes\n\n%s\n" % MARK[who])
        # One figure and one table at the same path in each, so one id names
        # both and only the session decides which is served.
        write(os.path.join(atlas, rel, "figures", "plot.png"),
              "\x89PNG" + MARK[who] * 100)
        write(os.path.join(atlas, rel, "figures", "t.csv"), "a,b\n1,%s\n" % MARK[who])
        # One tracked source file at the same path in each, for /source/.
        write(os.path.join(atlas, rel, "src", "tool.py"),
              "# %s\n" % MARK[who] + "def tool(x):\n    return x\n" * 12)

GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false"]
subprocess.run(["git", "init", "-q", atlas], check=True)
write(os.path.join(atlas, ".gitignore"), "/sessions/\n**/.ink/\n/meetings/\n")
subprocess.run(GIT + ["-C", atlas, "add", "-A"], check=True)
subprocess.run(GIT + ["-C", atlas, "commit", "-q", "-m", "projects/Beta: the fixture"],
               check=True)

# The figure's and the table's ids, the same in both subjects.
from tutorboard.course import library                         # noqa: E402
_found = library.result_index(os.path.join(atlas, SUBJECT["A"]))
FIG = [k for k, v in _found.items() if v["rel"] == "figures/plot.png"][0]
TABLE = [k for k, v in _found.items() if v["rel"] == "figures/t.csv"][0]

SID = {}
DIR = {}
for n, who in enumerate(("A", "B")):
    rec = sessions.new("session " + who, base=atlas, now=1.7e9 + n)
    SID[who] = rec["id"]
    DIR[who] = sessions.path(rec["id"], atlas)
    course_repo.Repo(atlas, session=DIR[who], create=False).set_state(subject=SUBJECT[who])
    write(os.path.join(DIR[who], "cards", "0001-start.md"),
          "---\ntitle: start\n---\n\nThe card of %s.\n" % MARK[who])
    for sub, name in (("answers", "own.png"), ("uploads", "own.png"),
                      ("slate", "page-01.png")):
        write(os.path.join(DIR[who], sub, name), MARK[who])
# Compiled TikZ is one cache beside the sessions, keyed by source and macros.
write(os.path.join(atlas, "sessions", ".tikz", "abc123.svg"), "<svg>shared figure</svg>")
# Rendered PDF pages are one cache outside the tree (`paths.PAGES`).
write(os.path.join(os.environ["TUTORBOARD_PAGES"], "abcdef12", "abcdef12-1.png"),
      "a shared page")
OTHER = {"A": "B", "B": "A"}

httpd = app.make_server(atlas, 0)
threading.Thread(target=httpd.serve_forever, daemon=True).start()
PORT = httpd.server_port


def ask(method, path, body=None, headers=None):
    conn = http.client.HTTPConnection("127.0.0.1", PORT, timeout=60)
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
        if ".git" in dirs:
            dirs.remove(".git")
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


def foreign(who):
    """Strings that name the other session or its subject."""
    o = OTHER[who]
    return (SID[o], MARK[o], SUBJECT[o], os.path.basename(SUBJECT[o]))


# The session directory of a sessionless Repo: nothing is ever written under it.
NONE = os.path.join("sessions", registry.NONE) + os.sep


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
for p in ("/board", "/slate", "/library", "/slate/page-"):
    EVERY.add(("GET", p, "handler"))

# Served only unprefixed, by the handler's own table; driven in part 3.
UNPREFIXED_ONLY = {("GET", "/static/", "pages"), ("GET", "/sw.js", "pages"),
                   ("GET", "/manifest.webmanifest", "pages")}
# Driven last, on its own: End ends the session it is asked of, and every ask
# routed to a subject before it needs that session open.
DRIVEN_LAST = {("POST", "/end", "lesson")}


def multipart(name, data):
    b = "----routing"
    body = ("--%s\r\nContent-Disposition: form-data; name=\"file\"; filename=\"%s\"\r\n"
            "Content-Type: text/plain\r\n\r\n" % (b, name)).encode("utf-8")
    body += data + ("\r\n--%s--\r\n" % b).encode("utf-8")
    return body, {"Content-Type": "multipart/form-data; boundary=%s" % b}


def upload(who):
    return multipart("hand-in.txt", MARK[who].encode("utf-8"))


# DRIVE: route -> (class, [(path, body, statuses[, unprefixed[, no subject]])]).
# `{mark}` and `{doc}` are filled in per session, and a body may be a function
# of the session. `statuses` None means anything under 500; a subject route's
# unprefixed ones, with `?subject=` and without, default to the same.
OK = (200,)
REFUSED = (400,)
DRIVE = {
    # handler's own pages
    ("GET", "/board", "handler"): ("session", [("/board", None, OK)]),
    ("GET", "/slate", "handler"): ("session", [("/slate", None, OK)]),
    ("GET", "/slate/page-", "handler"): ("session", [("/slate/page-01.png", None, OK)]),
    ("GET", "/library", "handler"): ("both", [("/library", None, OK)]),
    # lesson
    ("GET", "/board.json", "lesson"): ("session", [("/board.json", None, OK)]),
    ("GET", "/events", "lesson"): ("stream", []),
    ("GET", "/cards", "lesson"): ("session", [("/cards?before=9999", None, OK),
                                             ("/cards?before=x", None, REFUSED)]),
    ("GET", "/subject.json", "lesson"): ("session", [("/subject.json", None, OK)]),
    ("GET", "/archive", "lesson"): ("session", [("/archive", None, OK)]),
    ("GET", "/archive/", "lesson"): ("session", [("/archive/", None, OK),
                                                ("/archive/nope", None, (404,))]),
    ("POST", "/mode", "lesson"): ("session", [("/mode", {"mode": "do"}, OK),
                                             ("/mode", {"mode": "nope"}, (400,))]),
    ("POST", "/bind", "lesson"): ("session", [
        ("/bind", lambda who: {"subject": SUBJECT[who]}, OK),
        ("/bind", {"subject": "../x"}, REFUSED),
        ("/bind", {"subject": "courses/Nowhere"}, REFUSED)]),
    ("POST", "/handover", "lesson"): ("session", [("/handover", {"card": "0001"}, None)]),
    ("POST", "/dismiss-finish", "lesson"): ("session", [("/dismiss-finish", {}, OK)]),
    ("POST", "/session", "lesson"): ("session", [
        ("/session", {"session": "lecture"}, None),
        ("/session", {"session": "nope"}, (400,))]),
    ("POST", "/say", "lesson"): ("session", [("/say", {"text": "said {mark}"}, OK)]),
    ("POST", "/poke", "lesson"): ("session", [("/poke", {}, OK)]),
    ("POST", "/text/save", "lesson"): ("session", [
        ("/text/save", {"question": "1", "text": "typed {mark}"}, OK)]),
    # writing
    ("GET", "/slate/state", "writing"): ("session", [("/slate/state", None, OK)]),
    # saving
    ("POST", "/push", "saving"): ("session", [("/push", {"message": "{mark}"}, OK)]),
    ("POST", "/hw/build", "saving"): ("session", [("/hw/build", {}, OK)]),
    ("POST", "/export/shot", "saving"): ("session", [("/export/shot", {}, OK)]),
    ("POST", "/export", "saving"): ("session", [("/export", {"scope": "lesson"}, OK)]),
    # library
    ("GET", "/library.json", "library"): ("subject", [("/library.json", None, OK)]),
    ("GET", "/library/stamp", "library"): ("subject", [("/library/stamp", None, OK)]),
    ("GET", "/library/results.json", "library"): ("subject", [
        ("/library/results.json", None, OK)]),
    ("GET", "/library/table/", "library"): ("subject", [("/library/table/{table}", None, OK),
                                                        ("/library/table/nope", None, (404,))]),
    ("GET", "/library/view/", "library"): ("subject", [("/library/view/{doc}", None, OK)]),
    ("GET", "/library/note/", "library"): ("subject", [
        ("/library/note/{doc}/nope", None, (404,))]),
    ("GET", "/library/ledger/", "library"): ("subject", [("/library/ledger/{doc}", None, OK)]),
    ("GET", "/library/evidence/", "library"): ("subject", [
        ("/library/evidence/{doc}/a/b", None, (404,))]),
    ("POST", "/library/ledger/preview", "library"): ("subject", [
        ("/library/ledger/preview", {"document": "{doc}", "text": "fix {mark}"}, OK)]),
    ("POST", "/library/ledger/state", "library"): ("subject", [
        ("/library/ledger/state", {"document": "{doc}", "note": "n", "id": "1",
                                   "state": "done"}, None)]),
    ("POST", "/library/feedback", "library"): ("subject", [
        ("/library/feedback", {"document": "{doc}", "text": "fix {mark}"}, OK)]),
    ("POST", "/doc/delete", "library"): ("subject", [
        ("/doc/delete", {"id": "nope"}, (404,))]),
    ("POST", "/artifact", "library"): ("subject", [
        ("/artifact", {"make": "paper", "about": "{mark}"}, OK)]),
    ("GET", "/materials.json", "library"): ("subject", [("/materials.json", None, OK)]),
    ("POST", "/material/delete", "library"): ("subject", [
        ("/material/delete", {"name": "nope.pdf"}, (404,)),
        ("/material/delete", {"name": "../TUTOR.md"}, (404,))]),
    ("GET", "/library/marked/", "library"): ("subject", [
        ("/library/marked/nope/x.pdf", None, (404,)),
        ("/library/marked/{doc}/..%2Fnotes.pdf", None, (404,))]),
    ("POST", "/writeup/seen", "library"): ("session", [
        ("/writeup/seen", {"id": "t0001"}, OK)]),
    # machines
    ("GET", "/courses.json", "machines"): ("atlas", [("/courses.json", None, OK)]),
    ("GET", "/atlas.json", "machines"): ("atlas", [("/atlas.json", None, OK)]),
    ("GET", "/news", "machines"): ("atlas", [("/news", None, OK)]),
    ("GET", "/missions", "machines"): ("atlas", [("/missions", None, OK)]),
    ("GET", "/mission", "machines"): ("atlas", [("/mission?ws=nope&id=t1", None, (404,))]),
    ("POST", "/meeting", "machines"): ("atlas", [("/meeting", {"since": "nope"}, (400,))]),
    ("POST", "/default-agent", "machines"): ("atlas", [
        ("/default-agent", {"agent": "nobody-here"}, (400,))]),
    ("POST", "/colibri", "machines"): ("atlas", [("/colibri", {}, OK)]),
    ("POST", "/elsewhere", "machines"): ("atlas", [("/elsewhere", {"task": ""}, (400,))]),
    ("POST", "/switch", "machines"): ("atlas", [("/switch", {"repo": "nope"}, (404,))]),
    ("POST", "/seen", "machines"): ("session", [("/seen", {}, OK)]),
    ("GET", "/health", "machines"): ("both", [("/health", None, OK)]),
    # pages
    ("GET", "/answers/", "pages"): ("session", [("/answers/own.png", None, OK)]),
    ("GET", "/uploads/", "pages"): ("session", [("/uploads/own.png", None, OK)]),
    ("GET", "/figure/", "pages"): ("session", [("/figure/abc123.svg", None, OK)]),
    ("GET", "/result/", "pages"): ("subject", [("/result/{fig}", None, OK),
                                              ("/result/nope", None, (404,))]),
    # The Atlas root has no `src/tool.py` of its own, so with no subject it is 404.
    ("GET", "/source/", "pages"): ("subject?", [("/source/src/tool.py", None, OK, OK, (404,)),
                                               ("/source/nope.py", None, (404,))]),
    # taking
    ("GET", "/download/lesson", "taking"): ("session", [("/download/lesson", None, None)]),
    ("GET", "/download/homework", "taking"): ("session", [
        ("/download/homework", None, None)]),
    ("GET", "/view/lesson", "taking"): ("session", [("/view/lesson", None, OK)]),
    ("GET", "/view/homework", "taking"): ("session", [("/view/homework", None, OK)]),
    ("GET", "/view/doc/", "taking"): ("session", [("/view/doc/{doc}", None, None)]),
    ("GET", "/doc/", "taking"): ("session", [("/doc/{doc}/1.png", None, (404,))]),
    ("GET", "/paper/", "taking"): ("both", [("/paper/abcdef12-1.png", None, OK),
                                           ("/paper/nope.png", None, (404,))]),

    ("POST", "/slate/save", "writing"): ("session", [
        ("/slate/save", {"page": 2, "w": 10, "h": 10,
                         "strokes": [{"pts": [[1, 1]], "m": "{mark}"}]}, OK)]),
    ("POST", "/annotate/save", "writing"): ("subject?", [
        ("/annotate/save", {"card": "0001",
                            "strokes": [{"pts": [[2, 2]], "m": "{mark}"}]}, OK, REFUSED),
        ("/annotate/save", {"card": "doc/notes/p1",
                            "strokes": [{"pts": [[3, 3]], "m": "{mark}"}]}, OK),
        ("/annotate/save", {"card": "doc/notes/p2", "send": True,
                            "strokes": [{"pts": [[3, 3]], "m": "{mark}"}]}, OK, REFUSED)]),
    ("POST", "/annotate/burn", "writing"): ("subject", [
        ("/annotate/burn", {"kind": "library/{doc}", "mode": "same"}, REFUSED),
        ("/annotate/burn", {"kind": "homework", "mode": "none"}, None),
        ("/annotate/burn", {"kind": "lesson", "mode": "copy"}, None)]),
    ("POST", "/upload", "writing"): ("session", [("/upload", upload, OK)]),
    ("POST", "/file", "writing"): ("session", [
        ("/file", {"upload": "nope.pdf"}, REFUSED),
        ("/file", {"upload": "../session.json"}, REFUSED)]),
    # taking
    ("GET", "/marked/", "taking"): ("session", [
        ("/marked/homework/nope-marked.pdf", None, (404,)),
        ("/marked/doc/{doc}/..%2F..%2Fsession.json", None, (404,))]),
}


def fill(value, who):
    """`value` with `{mark}`, `{doc}`, `{fig}` and `{table}` made `who`'s."""
    if callable(value):
        return value(who)
    if isinstance(value, str):
        return (value.replace("{mark}", MARK[who]).replace("{doc}", DOC[who])
                .replace("{fig}", FIG).replace("{table}", TABLE))
    if isinstance(value, list):
        return [fill(v, who) for v in value]
    if isinstance(value, dict):
        return dict((k, fill(v, who)) for k, v in value.items())
    return value


def request(method, path, body):
    headers = None
    if isinstance(body, tuple):
        body, headers = body
    return ask(method, path, body, headers)


def drive_one(method, path, body, who):
    """`(status, reply, files written, commands run)`."""
    before = snapshot()
    n = len(CALLS)
    status, reply = request(method, path, fill(body, who))
    return status, reply, changed(before, snapshot()), CALLS[n:]


def judged(label, who, status, reply, wrote, calls, statuses, allowed):
    """The checks every driven request gets."""
    stray = [w for w in wrote if not inside(w, allowed)]
    check(label + " answers (%d)" % status,
          status < 500 if statuses is None else status in statuses)
    check(label + " writes only its own session and subject"
          + (" (stray: %s)" % stray if stray else ""), not stray)
    bad = [f for f in foreign(who) if f.encode("utf-8") in reply]
    check(label + " reads nothing of the other session" + (" (%s)" % bad if bad else ""),
          not bad)
    said = json.dumps(calls)
    bad = [f for f in foreign(who) if f in said]
    check(label + " runs nothing on the other session" + (" (%s)" % bad if bad else ""),
          not bad)


# Where an unprefixed ask of a subject's tutor may land: the newest open
# session on it, which `runner_route` chooses.
ROUTED = dict((who, (os.path.relpath(DIR[who], atlas) + os.sep,)) for who in ("A", "B"))
SESSIONS = tuple(os.path.relpath(DIR[who], atlas) + os.sep for who in ("A", "B"))


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


# ---------------------------------------------------------------------------
# 1. every route, in its class
# ---------------------------------------------------------------------------
missing = sorted(EVERY - set(DRIVE) - UNPREFIXED_ONLY - DRIVEN_LAST,
                 key=lambda r: (r[2], r[1], r[0]))
check("every route the modules answer is driven in its class"
      + (": not %s" % ["%s %s (%s)" % m for m in missing] if missing else ""), not missing)
gone = sorted(set(DRIVE) - EVERY)
check("every driven route is one the modules really answer"
      + (": not %s" % gone if gone else ""), not gone)

for route in sorted(DRIVE, key=lambda r: (r[2], r[1], r[0])):
    cls, asks = DRIVE[route]
    method = route[0]
    if cls == "stream":
        for who in ("A", "B"):
            before = snapshot()
            event = first_event(who)
            judged("GET /events in session %s" % who, who, 200 if event else 0,
                   event.encode("utf-8"), changed(before, snapshot()), [], OK, scope(who))
            check("session %s's stream carries its own card" % who, MARK[who] in event)
        continue
    for one in asks:
        path, body, statuses = one[:3]
        bare = one[3] if len(one) > 3 else statuses
        nobody = one[4] if len(one) > 4 else bare
        for who in ("A", "B"):
            status, reply, wrote, calls = drive_one(
                method, "/s/%s%s" % (SID[who], fill(path, who)), body, who)
            label = "%s %s in session %s" % (method, fill(path, who), who)
            if cls == "atlas":
                check(label + " is 404: it is served outside a session",
                      status == 404 and not wrote)
                continue
            judged(label, who, status, reply, wrote, calls, statuses, scope(who))
        if cls == "session":
            before = snapshot()
            status, _ = request(method, fill(path, "A"), fill(body, "A"))
            check("unprefixed %s %s is 404 and writes nothing" % (method, fill(path, "A")),
                  status == 404 and not changed(before, snapshot()))
        if cls in ("subject", "subject?"):
            # The subject named, from outside any session: it writes that
            # subject, or the session an ask of its tutor was routed to.
            for who in ("A", "B"):
                there = fill(path, who)
                there += ("&" if "?" in there else "?") + "subject=" + SUBJECT[who]
                status, reply, wrote, calls = drive_one(method, there, body, who)
                judged("unprefixed %s %s" % (method, there), who, status, reply, wrote,
                       calls, bare, (SUBJECT[who] + os.sep,) + ROUTED[who])
        if cls == "subject?":
            # And no subject named: the Atlas root's, which is no session's
            # and no subject's.
            status, reply, wrote, calls = drive_one(method, fill(path, "A"), body, "A")
            stray = [w for w in wrote if w.startswith("sessions" + os.sep)
                     or any(w.startswith(r + os.sep) for r in SUBJECT.values())]
            check("unprefixed %s %s, no subject, answers (%d) and writes no session or "
                  "subject%s" % (method, fill(path, "A"), status,
                                 " (stray: %s)" % stray if stray else ""),
                  (status < 500 if nobody is None else status in nobody) and not stray)
        if cls == "atlas":
            # Over every subject, from no session: it writes into none.
            status, reply, wrote, calls = drive_one(method, fill(path, "A"), body, "A")
            stray = [w for w in wrote if any(w.startswith(r) for r in SESSIONS)]
            check("unprefixed %s %s answers (%d) and writes no session%s"
                  % (method, fill(path, "A"), status, " (stray: %s)" % stray if stray else ""),
                  (status < 500 if statuses is None else status in statuses) and not stray)


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
          any(n.startswith("doc-notes-p1-") for n in held)
          and not any(n.startswith("doc-") for n in os.listdir(
              os.path.join(sdir, "annotations"))))
    check("an upload in %s lands in its uploads/" % who,
          any(n.endswith("hand-in.txt") for n in os.listdir(os.path.join(sdir, "uploads"))))
    board = [c for c in CALLS if c["fn"] == "board" and c["session"] == sdir]
    check("any board command a route in %s runs works on session %s" % (who, who),
          all(c["cwd"] == os.path.join(atlas, SUBJECT[who]) for c in board))

# One id, two subjects: the session, or ?subject=, decides whose file it is.
for who in ("A", "B"):
    _, own = ask("GET", "/s/%s/result/%s" % (SID[who], FIG))
    _, named = ask("GET", "/result/%s?subject=%s" % (FIG, SUBJECT[who]))
    _, table = ask("GET", "/library/table/%s?subject=%s" % (TABLE, SUBJECT[who]))
    check("/result/<id> in %s serves %s's figure, and ?subject= names it too"
          % (who, who), MARK[who].encode("utf-8") in own
          and MARK[who].encode("utf-8") in named and MARK[who].encode("utf-8") in table)

# The meeting deck is read in the Meetings library: its own page and routes
# are not served.
gone = [p for p in ("/meeting", "/meeting/", "/meeting/view", "/meeting/deck.json",
                    "/meeting/pdf") if ask("GET", p)[0] != 404]
check("the meeting page and its GET routes are gone (404): %s" % gone, not gone)

# Document ink saved outside a session: the named subject's .ink/, or the
# Atlas root's with none named.
before = snapshot()
ask("POST", "/annotate/save?subject=" + SUBJECT["B"],
    {"card": "doc/beta-notes/p3", "strokes": [{"pts": [[5, 5]]}]})
ask("POST", "/annotate/save", {"card": "doc/meeting/p1", "strokes": [{"pts": [[6, 6]]}]})
wrote = changed(before, snapshot())
check("unprefixed document ink lands in the named subject's .ink/, or the Atlas root's",
      len(wrote) == 2 and wrote[0].startswith(os.path.join(".ink", "doc-meeting-p1-"))
      and wrote[1].startswith(os.path.join(SUBJECT["B"], ".ink", "doc-beta-notes-p3-")))

for who in ("A", "B"):
    done = [c for c in CALLS if c["fn"] in ("push", "hw", "export")
            and (DIR[who] in c["args"] or os.path.join(atlas, SUBJECT[who]) in c["args"])]
    check("a push, a build and an export in %s each ran on %s's session or subject"
          % (who, who), sorted(set(c["fn"] for c in done)) == ["export", "hw", "push"])

# A second session on Alpha sees Alpha's document ink, and none of its cards'.
rec = sessions.new("second on Alpha", base=atlas, now=1.7e9 + 5)
SECOND = sessions.path(rec["id"], atlas)
course_repo.Repo(atlas, session=SECOND, create=False).set_state(subject=SUBJECT["A"])
status, reply = ask("GET", "/s/%s/board.json" % rec["id"])
notes = json.loads(reply.decode("utf-8")).get("notes") or {}
check("a second session on one subject carries none of the first's card ink",
      status == 200 and "0001" not in notes and "doc/notes/p1" not in notes)
from tutorboard.lesson import notes as lesson_notes           # noqa: E402
check("and reads that subject's document ink, which comes with the pages",
      "doc/notes/p1" in lesson_notes.doc_ink(sessions.repo(rec["id"], atlas),
                                             "notes")[0])

# ---------------------------------------------------------------------------
# 2b. an ask of a subject's tutor lands in that subject's newest open session
# ---------------------------------------------------------------------------
def inbox(where):
    try:
        with open(os.path.join(where, "inbox", "messages.jsonl"), encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return ""


def landed(method, path, body):
    """`(status, reply, {session dir: inbox lines it gained})`."""
    every = [sessions.path(r["id"], atlas) for r in sessions.all(atlas)]
    before = dict((d, inbox(d)) for d in every)
    status, reply = ask(method, path, body)
    grew = {}
    for r in sessions.all(atlas):
        d = sessions.path(r["id"], atlas)
        new = inbox(d)[len(before.get(d, "")):]
        if new:
            grew[d] = new
    return status, reply, grew


def only(grew, where, word):
    return list(grew) == [where] and word in grew[where]


status, _, grew = landed("POST", "/library/feedback?subject=" + SUBJECT["A"],
                         {"document": DOC["A"], "text": "a library note"})
check("library feedback from the library page lands in the newest open session on "
      "its subject, and nowhere else", status == 200 and only(grew, SECOND, "[revise]"))
status, _, grew = landed("POST", "/s/%s/library/feedback" % SID["B"],
                         {"document": DOC["B"], "text": "a note from B's board"})
check("library feedback from a session's own board lands in that session",
      status == 200 and only(grew, DIR["B"], "[revise]"))
had = set(r["id"] for r in sessions.all(atlas))
status, reply, grew = landed("POST", "/meeting", {"since": "3650d", "items": [SUBJECT["B"]]})
made = [r for r in sessions.all(atlas) if r["id"] not in had]
check("a meeting ask lands in a session bound to projects/Meetings, and nowhere else "
      "(%d %s)" % (status, reply[:200]),
      status == 200 and len(made) == 1 and made[0]["subject"] == "projects/Meetings"
      and only(grew, sessions.path(made[0]["id"], atlas), "[writeup]"))
status, reply, grew = landed("POST", "/elsewhere", {"task": "a mission for Beta",
                                                    "repo": SUBJECT["B"]})
check("a mission sent elsewhere lands in that subject's session, as its turn",
      status == 200 and only(grew, DIR["B"], "a mission for Beta")
      and "a mission for Beta" in open(os.path.join(DIR["B"], "turns.jsonl")).read())
status, _, grew = landed("POST", "/artifact?subject=" + SUBJECT["B"],
                         {"make": "deck", "about": "a deck from home"})
check("a deck asked for from a subject's row lands in its subject's session",
      status == 200 and only(grew, DIR["B"], "[writeup]"))
had = set(r["id"] for r in sessions.all(atlas))
status, _, grew = landed("POST", "/artifact?subject=" + LONE,
                         {"make": "paper", "about": "nobody is here"})
made = [r for r in sessions.all(atlas) if r["id"] not in had]
check("an ask of a subject with no open session opens one bound to it, titled for it",
      status == 200 and len(made) == 1 and made[0]["subject"] == LONE
      and (made[0]["title"] or "").startswith("Gamma: ")
      and list(grew) == [sessions.path(made[0]["id"], atlas)])

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
             "/library/stamp?subject=projects/Beta", "/paper/abcdef12-1.png"):
    named = path.split("subject=", 1)[1] + os.sep if "subject=" in path else None
    before = snapshot()
    status, reply = ask("GET", path)
    stray = [w for w in changed(before, snapshot())
             if not (named and w.startswith(named))]
    check("unprefixed GET %s answers and writes no other subject and no session%s"
          % (path, " (stray: %s)" % stray if stray else ""), status == 200 and not stray)

status, reply = ask("GET", "/sessions.json")
listed = [r["id"] for r in json.loads(reply.decode("utf-8"))["sessions"]]
check("/sessions.json lists both sessions", SID["A"] in listed and SID["B"] in listed)
status, reply = ask("GET", "/subjects.json")
check("/subjects.json lists every subject",
      sorted(s["id"] for s in json.loads(reply.decode("utf-8"))["subjects"])
      == sorted(list(SUBJECT.values()) + [LONE, "projects/Meetings"]))
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

check("a session that does not exist is 404",
      ask("GET", "/s/20990101-000000/board.json")[0] == 404
      and ask("GET", "/s/../board.json")[0] == 404)
check("nothing is written into a sessionless Repo's session",
      not [w for w in snapshot() if w.startswith(NONE)])

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

# End, last.
before = snapshot()
status, reply = ask("POST", "/end")
check("unprefixed POST /end is 404 and writes nothing",
      status == 404 and not changed(before, snapshot()))
status, reply = ask("POST", "/s/%s/end" % SID["A"])
wrote = changed(before, snapshot())
got = json.loads(reply.decode("utf-8")) if status == 200 else {}
check("POST /s/A/end ends session A and no other, writing only into A",
      status == 200 and (got.get("session") or {}).get("ended")
      and sessions.get(SID["A"], atlas).get("ended")
      and not sessions.get(SID["B"], atlas).get("ended")
      and wrote and all(w.startswith(os.path.join("sessions", SID["A"]) + os.sep)
                        for w in wrote))
if not (status == 200 and wrote):
    print("       %s %s %s" % (status, got, wrote))
check("and with no runner in this server, no wrap-up is queued",
      got.get("wrapup") is False)

sessions.delete(SID["A"], base=atlas)
check("a deleted session is 404 and leaves the registry",
      ask("GET", "/s/%s/board.json" % SID["A"])[0] == 404
      and SID["A"] not in reg.loaded())

httpd.shutdown()
shutil.rmtree(tmp, ignore_errors=True)
print()
if fails:
    print("%d FAILURES" % len(fails))
    sys.exit(1)
print("every route, in its class, under two sessions: neither reads or writes the other")
