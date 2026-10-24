#!/usr/bin/env python3
"""`board textbook`: split and scaffold, then ingest, find and status.

    python3 test/textbook.py

A temp tree holds courses/Fixture with a 6-page textbook PDF (made by gs from
PostScript, so no TeX is needed) and a 3-chapter chapters.tsv. Scaffolding
renders board/tex/writeup.tex.in; a course keeps no templates. The scripts
also run under /bin/bash where it is the Mac's 3.2.

The index (`course/book.py`) runs on three more gs-made books: one whose
outline has numbered chapters, sections and a "Solutions" item after them,
with one page that is only an image; one with no outline at all; and an
upload into a course with no textbook yet. The server's Ingester wakes its
session with the `[textbook]` line, and the brief and the homework sense
name `board textbook find`.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = os.path.dirname(HERE)
CLI = os.path.join(BOARD, "bin", "board")
SCRIPTS = os.path.join(BOARD, "scripts")
sys.path.insert(0, BOARD)

fails = []


def ok(msg):
    print("ok   " + msg)


def fail(msg):
    fails.append(msg)
    print("FAIL " + msg)


def put(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def board(args, base):
    env = dict(os.environ, TUTORBOARD_COURSES=base)
    return subprocess.run([sys.executable, CLI] + args, cwd=base, env=env,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          universal_newlines=True)


def pages(pdf):
    """Page count from pdfinfo, or None where it is not installed."""
    if not shutil.which("pdfinfo"):
        return None
    out = subprocess.run(["pdfinfo", pdf], stdout=subprocess.PIPE,
                         stderr=subprocess.DEVNULL,
                         universal_newlines=True).stdout
    for line in out.splitlines():
        if line.startswith("Pages:"):
            return int(line.split()[1])
    return -1


TSV = ("# num first last slug title\n"
       "01\t1\t2\tbeginnings\tBeginnings\n"
       "02\t3\t3\tmiddles\tMiddles\n"
       "03\t4\t6\tends\tEnds, and what follows\n")


def titled(path, title):
    """Is `path` the template rendered with `title`?"""
    try:
        body = open(path, encoding="utf-8").read()
    except OSError:
        return False
    return ("\\title{%s}" % title) in body and "@@" not in body \
        and "\\documentclass" in body


def fixture(base):
    course = os.path.join(base, "courses", "Fixture")
    put(os.path.join(course, "chapters.tsv"), TSV)
    ps = os.path.join(base, "book.ps")
    put(ps, "%!PS\n" + "".join(
        "/Helvetica findfont 24 scalefont setfont 72 720 moveto "
        "(page %d) show showpage\n" % n for n in range(1, 7)))
    os.makedirs(os.path.join(course, "textbook"))
    subprocess.run(["gs", "-q", "-dSAFER", "-dBATCH", "-dNOPAUSE",
                    "-sDEVICE=pdfwrite",
                    "-sOutputFile=" + os.path.join(course, "textbook",
                                                   "Book.pdf"), ps],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return course


# ---------------------------------------------------------------------------
# the index: books made by gs, with and without an outline
# ---------------------------------------------------------------------------
def ps_page(lines, num=None):
    """One PostScript page: `lines` from the top, `num` at the foot."""
    out = ["/Helvetica findfont 14 scalefont setfont"]
    y = 720
    for line in lines:
        out.append("72 %d moveto (%s) show" % (y, line))
        y -= 22
    if num is not None:
        out.append("300 60 moveto (%d) show" % num)
    return "\n".join(out + ["showpage"]) + "\n"


def gs(device, out, *inputs):
    subprocess.run(["gs", "-q", "-dSAFER", "-dBATCH", "-dNOPAUSE",
                    "-sDEVICE=" + device, "-sOutputFile=" + out] + list(inputs),
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                   check=True)


def outlined_book(where):
    """10 pages, printed number = PDF page - 1 from page 2. The outline:
    1 Beginnings (1.1, 1.2), 2 Middles (2.1), 3 Ends, then "Solutions to
    Exercises". Page 7, chapter 3's opener, is an image with no text."""
    os.makedirs(where, exist_ok=True)
    head = [
        ps_page(["Contents", "1 Beginnings 1", "2 Middles 4", "3 Ends 6"]),
        ps_page(["1 Beginnings", "", "1.1  First things",
                 "Text about the first things."], 1),
        ps_page(["1.2  Second things", "More text on second things."], 2),
        ps_page(["Exercises", "1.1 Show that the first thing holds.",
                 "1.2 Prove the second thing.", "1.3 Find a third thing."], 3),
        ps_page(["2 Middles", "", "2.1  Halfway", "Exercises",
                 "2.1 Halve a number."], 4),
        ps_page(["Text in the middle of things.", "2.2 Double a number."], 5),
    ]
    image = ps_page(["3 Ends", "", "Everything ends somewhere."], 6)
    tail = [
        ps_page(["Exercises", "3.1 End it."], 7),
        ps_page(["Solutions to Exercises", "1.1 It holds."], 8),
        ps_page(["More solutions."], 9),
    ]
    marks = ("%!PS\n"
             "[/Count 2 /Title (1 Beginnings) /Page 2 /OUT pdfmark\n"
             "[/Title (1.1 First things) /Page 2 /OUT pdfmark\n"
             "[/Title (1.2 Second things) /Page 3 /OUT pdfmark\n"
             "[/Count 1 /Title (2 Middles) /Page 5 /OUT pdfmark\n"
             "[/Title (2.1 Halfway) /Page 5 /OUT pdfmark\n"
             "[/Title (3 Ends) /Page 7 /OUT pdfmark\n"
             "[/Title (Solutions to Exercises) /Page 9 /OUT pdfmark\n")
    parts = {"a": "%!PS\n" + "".join(head), "img": "%!PS\n" + image,
             "c": "%!PS\n" + "".join(tail), "marks": marks}
    for name, text in parts.items():
        put(os.path.join(where, name + ".ps"), text)
    j = lambda name: os.path.join(where, name)              # noqa: E731
    gs("pdfwrite", j("a.pdf"), j("a.ps"))
    # pdfimage24 draws each page as a picture: no text layer at all.
    gs("pdfimage24", j("img.pdf"), "-r150", j("img.ps"))
    gs("pdfwrite", j("c.pdf"), j("c.ps"))
    gs("pdfwrite", j("book.pdf"), j("a.pdf"), j("img.pdf"), j("c.pdf"),
       j("marks.ps"))
    return j("book.pdf")


