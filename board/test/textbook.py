#!/usr/bin/env python3
"""`board textbook split` and `board textbook scaffold`, on a fixture course.

    python3 test/textbook.py

A temp tree holds courses/Fixture with a 6-page textbook PDF (made by gs from
PostScript, so no TeX is needed), a 3-chapter chapters.tsv and the two
templates. The scripts also run under /bin/bash where it is the Mac's 3.2.
"""

import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = os.path.dirname(HERE)
CLI = os.path.join(BOARD, "bin", "board")
SCRIPTS = os.path.join(BOARD, "scripts")

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
NOTES = "\\section*{Chapter @@NUM@@: @@TITLE@@ notes}\n"
HOMEWORK = "\\section*{@@TITLE@@ (@@NUM@@)}\n"


def fixture(base):
    course = os.path.join(base, "courses", "Fixture")
    put(os.path.join(course, "chapters.tsv"), TSV)
    put(os.path.join(course, "latex", "templates", "notes.tex.in"), NOTES)
    put(os.path.join(course, "latex", "templates", "homework.tex.in"),
        HOMEWORK)
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


if not shutil.which("gs"):
    print("skip  ghostscript (gs) is not installed; `board textbook split` "
          "needs it")
    sys.exit(0)

base = tempfile.mkdtemp(prefix="tutor-textbook-")
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
        try:
            body = open(notes, encoding="utf-8").read()
        except OSError:
            body = ""
        if p.returncode == 0 and body == \
                "\\section*{Chapter 03: Ends, and what follows notes}\n" and \
                os.path.isfile(os.path.join(course, "chapters", "ch01-beginnings",
                                            "handwritten", ".gitkeep")) and \
                not os.path.exists(os.path.join(course, "chapters", "ch01-beginnings",
                                                "homework")):
            ok("%s: scaffold writes each chapter's notes from the template"
               % bash)
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
                "the owner's mathematics\n" and os.path.isfile(hw) and \
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
        if p.returncode == 0 and os.path.isfile(hw4) and \
                open(hw4).read() == "\\section*{Homework 04 (04)}\n":
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
finally:
    shutil.rmtree(base, ignore_errors=True)

print()
if fails:
    print("%d failure(s)" % len(fails))
    sys.exit(1)
print("board textbook: all good")
