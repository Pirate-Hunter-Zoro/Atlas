#!/usr/bin/env python3
"""A session resumes the document it was annotating, a session from before
`doc` existed included.

    python3 test/resuming.py

Everything runs in a temp Atlas. Nothing here touches the real `sessions/`.

  * A session with no `doc` whose inbox holds `[filed] uploads/X.pdf ->
    courses/<S>/materials/X.pdf` resumes that PDF, the newest such line,
    saved once with the subject and `filed_seen`; on the page with its
    newest ink. A session without such a line is left byte for byte.
  * A line for a file that has gone, a non-PDF, or a path that leaves the
    subject makes no `doc`; an older line whose file is there still does.
  * A document closed afterwards stays closed; a newer `[filed]` line
    resumes again. `file` while a document is open keeps that one.
  * A later `[bind]` to another subject keeps the document and its subject,
    and the session still opens inside itself, on its bare board, since a
    board reads only its own subject; binding back opens the document on the
    board again. `bind` stamps the old subject on a `doc` that has none. A
    session's own upload is in no subject: it gets no subject and opens on
    the board.
  * `forget_doc` clears a `doc` by the subject it names, not the binding.
  * `GET /sessions.json` from a server whose Atlas is not the code's tree
    (`serve.py --atlas`) backfills and lists in that Atlas, `doc` and `url`
    alike, and writes nothing in the code's tree.
"""

import http.client
import json
import os
import shutil
import sys
import tempfile
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD_DIR = os.path.dirname(HERE)
sys.path.insert(0, BOARD_DIR)

fails = []


def check(name, cond, detail=""):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name + (("\n       " + str(detail)) if detail else ""))