def plain_book(where):
    """6 pages and no outline: "Chapter N" opens pages 1, 3 and 5."""
    os.makedirs(where, exist_ok=True)
    pages = []
    for n, title in ((1, "Beginnings"), (2, "Middles"), (3, "Ends")):
        pages.append(ps_page(["Chapter %d %s" % (n, title), "",
                              "The opening of chapter %d." % n]))
        pages.append(ps_page(["The rest of chapter %d, which goes on for "
                              "a while." % n]))
    put(os.path.join(where, "plain.ps"), "%!PS\n" + "".join(pages))
    gs("pdfwrite", os.path.join(where, "plain.pdf"), os.path.join(where, "plain.ps"))
    return os.path.join(where, "plain.pdf")


def has_ocr():
    try:
        out = subprocess.run(["gs", "-h"], stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT,
                             universal_newlines=True).stdout
    except OSError:
        return False
    return " ocr" in out


def index_suite(base):
    from tutorboard.course import book
    from tutorboard import brief as brief_mod
    from tutorboard import sense as sense_mod
    from tutorboard.server.routes import textbook as route

    made = os.path.join(base, "made")
    pdf = outlined_book(made)
    course = os.path.join(base, "courses", "Booked")
    os.makedirs(os.path.join(course, "textbook"))
    shutil.copyfile(pdf, os.path.join(course, "textbook", "Book.pdf"))
    # The hand-made table: right but for chapter 3, which it runs a page long.
    table = ("# the owner's comment\n"
             "01\t2\t4\tbeginnings\tBeginnings\n"
             "02\t5\t6\tmiddles\tMiddles\n"
             "03\t7\t9\tthe-end\tEnds\n")
    put(os.path.join(course, "chapters.tsv"), table)

    # ---- --check: the differences, and nothing written -----------------
    p = board(["textbook", "ingest", "courses/Booked", "--check"], base)
    if p.returncode == 1 and "1 chapter-row difference(s)" in p.stdout \
            and "~ ch03 table 7-9 Ends | book 7-8 Ends" in p.stdout:
        ok("ingest --check prints the one chapter row the table has wrong, "
           "and exits 1")
    else:
        fail("ingest --check: %d %s" % (p.returncode, p.stdout))
    if open(os.path.join(course, "chapters.tsv")).read() == table \
            and not os.path.isdir(os.path.join(course, "chapters")):
        ok("and writes no chapters.tsv and splits nothing")
    else:
        fail("ingest --check wrote chapters.tsv or split")

    index = book.read(course) or {}
    rows = [(c["num"], c["first"], c["last"], c["title"])
            for c in index.get("chapters") or []]
    if rows == [("01", 2, 4, "Beginnings"), ("02", 5, 6, "Middles"),
                ("03", 7, 8, "Ends")]:
        ok("the outline gives the chapters; each ends a page before the next "
           "item at its depth")
    else:
        fail("the chapters from the outline: %r" % rows)
    if any("Solutions to Exercises" in d for d in index.get("doubts") or []):
        ok("the chapters stop at the Solutions item, recorded as a doubt")
    else:
        fail("no doubt for the back matter: %r" % index.get("doubts"))
    secs = [(s["num"], s["page"]) for s in index.get("sections") or []]
    if secs == [("1.1", 2), ("1.2", 3), ("2.1", 5)]:
        ok("the sections come from the outline")
    else:
        fail("the sections: %r" % secs)
    labels = [(r["first"], r["last"], r["offset"]) for r in index.get("labels") or []]
    if labels == [(1, 10, 1)]:
        ok("the printed page numbers are one run, PDF page - 1")
    else:
        fail("the printed page runs: %r" % labels)
    exs = [e["label"] for e in index.get("exercises") or []]
    if exs == ["1.1", "1.2", "1.3", "2.1", "2.2", "3.1"]:
        ok("the exercises are read after each \"Exercises\" line, chapter by "
           "chapter")
    else:
        fail("the exercises: %r" % exs)
    if 7 in (index.get("ocr") or []):
        ok("the image-only page is OCR'd by gs")
    else:
        fail("page 7 was not OCR'd: %r" % index.get("ocr"))
    if has_ocr():
        if "Ends" in book.page_text(course, 7):
            ok("and its text is read off the picture")
        else:
            fail("OCR read nothing on page 7: %r" % book.page_text(course, 7))

    # ---- find --------------------------------------------------------------
    def found(ref):
        return book.find(course, ref)

    got = found("p. 3")
    if got.get("ok") and got["pdf_page"] == 4 and got["printed"] == 3:
        ok('"p. 3" is PDF page 4')
    else:
        fail('"p. 3": %r' % got)
    got = found("1.2")
    if got.get("ok") and got["kind"] == "exercise" and got["pdf_page"] == 4 \
            and "Prove the second thing" in got["text"] \
            and "Section 1.2" in " ".join(got.get("also") or []):
        ok('"1.2" is the exercise, its text, and names section 1.2 too')
    else:
        fail('"1.2": %r' % got)
    for ref, page in (("Section 1.2", 3), ("§2.1", 5), ("Ch 2 #2", 6),
                      ("Exercise 3.1", 8), ("Ch 3", 7)):
        got = found(ref)
        if not (got.get("ok") and got["pdf_page"] == page):
            fail("%r should be PDF page %d: %r" % (ref, page, got))
            break
    else:
        ok('"Section 1.2", "§2.1", "Ch 2 #2", "Exercise 3.1" and "Ch 3" find '
           "their pages")
    for ref in ("Exercise 9.9", "p. 400", "Section 4.1", "#3", "what"):
        got = found(ref)
        if got.get("ok") or "not indexed" not in got.get("error", ""):
            fail("%r should be \"not indexed\": %r" % (ref, got))
            break
    else:
        ok("what the index does not hold is \"not indexed\", never guessed")

    # ---- --write, then split and scaffold ------------------------------
    p = board(["textbook", "ingest", "Booked", "--write"], base)
    tsv = open(os.path.join(course, "chapters.tsv")).read()
    if p.returncode == 0 and "03\t7\t8\tthe-end\tEnds" in tsv \
            and tsv.startswith("# the owner's comment"):
        ok("--write rewrites the rows from the book, keeping the table's "
           "comment and slugs")
    else:
        fail("ingest --write: %s\n%s" % (p.stdout, tsv))
    reading = os.path.join(course, "chapters", "ch03-the-end", "reading", "ch03.pdf")
    notes = os.path.join(course, "chapters", "ch01-beginnings", "notes",
                         "ch01-notes.tex")
    hw = os.path.join(course, "chapters", "ch02-middles", "homework",
                      "ch02-homework.tex")
    if os.path.isfile(reading) and pages(reading) in (None, 2) \
            and os.path.isfile(notes) and os.path.isfile(hw):
        ok("then split cuts the readings and scaffold --chapter-homework "
           "writes the .tex files")
    else:
        fail("split or scaffold did not run: %s" % p.stdout)
    got = found("Ch 2 #2")
    if got.get("reading") == os.path.join("chapters", "ch02-middles", "reading",
                                          "ch02.pdf") and got["reading_page"] == 2:
        ok("find names the reading excerpt and the page in it")
    else:
        fail("the reading of Ch 2 #2: %r" % got)
    p = board(["textbook", "find", "courses/Booked", "Exercise 1.3", "--json"], base)
    try:
        said = json.loads(p.stdout)
    except ValueError:
        said = []
    if p.returncode == 0 and said and said[0].get("pdf_page") == 4:
        ok("board textbook find --json answers with the record")
    else:
        fail("board textbook find --json: %s" % p.stdout)
    p = board(["textbook", "status", "courses/Booked"], base)
    if p.returncode == 0 and "chapters.tsv: same" in p.stdout \
            and "3 chapters, 3 sections, 6 exercises" in p.stdout:
        ok("board textbook status: the counts, and the table matches")
    else:
        fail("board textbook status: %s" % p.stdout)

    # ---- a sheet --------------------------------------------------------------
    sheet = os.path.join(made, "sheet.pdf")
    put(os.path.join(made, "sheet.ps"), "%!PS\n" + ps_page(
        ["Homework 1", "Exercises 1.2 and 2.1, and Section 1.1.",
         "From chapter 2:", "1, 2"]))
    gs("pdfwrite", sheet, os.path.join(made, "sheet.ps"))
    labels = [g.get("label") or g.get("ref") for g in book.sheet(course, sheet, 2)]
    if labels[:3] == ["Exercise 1.2", "Exercise 2.1", "Section 1.1 First things"] \
            and "Exercise 2.1" in labels[3:] and "Exercise 2.2" in labels[3:]:
        ok("--sheet resolves each reference on an assignment sheet, and a "
           "bare list by the chapter given")
    else:
        fail("the sheet's references: %r" % labels)

    hw = os.path.join(made, "hw.pdf")
    put(os.path.join(made, "hw.ps"), "%!PS\n" + ps_page(
        ["Homework 2", "Chapter 1, problems 1, 2 and 3.",
         "Ch. 2 exercises 1, 2", "Problem 7 from the notes."]))
    gs("pdfwrite", hw, os.path.join(made, "hw.ps"))
    p = board(["textbook", "find", "courses/Booked", "--sheet", hw, "--json"], base)
    try:
        said = json.loads(p.stdout)
    except ValueError:
        said = []
    labels = [g.get("label") for g in said if g.get("ok")]
    if p.returncode == 1 and labels == ["Exercise 1.1", "Exercise 1.2", "Exercise 1.3",
                                        "Exercise 2.1", "Exercise 2.2"] \
            and [g["ref"] for g in said if not g.get("ok")] == ["Problem 7 from the notes."]:
        ok("--sheet resolves every number of a chapter's list, and exits 1 on "
           "the line it could not read")
    else:
        fail("--sheet on a list: %d %s" % (p.returncode, p.stdout))
    env = dict(os.environ, TUTORBOARD_COURSES=base)
    p = subprocess.run([sys.executable, CLI, "textbook", "find", "Section", "1.2"],
                       cwd=course, env=env, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, universal_newlines=True)
    if p.returncode == 0 and p.stdout.startswith("Section 1.2 Second things: PDF page 3"):
        ok("an unquoted reference is a reference, in the course it runs in")
    else:
        fail("find Section 1.2, unquoted: %d %s" % (p.returncode, p.stdout))

    # ---- the brief and the homework sense ---------------------------------
    line = brief_mod.book_sense(course)
    if "board textbook find <ref>" in line:
        ok("the brief's book line names board textbook find")
    else:
        fail("the book line: %r" % line)
    said = sense_mod._sheet_refs(course, "homework/hw01/assignment/s.pdf")
    if "board textbook find --sheet homework/hw01/assignment/s.pdf" in said \
            and sense_mod._sheet_refs(base, "x.pdf") == "":
        ok("the homework sense asks for find --sheet only where there is an index")
    else:
        fail("the homework sense: %r" % said)

    # ---- no outline -------------------------------------------------------
    plain = os.path.join(base, "courses", "Plain")
    os.makedirs(os.path.join(plain, "textbook"))
    shutil.copyfile(plain_book(made), os.path.join(plain, "textbook", "Plain.pdf"))
    p = board(["textbook", "ingest", "courses/Plain"], base)
    index = book.read(plain) or {}
    rows = [(c["num"], c["first"], c["last"]) for c in index.get("chapters") or []]
    doubts = " ".join(index.get("doubts") or [])
    if p.returncode == 0 and rows == [("01", 1, 2), ("02", 3, 4), ("03", 5, 6)] \
            and doubts.count("the PDF has no outline") == 3:
        ok("with no outline the chapters are read off the page text, each a doubt")
    else:
        fail("no outline: %r %r\n%s" % (rows, doubts, p.stdout))
    tsv = open(os.path.join(plain, "chapters.tsv")).read() \
        if os.path.isfile(os.path.join(plain, "chapters.tsv")) else ""
    if "02\t3\t4\tmiddles\tMiddles" in tsv and os.path.isfile(os.path.join(
            plain, "chapters", "ch02-middles", "reading", "ch02.pdf")):
        ok("an absent chapters.tsv is written, and the book is split by it")
    else:
        fail("chapters.tsv was not written and split: %r" % tsv)
    if "not indexed" in book.find(plain, "p. 2").get("error", ""):
        ok("a book with no printed numbers leaves a page reference not indexed")
    else:
        fail("p. 2 in a book with no page numbers: %r" % book.find(plain, "p. 2"))

    # ---- an upload --------------------------------------------------------
    fresh = os.path.join(base, "courses", "Fresh")
    os.makedirs(fresh)
    p = board(["textbook", "ingest", "courses/Fresh", "--upload", pdf, "--check"], base)
    if p.returncode == 0 and os.path.isfile(pdf) \
            and os.path.isfile(os.path.join(fresh, "textbook", "book.pdf")):
        ok("--upload <path> files a copy into textbook/ and indexes it")
    else:
        fail("ingest --upload: %s" % p.stdout)
    p = board(["textbook", "ingest", "courses/Fresh", "--upload",
               os.path.join(made, "plain.pdf"), "--check"], base)
    if p.returncode == 1 and "second, different PDF" in p.stdout:
        ok("a second, different PDF is refused")
    else:
        fail("a second textbook was not refused: %s" % p.stdout)
    dup = os.path.join(made, "again.pdf")
    shutil.copyfile(pdf, dup)
    try:
        got = book.file_upload(fresh, dup)
        same = got.endswith("book.pdf") and not os.path.exists(dup)
    except book.Refused:
        same = False
    if same and book.pdfs(fresh) == [os.path.join(fresh, "textbook", "book.pdf")]:
        ok("the same PDF again is not a second one")
    else:
        fail("the same PDF again was refused or kept twice")

    # ---- the server's Ingester and its [textbook] line ---------------------
    woke = []

    def wait():
        for _ in range(600):
            if woke:
                return woke[-1]
            time.sleep(0.05)
        return None

    worker = route.Ingester(run=lambda root: book.ingest(root, split=False),
                            wake=lambda root, sid, line: woke.append((root, sid, line)))
    worker.start()
    shutil.rmtree(os.path.join(fresh, "textbook", "text"))
    worker.submit(fresh, "s1")
    got = wait()
    line = got[2] if got else ""
    if got and got[1] == "s1" and line.startswith("[textbook] book.pdf is indexed") \
            and "3 chapters, 3 sections, 6 exercises" in line \
            and "Solutions to Exercises" in line and "TUTOR.md" in line \
            and not worker.running(fresh):
        ok("the Ingester wakes the asking session with the [textbook] line: "
           "counts, doubts and what to do")
    else:
        fail("the [textbook] line: %r" % (got,))
    prog = book.progress(fresh) or {}
    if prog.get("state") == "done":
        ok("and textbook/ingest.json says the run is done")
    else:
        fail("ingest.json: %r" % prog)
    del woke[:]

    def broken(root):
        raise book.Refused("pdfinfo cannot read it")
    worker.run_one = broken
    worker.submit(fresh, "s2")
    got = wait()
    if got and "failed: pdfinfo cannot read it" in got[2]:
        ok("a failed run wakes it too, saying why")
    else:
        fail("a failed run: %r" % (got,))


