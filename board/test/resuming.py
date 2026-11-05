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
    and the session opens it on its board, in the document's subject (the
    real 20261102-144106: bound to Random, filed there, bound to
    Probability). `bind` stamps the old subject on a `doc` that has none. A
    session's own upload is in no subject: it gets no subject and opens on
    the board. A `doc` naming a subject that is none opens the bare board.
  * `forget_doc` clears a `doc` by the subject it names, not the binding.
  * `GET /sessions.json` from a server whose Atlas is not the code's tree
    (`serve.py --atlas`) backfills and lists in that Atlas, `doc` and `url`
    alike, and writes nothing in the code's tree. A session whose backfill
    raises (a `[filed]` path with a NUL byte, a session directory it cannot
    write) is listed without a document, and the rest are listed.
  * The session board reads, inks, burns and `/seen`s a document in the
    subject its stored `doc` names, or the board names (`?subject=`), even
    where the session's own subject has a document of the same id. A subject
    that is none, a path that climbs, and an id the subject does not hold
    are refused.
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


def real_pdf(n):
    """A PDF of `n` blank pages a renderer can draw."""
    objs = ["<< /Type /Catalog /Pages 2 0 R >>",
            "<< /Type /Pages /Count %d /Kids [%s] >>"
            % (n, " ".join("%d 0 R" % (3 + i) for i in range(n)))]
    for _ in range(n):
        objs.append("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 400] >>")
    out, offs = b"%PDF-1.4\n", []
    for i, obj in enumerate(objs, start=1):
        offs.append(len(out))
        out += ("%d 0 obj\n" % i).encode() + obj.encode() + b"\nendobj\n"
    start = len(out)
    out += ("xref\n0 %d\n" % (len(objs) + 1)).encode() + b"0000000000 65535 f \n"
    for off in offs:
        out += ("%010d 00000 n \n" % off).encode()
    out += ("trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"
            % (len(objs) + 1, start)).encode()
    return out


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
    # Random's has two pages; Probability has a one-page document of the
    # same id, so reading the wrong subject shows.
    write(os.path.join(rand, "materials", "birth_death.pdf"), real_pdf(2))
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
    # The real 20261102-144106: bound to Random, the PDF filed there, then
    # bound to Probability.
    sid9, where9 = make_session("Annotate birth_death.pdf", "courses/Random", now)
    filed(where9, "courses/Random/materials/birth_death.pdf", now + 1)
    legacy(where9)
    sessions.bind(sid9, "courses/Probability", base=base, now=now + 2, force=True)
    rec9 = sessions.get(sid9, base)
    got = sessions.url(rec9, base)
    doc9 = sessions.get(sid9, base).get("doc") or {}
    check("a [bind] to another subject after the filing still resumes the "
          "PDF on the session's board, its subject kept",
          got == "/s/%s/board#/s/%s/doc/%s" % (sid9, sid9, bd)
          and doc9.get("id") == bd
          and doc9.get("subject") == "courses/Random", (got, doc9))
    check("never a URL outside the session",
          got.startswith("/s/%s/" % sid9), got)
    home9 = sessions.reading(sessions.repo(sid9, base), bd)
    check("the session reads it through its subject, not its binding",
          os.path.realpath(home9.root) == os.path.realpath(rand)
          and os.path.realpath(home9.doc_ink) == os.path.realpath(
              os.path.join(rand, sessions.INK))
          and home9.session == sessions.repo(sid9, base).session,
          (home9.root, home9.doc_ink))
    listed = [d for d in library.documents(rand) if d["id"] == bd]
    check("that subject's library still holds the document with a PDF",
          len(listed) == 1 and listed[0]["pdf"], listed)
    sessions.bind(sid9, "courses/Random", base=base, now=now + 3, force=True)
    got = sessions.url(sessions.get(sid9, base), base)
    check("bound back, it opens on the board again",
          got == "/s/%s/board#/s/%s/doc/%s" % (sid9, sid9, bd), got)
    check("bound back, it is read through the session's own Repo",
          os.path.realpath(sessions.reading(sessions.repo(sid9, base), bd).root)
          == os.path.realpath(rand))
    sessions.bind(sid9, "courses/Probability", base=base, now=now + 4, force=True)

    sid10, where10 = make_session("Read, then moved", "courses/Probability", now)
    sessions.repo(sid10, base).set_state(doc={"id": m2, "page": 3,
                                              "name": "Module-2.pdf"})
    sessions.bind(sid10, "courses/Random", base=base, now=now + 2, force=True)
    doc10 = sessions.get(sid10, base).get("doc") or {}
    got = sessions.url(sessions.get(sid10, base), base)
    check("bind stamps the old subject on a doc that names none",
          doc10.get("subject") == "courses/Probability"
          and got == "/s/%s/board#/s/%s/doc/%s/p3" % (sid10, sid10, m2),
          (doc10, got))
    sid11, _ = make_session("Moved, nothing open", "courses/Probability", now)
    sessions.bind(sid11, "courses/Random", base=base, now=now + 2, force=True)
    check("bind leaves a session with no doc without one",
          sessions.get(sid11, base).get("doc") is None)

    bad = {"id": sid10, "view": "board", "subject": "courses/Random",
           "doc": {"id": m2, "page": 1, "name": "x", "subject": "../../etc"}}
    check("a doc naming a malformed subject opens the bare board",
          sessions.url(bad, base) == "/s/%s/board" % sid10, sessions.url(bad, base))
    for said in ("courses/Nowhere", "courses/Random/../Probability",
                 "courses/..", "Random", "/etc", "courses/Random/materials"):
        odd = dict(bad, doc=dict(bad["doc"], subject=said))
        check("a doc naming %r opens the bare board" % said,
              sessions.url(odd, base) == "/s/%s/board" % sid10,
              sessions.url(odd, base))
    r10 = sessions.repo(sid10, base)
    for said in ("courses/Nowhere", "courses/../courses/Probability",
                 "../../etc", "courses/Probability/../Random", "courses/Rand\x00om"):
        try:
            sessions.reading(r10, m2, said)
            refused = False
        except sessions.NotReadable:
            refused = True
        check("reading refuses the subject %r" % said, refused)
    try:
        sessions.reading(sessions.repo(sid9, base), m1, "courses/Random")
        refused = False
    except sessions.NotReadable:
        refused = True
    check("reading refuses an id the named subject does not hold", refused)

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
    # A [filed] line whose path carries a NUL byte, and nothing else.
    sid15, where15 = make_session("Annotate nul.pdf", "courses/Random", now)
    filed(where15, "courses/Random/materials/bad\x00name.pdf", now + 1)
    legacy(where15)
    # A session whose backfill cannot be saved: its directory is read-only.
    sid16, where16 = make_session("Annotate locked.pdf", "courses/Random", now)
    filed(where16, "courses/Random/materials/birth_death.pdf", now + 1)
    legacy(where16)
    # The NUL line newer than a good one: the good one still resumes.
    sid17, where17 = make_session("Two lines, one bad", "courses/Random", now)
    filed(where17, "courses/Random/materials/birth_death.pdf", now + 1)
    filed(where17, "courses/Random/materials/bad\x00name.pdf", now + 2)
    legacy(where17)
    check("a [filed] line with a NUL byte is passed over for an older one",
          (sessions.resumed(sessions.get(sid17, base), base).get("doc")
           or {}).get("id") == bd)
    # Same-id documents in the session's subject and the doc's: the board
    # must read Random's two pages, never Probability's one.
    write(os.path.join(prob, "materials", "birth_death.pdf"), real_pdf(1))
    library.forget()
    p9 = os.path.join(where9, course_repo.SESSION_JSON)

    from tutorboard.server import app                       # noqa: E402
    os.environ["TUTORBOARD_COURSES"] = code_tree             # `serve.py --atlas`
    httpd = app.make_server(base, 0, start=False)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    def ask(method, url, body=None):
        conn = http.client.HTTPConnection("127.0.0.1", httpd.server_port,
                                          timeout=60)
        data = None if body is None else json.dumps(body).encode("utf-8")
        conn.request(method, url, body=data,
                     headers={"Content-Type": "application/json"})
        got = conn.getresponse()
        text = got.read()
        conn.close()
        try:
            return got.status, json.loads(text.decode("utf-8"))
        except ValueError:
            return got.status, text

    os.chmod(where16, 0o555)
    try:
        status, listing = ask("GET", "/sessions.json")
        listed = status
        by = {one.get("id"): one for one in listing.get("sessions") or []}
        one15, one16 = by.get(sid15) or {}, by.get(sid16) or {}
        check("/sessions.json lists a session whose [filed] path has a NUL "
              "byte, on its bare board without a document",
              status == 200 and one15.get("url") == "/s/%s/board" % sid15
              and not one15.get("doc"), one15)
        check("/sessions.json lists a session it cannot write, without a "
              "document, and the others besides",
              one16.get("url") == "/s/%s/board" % sid16
              and not one16.get("doc") and sid13 in by and sid14 in by,
              (one16.get("url"), one16.get("doc"), sorted(by)))
        os.chmod(where16, 0o755)
        # Whatever a backfill raises, ValueError (os.path.realpath on a NUL)
        # included, is that session's alone.
        from tutorboard.server import handler as handler_mod   # noqa: E402
        real_resumed = sessions.resumed

        def raising(rec, base_=None):
            if rec.get("id") == sid15:
                raise ValueError("embedded null byte")
            return real_resumed(rec, base_)
        sessions.resumed = raising
        try:
            again = handler_mod.Handler.session_listing(httpd.registry)
        finally:
            sessions.resumed = real_resumed
        by2 = {one.get("id"): one for one in again.get("sessions") or []}
        check("a ValueError from one backfill lists that session without a "
              "document, and the rest with theirs",
              by2.get(sid15, {}).get("url") == "/s/%s/board" % sid15
              and by2.get(sid15, {}).get("doc") is None
              and (by2.get(sid13, {}).get("doc") or {}).get("id") == bd,
              (by2.get(sid15), by2.get(sid13, {}).get("doc")))

        # ---- the session board reads its document in the doc's subject ---
        pre = "/s/%s" % sid9
        status, got = ask("GET", pre + "/view/doc/" + bd)
        check("/view/doc reads the stored doc's subject, not the binding: "
              "Random's two pages", status == 200 and got.get("ok")
              and got.get("n") == 2, (status, got))
        status, got = ask("GET", pre + "/view/doc/%s?subject=courses/Random" % bd)
        check("/view/doc with ?subject= naming that subject reads it too",
              got.get("ok") and got.get("n") == 2, got)
        status, got = ask("GET", pre + "/view/doc/%s?subject=courses/Probability"
                          % bd)
        check("/view/doc naming the session's own subject reads that one",
              got.get("ok") and got.get("n") == 1, got)
        for said in ("courses/Nowhere", "courses/../../etc",
                     "courses/Probability/../Random", "..%2F..%2Fetc"):
            status, got = ask("GET", pre + "/view/doc/%s?subject=%s" % (bd, said))
            check("/view/doc refuses ?subject=%s" % said,
                  not got.get("ok") and got.get("why") == "none", (status, got))
        status, got = ask("GET", pre + "/view/doc/%s?subject=courses/Random" % m1)
        check("/view/doc refuses an id the named subject does not hold",
              not got.get("ok"), got)
        status, png = ask("GET", pre + "/doc/%s/2.png" % bd)
        check("/doc/<id>/<n>.png serves Random's second page",
              status == 200 and isinstance(png, bytes)
              and png[:4] == b"\x89PNG", status)
        status, _ = ask("GET", pre + "/doc/%s/2.png?subject=courses/Nowhere" % bd)
        check("/doc/<id>/<n>.png refuses a subject that is none", status == 404,
              status)

        key = "doc/%s/p2" % bd
        stroke = {"c": "#ff0000", "w": 2, "p": [0.1, 0.1, 0.4, 0.4],
                  "pr": [0.5, 0.5], "pg": 1}
        status, got = ask("POST", pre + "/annotate/save",
                          {"card": key, "strokes": [stroke]})
        rand_ink = os.path.join(rand, sessions.INK, writing.ann_file(key) + ".json")
        prob_ink = os.path.join(prob, sessions.INK, writing.ann_file(key) + ".json")
        check("/annotate/save keeps the page's ink in the document's subject",
              status == 200 and got.get("ok") and os.path.isfile(rand_ink)
              and not os.path.exists(prob_ink), (status, got))
        status, got = ask("GET", pre + "/view/doc/" + bd)
        check("and /view/doc hands that ink back",
              key in (got.get("ink") or {}), sorted(got.get("ink") or {}))
        for said in ("courses/Nowhere", "courses/../../etc"):
            status, got = ask("POST", pre + "/annotate/save?subject=" + said,
                              {"card": key, "strokes": []})
            check("/annotate/save refuses ?subject=%s" % said,
                  status == 400 and not got.get("ok"), (status, got))
        check("a refused save wrote nothing",
              json.load(open(rand_ink)).get("strokes") == [stroke])
        status, got = ask("POST", pre + "/annotate/save",
                          {"card": "0001", "strokes": []})
        check("card ink stays the session's", status == 200 and os.path.isfile(
            os.path.join(where9, "annotations", "0001.json")), (status, got))

        status, got = ask("POST", pre + "/annotate/burn",
                          {"kind": "doc/" + bd, "mode": "none"})
        check("/annotate/burn finds the ink in the document's subject",
              status == 200 and got.get("ok") and got.get("marks") == 1,
              (status, got))
        status, got = ask("POST", pre + "/annotate/burn?subject=courses/Nowhere",
                          {"kind": "doc/" + bd, "mode": "none"})
        check("/annotate/burn refuses a subject that is none",
              status == 400 and not got.get("ok"), (status, got))
        status, got = ask("POST", pre + "/annotate/burn?subject=courses/Random",
                          {"kind": "doc/" + bd, "mode": "new"})
        name = got.get("name") or ""
        check("/annotate/burn keeps a marked copy beside Random's PDF",
              got.get("ok") and os.path.isfile(
                  os.path.join(rand, "materials", name)), got)
        status, pdf = ask("GET", pre + "/marked/doc/%s/%s?subject=courses/Random"
                          % (bd, name))
        check("/marked serves that copy from the document's subject",
              status == 200 and pdf[:5] == b"%PDF-", status)
        status, _ = ask("GET", pre + "/marked/doc/%s/%s?subject=courses/Nowhere"
                        % (bd, name))
        check("/marked refuses a subject that is none", status == 404, status)

        status, got = ask("POST", pre + "/seen",
                          {"doc": {"id": bd, "page": 2, "name": "birth_death.pdf"}})
        stored = json.load(open(p9)).get("doc") or {}
        check("/seen of the same document without a subject keeps its subject",
              status == 200 and stored.get("subject") == "courses/Random"
              and stored.get("page") == 2, stored)
        status, got = ask("POST", pre + "/seen",
                          {"doc": {"id": bd, "page": 1, "name": "birth_death.pdf",
                                   "subject": "courses/Random"}})
        stored = json.load(open(p9)).get("doc") or {}
        check("/seen naming the document's subject stores it",
              status == 200 and stored.get("subject") == "courses/Random"
              and stored.get("page") == 1, stored)
        for said in ("courses/Nowhere", "../../etc", "courses/../../etc", 7):
            status, got = ask("POST", pre + "/seen",
                              {"doc": {"id": bd, "page": 5, "name": "x",
                                       "subject": said}})
            check("/seen refuses the subject %r and keeps what was stored"
                  % (said,), status == 400
                  and (json.load(open(p9)).get("doc") or {}).get("page") == 1,
                  (status, got))
        status, got = ask("POST", pre + "/seen",
                          {"doc": {"id": m1, "page": 1, "name": "x",
                                   "subject": "courses/Random"}})
        check("/seen refuses an id the named subject does not hold",
              status == 400, (status, got))
        status, got = ask("POST", pre + "/seen",
                          {"doc": {"id": bd, "page": 1, "name": "birth_death.pdf",
                                   "subject": ""}})
        stored = json.load(open(p9)).get("doc") or {}
        check("/seen naming no subject stores the session's own document",
              status == 200 and stored.get("id") == bd and "subject" not in stored,
              stored)
        status, got = ask("GET", pre + "/view/doc/" + bd)
        check("which /view/doc then reads in the session's subject",
              got.get("ok") and got.get("n") == 1, got)
    finally:
        os.chmod(where16, 0o755)
        httpd.shutdown()
        httpd.server_close()
        os.environ["TUTORBOARD_COURSES"] = base
    one13, one14 = by.get(sid13) or {}, by.get(sid14) or {}
    check("/sessions.json backfills a session in the server's Atlas: url and "
          "doc both name the PDF on the first GET",
          listed == 200
          and one13.get("url") == "/s/%s/board#/s/%s/doc/%s" % (sid13, sid13, bd)
          and (one13.get("doc") or {}).get("id") == bd
          and (json.load(open(p13)).get("doc") or {}).get("id") == bd,
          (listed, one13.get("url"), one13.get("doc")))
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