def write(path, data, mtime=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb" if isinstance(data, bytes) else "w") as fh:
        fh.write(data)
    if mtime is not None:
        os.utime(path, (mtime, mtime))


def raw(path):
    with open(path, "rb") as fh:
        return fh.read()


box = os.path.realpath(tempfile.mkdtemp(prefix="tutor-resuming-"))
base = os.path.join(box, "Atlas")
os.makedirs(base)
# What `subjects.root()` names for the server part: a tree that is not its Atlas.
code_tree = os.path.join(box, "code")
os.makedirs(code_tree)
os.environ["TUTORBOARD_COURSES"] = base
os.environ["BOARD_STATE_DIR"] = os.path.join(box, ".state")
os.environ["TUTORBOARD_TRASH"] = os.path.join(box, ".trash")
os.environ["XDG_CONFIG_HOME"] = os.path.join(box, ".config")
os.environ["TUTORBOARD_PAGES"] = os.path.join(box, ".pages")
os.environ.pop("TUTORBOARD_SESSION", None)

from tutorboard import sessions                                    # noqa: E402
from tutorboard.course import library                              # noqa: E402
from tutorboard.course import repo as course_repo                  # noqa: E402
from tutorboard.server.routes import library as library_routes     # noqa: E402
from tutorboard.server.routes import writing                       # noqa: E402

PDF = b"%PDF-1.4 fixture\n"


def make_session(title, subject, now):
    rec = sessions.new(title, base=base, now=now)
    where = sessions.path(rec["id"], base)
    sessions.repo(rec["id"], base).set_state(subject=subject)
    return rec["id"], where


def filed(where, shown, at, files=True):
    """A `[filed]` line as `sessions.file` writes it, at time `at`."""
    name = os.path.basename(shown)
    extra = {"files": [shown]} if files else {}
    sessions.quiet_line(os.path.join(where, "inbox", "messages.jsonl"),
                        "[filed] uploads/%s -> %s" % (name, shown), "filed",
                        now=at, **extra)


def legacy(where, doc="absent"):
    """session.json as a session from before `doc` has it: no key, or null."""
    p = os.path.join(where, course_repo.SESSION_JSON)
    rec = json.load(open(p))
    rec.pop("doc", None)
    if doc is None:
        rec["doc"] = None
    write(p, json.dumps(rec, indent=2))
    return p


try:
    prob = os.path.join(base, "courses", "Probability")
    rand = os.path.join(base, "courses", "Random")
    for root, name in ((prob, "Probability"), (rand, "Random")):
        write(os.path.join(root, "tutorboard.json"), json.dumps({"name": name}))
    write(os.path.join(prob, "materials", "Module-2.pdf"), PDF)
    write(os.path.join(prob, "materials", "Module-1.pdf"), PDF)
    write(os.path.join(prob, "materials", "notes.png"), b"\x89PNG")
    write(os.path.join(rand, "materials", "birth_death.pdf"), PDF)
    now = time.time() - 3600
    ids = library.ident_map(prob)
    m2 = ids.get(os.path.realpath(os.path.join(prob, "materials", "Module-2.pdf")))
    m1 = ids.get(os.path.realpath(os.path.join(prob, "materials", "Module-1.pdf")))
    bd = library.ident_map(rand).get(
        os.path.realpath(os.path.join(rand, "materials", "birth_death.pdf")))
    check("the fixture's PDFs are library documents", m2 and m1 and bd,
          (m2, m1, bd))

    # ---- backfill: a session from before `doc`, its PDF filed --------------
    sid, where = make_session("Annotate Module-2.pdf", "courses/Probability", now)
    filed(where, "courses/Probability/materials/Module-2.pdf", now + 1)
    p = legacy(where)
    ink = os.path.join(prob, sessions.INK)
    for page, at in ((3, now + 5), (7, now + 9), (5, now + 7)):
        key = "doc/%s/p%d" % (m2, page)
        write(os.path.join(ink, writing.ann_file(key) + ".json"),
              json.dumps({"card": key, "strokes": []}), mtime=at)
    # A newer erased page is no place to resume.
    gone = "doc/%s/p9" % m2
    write(os.path.join(ink, writing.ann_file(gone) + ".gone"), "{}", mtime=now + 20)
    rec = sessions.get(sid, base)
    got = sessions.url(rec, base)
    check("a session with no doc resumes the PDF its [filed] line names, "
          "on its newest inked page",
          got == "/s/%s/board#/s/%s/doc/%s/p7" % (sid, sid, m2), got)
    saved = json.load(open(p))
    check("the backfill is saved once with its subject and the line's time",
          saved.get("doc") == {"id": m2, "page": 7, "name": "Module-2.pdf",
                               "subject": "courses/Probability"}
          and saved.get("filed_seen") == now + 1, saved)

    sid2, where2 = make_session("Annotate Module-1.pdf", "courses/Probability", now)
    filed(where2, "courses/Probability/materials/Module-1.pdf", now + 1, files=False)
    legacy(where2, doc=None)
    got = sessions.url(sessions.get(sid2, base), base)
    check("a doc of null backfills too, from the line's text alone, page unknown",
          got == "/s/%s/board#/s/%s/doc/%s" % (sid2, sid2, m1), got)

    sid3, where3 = make_session("Two filings", "courses/Probability", now)
    filed(where3, "courses/Probability/materials/Module-1.pdf", now + 1)
    filed(where3, "courses/Probability/materials/Module-2.pdf", now + 2)
    filed(where3, "courses/Probability/materials/notes.png", now + 3)
    doc3 = sessions.resumed(sessions.get(sid3, base), base).get("doc") or {}
    check("of several [filed] lines the newest PDF wins, a picture skipped",
          doc3.get("id") == m2, doc3)

    # ---- left alone ---------------------------------------------------------
    sid4, where4 = make_session("A lesson", "courses/Probability", now)
    p4 = legacy(where4)
    before = raw(p4)
    got = sessions.url(sessions.get(sid4, base), base)
    check("a session without a [filed] line opens the bare board, its file "
          "untouched", got == "/s/%s/board" % sid4 and raw(p4) == before, got)

    sid5, where5 = make_session("Gone", "courses/Probability", now)
    filed(where5, "courses/Probability/materials/deleted.pdf", now + 1)
    filed(where5, "courses/Probability/materials/../../Random/materials/"
                  "birth_death.pdf", now + 2)
    filed(where5, "courses/Nowhere/materials/x.pdf", now + 3)
    p5 = legacy(where5)
    before = raw(p5)
    got = sessions.url(sessions.get(sid5, base), base)
    check("a [filed] line for a file that has gone, a path leaving the "
          "subject or no subject makes no doc",
          got == "/s/%s/board" % sid5 and raw(p5) == before, got)

    filed(where5, "courses/Probability/materials/Module-1.pdf", now - 5)
    doc5 = sessions.resumed(sessions.get(sid5, base), base).get("doc") or {}
    check("an older [filed] line whose file is there still resumes",
          doc5.get("id") == m1, doc5)

    sid6, where6 = make_session("A stored doc", "courses/Probability", now)
    filed(where6, "courses/Probability/materials/Module-2.pdf", now + 1)
    mine = {"id": m1, "page": 2, "name": "Module-1.pdf"}
    sessions.repo(sid6, base).set_state(doc=mine)
    got = sessions.url(sessions.get(sid6, base), base)
    check("a stored doc stands over a [filed] line",
          got == "/s/%s/board#/s/%s/doc/%s/p2" % (sid6, sid6, m1)
          and sessions.get(sid6, base).get("doc") == mine, got)

    # ---- closed stays closed ------------------------------------------------
    sessions.repo(sid, base).set_state(doc=None)    # what `/seen` does on close
    got = sessions.url(sessions.get(sid, base), base)
    check("a document closed after its backfill stays closed",
          got == "/s/%s/board" % sid and sessions.get(sid, base).get("doc") is None,
          got)
    filed(where, "courses/Probability/materials/Module-1.pdf", now + 30)
    got = sessions.url(sessions.get(sid, base), base)
    check("a newer [filed] line resumes again",
          got == "/s/%s/board#/s/%s/doc/%s" % (sid, sid, m1), got)

    # `file` while a document is on the glass: that one stays the resume.
    sid7, where7 = make_session("Filing", "courses/Probability", now)
    write(os.path.join(where7, "uploads", "extra.pdf"), PDF)
    open_doc = {"id": m2, "page": 4, "name": "Module-2.pdf"}
    sessions.repo(sid7, base).set_state(doc=open_doc)
    sessions.file(sid7, "extra.pdf", base=base)
    sessions.repo(sid7, base).set_state(doc=None)
    got = sessions.url(sessions.get(sid7, base), base)
    check("a filing while another document was open does not reopen the "
          "filed one once that is closed", got == "/s/%s/board" % sid7, got)

    sid8, where8 = make_session("Filing, nothing open", "courses/Probability", now)
    write(os.path.join(where8, "uploads", "fresh.pdf"), PDF)
    sessions.file(sid8, "fresh.pdf", base=base)
    doc8 = sessions.resumed(sessions.get(sid8, base), base).get("doc") or {}
    check("a filing with nothing open resumes the filed PDF",
          doc8.get("name") == "fresh.pdf"
          and doc8.get("subject") == "courses/Probability", doc8)

    # ---- a later bind to another subject ------------------------------------
    sid9, where9 = make_session("Annotate birth_death.pdf", "courses/Random", now)
    filed(where9, "courses/Random/materials/birth_death.pdf", now + 1)
    legacy(where9)
    sessions.bind(sid9, "courses/Probability", base=base, now=now + 2, force=True)
    rec9 = sessions.get(sid9, base)
    got = sessions.url(rec9, base)
    doc9 = sessions.get(sid9, base).get("doc") or {}
    check("a [bind] to another subject after the filing still resolves the "
          "PDF in its own subject, and the session opens inside itself",
          got == "/s/%s/board" % sid9 and doc9.get("id") == bd
          and doc9.get("subject") == "courses/Random", (got, doc9))
    check("never a URL outside the session",
          got.startswith("/s/%s/" % sid9), got)
    listed = [d for d in library.documents(rand) if d["id"] == bd]
    check("that subject's library still holds the document with a PDF",
          len(listed) == 1 and listed[0]["pdf"], listed)
    sessions.bind(sid9, "courses/Random", base=base, now=now + 3, force=True)
    got = sessions.url(sessions.get(sid9, base), base)
    check("bound back, it opens on the board again",
          got == "/s/%s/board#/s/%s/doc/%s" % (sid9, sid9, bd), got)

    sid10, where10 = make_session("Read, then moved", "courses/Probability", now)
    sessions.repo(sid10, base).set_state(doc={"id": m2, "page": 3,
                                              "name": "Module-2.pdf"})
    sessions.bind(sid10, "courses/Random", base=base, now=now + 2, force=True)
    doc10 = sessions.get(sid10, base).get("doc") or {}
    got = sessions.url(sessions.get(sid10, base), base)
    check("bind stamps the old subject on a doc that names none",
          doc10.get("subject") == "courses/Probability"
          and got == "/s/%s/board" % sid10,
          (doc10, got))
    sid11, _ = make_session("Moved, nothing open", "courses/Probability", now)
    sessions.bind(sid11, "courses/Random", base=base, now=now + 2, force=True)
    check("bind leaves a session with no doc without one",
          sessions.get(sid11, base).get("doc") is None)

    bad = {"id": sid10, "view": "board", "subject": "courses/Random",
           "doc": {"id": m2, "page": 1, "name": "x", "subject": "../../etc"}}
    check("a doc naming a malformed subject opens the bare board",
          sessions.url(bad, base) == "/s/%s/board" % sid10, sessions.url(bad, base))

    # A session's own upload: in no subject's library, on the board always.
    sid12, where12 = make_session("Upload, then moved", "courses/Probability", now)
    write(os.path.join(where12, "uploads", "slides.pdf"), PDF)
    up = sessions.repo(sid12, base)
    ups = [u["id"] for u in library.uploads(up)]
    up.set_state(doc={"id": ups[0] if ups else "", "page": 2,
                      "name": "slides.pdf"})
    sessions.bind(sid12, "courses/Random", base=base, now=now + 2, force=True)
    doc12 = sessions.get(sid12, base).get("doc") or {}
    got = sessions.url(sessions.get(sid12, base), base)
    check("bind stamps no subject on the session's own upload, which still "
          "opens on the board",
          ups and ups[0].startswith(sessions.UPLOAD_DOC)
          and "subject" not in doc12
          and got == "/s/%s/board#/s/%s/doc/%s/p2" % (sid12, sid12, ups[0]),
          (ups, doc12, got))
    stamped = {"id": sid12, "view": "board", "subject": "courses/Random",
               "doc": dict(doc12, subject="courses/Probability")}
    check("an upload's doc naming another subject still opens on the board",
          sessions.url(stamped, base).startswith("/s/%s/board#" % sid12),
          sessions.url(stamped, base))

    # ---- forget_doc by the doc's subject -------------------------------------
    class _Repo(object):
        atlas = base
    library_routes.forget_doc(_Repo(), "courses/Random", m2)
    check("forget_doc leaves a doc in another subject than the one named",
          (sessions.get(sid10, base).get("doc") or {}).get("id") == m2)
    library_routes.forget_doc(_Repo(), "courses/Probability", m2)
    check("forget_doc clears a doc by the subject it names, whatever the "
          "session is bound to", sessions.get(sid10, base).get("doc") is None)

    # ---- GET /sessions.json, the server's Atlas not the code's tree ---------
    sid13, where13 = make_session("Annotate birth_death.pdf", "courses/Random", now)
    filed(where13, "courses/Random/materials/birth_death.pdf", now + 1)
    p13 = legacy(where13)
    sid14, where14 = make_session("Plain lesson", "courses/Random", now)
    p14 = legacy(where14)
    before14 = raw(p14)
    from tutorboard.server import app                       # noqa: E402
    os.environ["TUTORBOARD_COURSES"] = code_tree             # `serve.py --atlas`
    httpd = app.make_server(base, 0, start=False)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        conn = http.client.HTTPConnection("127.0.0.1", httpd.server_port,
                                          timeout=60)
        conn.request("GET", "/sessions.json")
        resp = conn.getresponse()
        listing = json.loads(resp.read().decode("utf-8"))
        conn.close()
    finally:
        httpd.shutdown()
        httpd.server_close()
        os.environ["TUTORBOARD_COURSES"] = base
    by = {one.get("id"): one for one in listing.get("sessions") or []}
    one13, one14 = by.get(sid13) or {}, by.get(sid14) or {}
    check("/sessions.json backfills a session in the server's Atlas: url and "
          "doc both name the PDF on the first GET",
          resp.status == 200
          and one13.get("url") == "/s/%s/board#/s/%s/doc/%s" % (sid13, sid13, bd)
          and (one13.get("doc") or {}).get("id") == bd
          and (json.load(open(p13)).get("doc") or {}).get("id") == bd,
          (resp.status, one13.get("url"), one13.get("doc")))
    check("/sessions.json leaves a session with no [filed] line on the bare "
          "board, its file untouched",
          one14.get("url") == "/s/%s/board" % sid14 and not one14.get("doc")
          and raw(p14) == before14, (one14.get("url"), one14.get("doc")))
    check("/sessions.json writes nothing in the code's own tree",
          os.listdir(code_tree) == [], os.listdir(code_tree))
finally:
    shutil.rmtree(box, ignore_errors=True)

if fails:
    print("\n%d failed: %s" % (len(fails), ", ".join(fails)))
    sys.exit(1)
print("\nall passed")