def rules_suite(base):
    """The reading rules on text alone: running headers, a misread number,
    a sentence starting "index", a bare N.M, page 0 and ranges, the
    phrasings assignment sheets use, a timeout, and two filings at once."""
    import threading
    from tutorboard.course import book
    from tutorboard.server.routes import textbook as route

    c = {"num": "12", "first": 1, "last": 3, "title": "Finite fields"}
    secs = [{"num": "12.4", "chapter": "12", "title": "The multiplicative group",
             "page": 1}]
    text = [
        "12.4 The multiplicative group\n\n   Exercises\n   12.1 One.\n"
        "   12.2 Two, and the index of H in G.)\n",
        "          12.4. The multiplicative group of a finite field          105\n"
        "\n   12.3 Three.\n   12.4 Four.\n   12.5 Five.\n   12.9 Six, misread.\n",
        "106        Finite fields\n   12.7 Seven.\n   12.8 Eight.\n   12.9 Nine.\n",
    ]
    doubts = []
    got = [(e["label"], e["page"]) for e in book.exercises(c, text, secs, doubts)]
    if got == [("12.1", 1), ("12.2", 1), ("12.3", 2), ("12.4", 2), ("12.5", 2),
               ("12.7", 3), ("12.8", 3), ("12.9", 3)]:
        ok("exercises run on past a page's running header, past a sentence "
           "about an index, and past a misread number")
    else:
        fail("the exercises across a page turn: %r" % got)
    if len(doubts) == 1 and "12.6 not read" in doubts[0] \
            and "12.9 (page 2)" in doubts[0]:
        ok("and the number skipped is a doubt, naming the one read out of "
           "sequence there")
    else:
        fail("the doubts of a misread number: %r" % doubts)

    root = os.path.join(base, "rules")
    put(os.path.join(root, "textbook", "index.json"), json.dumps({
        "pages": 6, "labels": [{"first": 1, "last": 6, "offset": 1}],
        "chapters": [{"num": "08", "first": 1, "last": 6, "title": "Closures"}],
        "sections": [{"num": "8.2", "chapter": "08", "title": "Existence",
                      "page": 3, "source": "outline"}],
        "exercises": [{"chapter": "08", "n": 1, "label": "8.1", "page": 4,
                       "line": 0, "starred": False}]}))
    got = book.find(root, "8.2")
    if not got.get("ok") and "not indexed" in got["error"] \
            and "Section 8.2" in got["error"]:
        ok('a bare "8.2" with no exercise 8.2 is not indexed, naming the '
           "section rather than answering with it")
    else:
        fail('"8.2" with only a section 8.2: %r' % got)
    got = book.find(root, "p. 0")
    if not got.get("ok") and "not indexed" in got["error"]:
        ok('"p. 0" is not indexed')
    else:
        fail('"p. 0": %r' % got)
    got = book.find(root, "pp. 2-4")
    if got.get("ok") and got["pdf_page"] == 3 and got["pdf_last"] == 5:
        ok('"pp. 2-4" is PDF pages 3 to 5')
    else:
        fail('"pp. 2-4": %r' % got)

    sheet = ("Practice.\nChapter 1, problems 4, 5, 6, 7 and 17. (Do not hand in "
             "practice problems.)\n\n1. Let E and F be events.\n"
             "And work the following problems from the text:\n"
             "8. (Bonferroni\u2019s inequality), 10. (Boole\u2019s inequality), "
             "12, 39 and 41.\n"
             "Ch. 1 exercises 8, 10, 12, 39, 41\nChapter 4: 1, 7, 9 or 10\n"
             "Read pp. 12-15.\nProblem 7 from the notes.\n")
    refs, bare, named, unread = book.sheet_refs(sheet)
    want = (["Ch 1 #%d" % n for n in (4, 5, 6, 7, 17, 8, 10, 12, 39, 41)]
            + ["Ch 4 #%d" % n for n in (1, 7, 9, 10)] + ["pp. 12-15"])
    if refs == want and bare == [8, 10, 12, 39, 41] and named == [1, 4] \
            and unread == ["Problem 7 from the notes."]:
        ok("a sheet's lists are read whole: \"problems 4, 5 and 17\", "
           "\"Chapter 4: 1, 7, 9 or 10\", a bare list with notes beside it, "
           "\"pp. 12-15\"; a line naming a problem it cannot read is kept")
    else:
        fail("the sheet's references: %r %r %r %r" % (refs, bare, named, unread))

    try:
        book._run([sys.executable, "-c", "import time; time.sleep(5)"], timeout=1)
        timed = False
    except book.Refused as exc:
        timed = "gave up after 1 seconds" in str(exc)
    if timed:
        ok("a tool that hangs is Refused, in words, not a traceback")
    else:
        fail("a hung tool was not Refused")

    twice = 0
    for k in range(10):
        course = os.path.join(base, "race", str(k))
        ups = []
        for name in ("a.pdf", "b.pdf"):
            put(os.path.join(base, "race-up", str(k), name), "%PDF " + name)
            ups.append(os.path.join(base, "race-up", str(k), name))
        gate = threading.Barrier(2)

        def one(path):
            gate.wait()
            try:
                book.file_upload(course, path)
            except book.Refused:
                pass
        runs = [threading.Thread(target=one, args=(u,)) for u in ups]
        for t in runs:
            t.start()
        for t in runs:
            t.join()
        twice += len(book.pdfs(course)) != 1
    if not twice:
        ok("two filings at once into one course land one PDF, every time")
    else:
        fail("two filings at once left two PDFs %d time(s) in 10" % twice)
    work = route.Ingester(run=lambda root: None, wake=lambda *a: None)
    if work.claim(root) and not work.claim(root) and work.running(root):
        work.release(root)
        if work.claim(root):
            ok("the Ingester claims a course before filing, and a second "
               "claim is refused")
        else:
            fail("a released claim could not be made again")
    else:
        fail("the Ingester's claim is not exclusive")


def server_suite(base):
    """`POST /s/<id>/textbook` on a real server: filed, indexed on the
    Ingester, and the session woken with the `[textbook]` line."""
    import http.client
    import threading
    from tutorboard import sessions
    from tutorboard.server import app

    course = os.path.join(base, "courses", "Served")
    put(os.path.join(course, "tutorboard.json"), '{"name": "Served", "phi": false}')
    sid = sessions.new(title="Served: the book", base=base)["id"]
    sessions.bind(sid, "courses/Served", base=base)
    where = sessions.path(sid, base)
    os.makedirs(os.path.join(where, "uploads"), exist_ok=True)
    shutil.copyfile(os.path.join(base, "made", "book.pdf"),
                    os.path.join(where, "uploads", "Book.pdf"))
    shutil.copyfile(os.path.join(base, "made", "plain.pdf"),
                    os.path.join(where, "uploads", "Other.pdf"))
    httpd = app.make_server(base, 0, start=False)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    def ask(method, path, body=None):
        conn = http.client.HTTPConnection("127.0.0.1", httpd.server_port, timeout=30)
        data = json.dumps(body).encode("utf-8") if body is not None else None
        conn.request(method, path, body=data,
                     headers={"Content-Type": "application/json"} if data else {})
        r = conn.getresponse()
        got = json.loads(r.read().decode("utf-8") or "{}")
        conn.close()
        return r.status, got

    def woken():
        try:
            with open(os.path.join(where, "inbox", "messages.jsonl")) as fh:
                lines = [json.loads(l) for l in fh if l.strip()]
        except OSError:
            return []
        return [m for m in lines if m.get("signal") == "textbook"]

    try:
        status, got = ask("GET", "/textbook.json?subject=courses/Served")
        if status == 200 and got.get("course") and not got.get("indexed") \
                and got.get("pdfs") == []:
            ok("GET /textbook.json: a course with no book yet")
        else:
            fail("GET /textbook.json before: %d %r" % (status, got))
        status, got = ask("POST", "/s/%s/textbook" % sid, {"upload": "Book.pdf"})
        if status == 200 and got.get("started") and got.get("pdf") == "Book.pdf":
            ok("POST /s/<id>/textbook files the upload and starts the index")
        else:
            fail("POST /textbook: %d %r" % (status, got))
        lines = []
        for _ in range(600):
            lines = woken()
            if lines:
                break
            time.sleep(0.05)
        line = lines[0] if lines else {}
        if line.get("text", "").startswith("[textbook] Book.pdf is indexed") \
                and line.get("wake") is not False and line.get("session") == sid:
            ok("and the session is woken with the [textbook] line when it ends")
        else:
            fail("no [textbook] line: %r" % lines)
        if os.path.isfile(os.path.join(course, "chapters.tsv")) and os.path.isfile(
                os.path.join(course, "chapters", "ch01-beginnings", "reading",
                             "ch01.pdf")) \
                and not os.path.exists(os.path.join(where, "uploads", "Book.pdf")):
            ok("chapters.tsv is written, the readings cut, and the upload moved")
        else:
            fail("the served ingest left no chapters.tsv or readings")
        status, got = ask("GET", "/s/%s/textbook.json" % sid)
        if status == 200 and got.get("indexed") and got.get("chapters") == 3:
            ok("GET /s/<id>/textbook.json: the session's course, indexed")
        else:
            fail("GET /textbook.json after: %d %r" % (status, got))
        status, got = ask("POST", "/s/%s/textbook" % sid, {"upload": "Other.pdf"})
        if status == 409 and "second, different PDF" in got.get("error", ""):
            ok("a second, different book is 409")
        else:
            fail("a second book: %d %r" % (status, got))
        other = sessions.new(title="unbound", base=base)["id"]
        status, got = ask("POST", "/s/%s/textbook" % other, {"upload": "x.pdf"})
        if status == 400 and "course" in got.get("error", ""):
            ok("a session bound to no course is refused")
        else:
            fail("an unbound session: %d %r" % (status, got))
    finally:
        httpd.shutdown()
        httpd.server_close()


if not shutil.which("gs"):
    print("skip  ghostscript (gs) is not installed; `board textbook split` "
          "needs it")
    sys.exit(0)

base = os.path.realpath(tempfile.mkdtemp(prefix="tutor-textbook-"))
# The in-process server and the engine keep their state in the temp tree.
for name, sub in (("BOARD_STATE_DIR", ".state"), ("TUTORBOARD_TRASH", ".trash"),
                  ("XDG_CONFIG_HOME", ".config"), ("TUTORBOARD_PAGES", ".pages")):
    os.environ[name] = os.path.join(base, sub)
os.environ["TUTORBOARD_COURSES"] = base
os.environ.pop("TUTORBOARD_SESSION", None)
try:
    course = fixture(base)
    if pages(os.path.join(course, "textbook", "Book.pdf")) not in (None, 6):
        fail("the fixture textbook is not 6 pages")

    # ---- split, by subject id -------------------------------------------
    p = board(["textbook", "split", "courses/Fixture"], base)
    want = {"ch01-beginnings": 2, "ch02-middles": 1, "ch03-ends": 3}
    got = {}
    for d, n in want.items():
        pdf = os.path.join(course, "chapters", d, "reading",
                           d.split("-")[0] + ".pdf")
        got[d] = pages(pdf) if os.path.isfile(pdf) else 0
    if p.returncode != 0:
        fail("board textbook split failed: %s" % p.stdout)
    elif any(got[d] == 0 for d in want):
        fail("a chapter reading is missing: %r\n%s" % (got, p.stdout))
    elif any(got[d] is not None and got[d] != n for d, n in want.items()):
        fail("the readings have the wrong page counts: %r" % got)
    else:
        ok("board textbook split writes chapters/chNN-slug/reading/chNN.pdf "
           "for each of 3 chapters, by the page ranges in chapters.tsv")
    if "3 chapter excerpt(s) written." not in p.stdout:
        fail("split did not say how many it wrote: %s" % p.stdout)
    if not os.path.isdir(os.path.join(base, "live")) and \
            not os.path.isdir(os.path.join(course, "live")):
        ok("and makes no live/ anywhere")
    else:
        fail("board textbook made a live/ directory")

    # ---- split one chapter, by path, under the Mac's bash 3.2 -----------
    shutil.rmtree(os.path.join(course, "chapters"))
    for bash in ("bash", "/bin/bash"):
        if bash.startswith("/") and not os.path.exists(bash):
            continue
        p = subprocess.run([bash, os.path.join(SCRIPTS, "split-textbook.sh"),
                            course, "2"], stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, universal_newlines=True)
        made = sorted(os.listdir(os.path.join(course, "chapters"))) \
            if os.path.isdir(os.path.join(course, "chapters")) else []
        if p.returncode == 0 and made == ["ch02-middles"]:
            ok("%s: split with a chapter number cuts only that chapter" % bash)
        else:
            fail("%s: split 2 made %r: %s" % (bash, made, p.stdout))
        shutil.rmtree(os.path.join(course, "chapters"), ignore_errors=True)

    # ---- two PDFs in textbook/ is refused --------------------------------
    shutil.copyfile(os.path.join(course, "textbook", "Book.pdf"),
                    os.path.join(course, "textbook", "Other.pdf"))
    p = board(["textbook", "split", course], base)
    if p.returncode != 0 and "exactly one PDF" in p.stdout:
        ok("a textbook/ with two PDFs is refused, by name")
    else:
        fail("two textbook PDFs were not refused: %s" % p.stdout)
    os.remove(os.path.join(course, "textbook", "Other.pdf"))

    # ---- scaffold: chapters, chapter homework, numbered sets -------------
    for bash in ("bash", "/bin/bash"):
        if bash.startswith("/") and not os.path.exists(bash):
            continue
        shutil.rmtree(os.path.join(course, "chapters"), ignore_errors=True)
        shutil.rmtree(os.path.join(course, "homework"), ignore_errors=True)
        script = os.path.join(SCRIPTS, "scaffold.sh")
        p = subprocess.run([bash, script, course], stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, universal_newlines=True)
        notes = os.path.join(course, "chapters", "ch03-ends", "notes",
                             "ch03-notes.tex")
        body = notes
        if p.returncode == 0 and \
                titled(notes, "Chapter 03 notes — Ends, and what follows") and \
                os.path.isfile(os.path.join(course, "chapters", "ch01-beginnings",
                                            "handwritten", ".gitkeep")) and \
                not os.path.exists(os.path.join(course, "chapters", "ch01-beginnings",
                                                "homework")):
            ok("%s: scaffold writes each chapter's notes from "
               "board/tex/writeup.tex.in" % bash)
        else:
            fail("%s: scaffold did not write the notes: %r %s"
                 % (bash, body, p.stdout))
        put(notes, "the owner's mathematics\n")
        p = subprocess.run([bash, script, course, "--chapter-homework", "3"],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           universal_newlines=True)
        hw = os.path.join(course, "chapters", "ch03-ends", "homework",
                          "ch03-homework.tex")
        if p.returncode == 0 and open(notes).read() == \
                "the owner's mathematics\n" and \
                titled(hw, "Chapter 03 homework — Ends, and what follows") and \
                not os.path.exists(os.path.join(course, "chapters",
                                                "ch01-beginnings", "homework")):
            ok("%s: --chapter-homework adds chNN-homework.tex and never "
               "overwrites a .tex" % bash)
        else:
            fail("%s: --chapter-homework went wrong: %s" % (bash, p.stdout))
        p = subprocess.run([bash, script, course, "--hw", "4"],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           universal_newlines=True)
        hw4 = os.path.join(course, "homework", "hw04", "hw04.tex")
        if p.returncode == 0 and titled(hw4, "Homework 04"):
            ok("%s: --hw 4 makes homework/hw04/hw04.tex" % bash)
        else:
            fail("%s: --hw 4 went wrong: %s" % (bash, p.stdout))

    p = board(["textbook", "scaffold", "Fixture", "1"], base)
    if p.returncode == 0 and "keep" in p.stdout:
        ok("board textbook scaffold finds a course by its slug")
    else:
        fail("board textbook scaffold Fixture: %s" % p.stdout)

    p = board(["textbook", "split", "courses/Nothing"], base)
    if p.returncode != 0 and "no course" in p.stdout:
        ok("an unknown course is refused")
    else:
        fail("an unknown course was not refused: %s" % p.stdout)

    rules_suite(base)
    if shutil.which("pdftohtml") and shutil.which("pdftotext"):
        index_suite(base)
        server_suite(base)
    else:
        print("skip  poppler (pdftohtml, pdftotext) is not installed; "
              "`board textbook ingest` needs it")
finally:
    shutil.rmtree(base, ignore_errors=True)

print()
if fails:
    print("%d failure(s)" % len(fails))
    sys.exit(1)
print("board textbook: all good")
