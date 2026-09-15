#!/usr/bin/env python3
"""Writing on a compiled document, kept as a document.

The pen over a page of a PDF already worked and the ink already survived a
reload. What it could not do was leave: it lived in `live/annotations/`, which
is the board's drawer, and a drawer is not something you hand to anybody.

Three ways out, because there are three things "save" means, and the middle one
is the only one that is obvious:

    same      over the PDF being viewed
    new       a new file beside it
    none      no file at all, marks left in the drawer

What is guarded here is the arithmetic, not the appearance. A burn that puts
page 3's ink on page 1 looks completely fine until it is read -- so the page
ORDER is checked against a document whose pages can be told apart, and it is
checked because the first version of this got it wrong: the renderer names its
output `page-1.jpg` and `paper.py`'s page-number helper matches `.png`, so every
page sorted equal and came back in directory order.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tutorboard.course import burn                                   # noqa: E402
from tutorboard.course import paper                                  # noqa: E402
from tutorboard.server.routes import writing                         # noqa: E402

fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


class Repo(object):
    """Just enough of a repository for the burner: a root, a notes dir, state."""

    def __init__(self, root):
        self.root = root
        self.live = os.path.join(root, "live")
        self.notes = os.path.join(self.live, "annotations")
        os.makedirs(self.notes, exist_ok=True)

    def state(self):
        return {"course": "Test Course", "hw": "homework/hw01/hw01.tex"}


def stroke(y, colour="#e0b45c", w=2.4):
    """A short scrawl across the page at height `y`, in box fractions."""
    p, pr = [], []
    for i in range(24):
        t = i / 23.0
        p += [0.15 + 0.6 * t, y + 0.01 * ((-1) ** i)]
        pr.append(0.4 + 0.5 * t)
    return {"c": colour, "w": w, "p": p, "pr": pr}


def make_pdf(path, pages):
    """A real multi-page PDF, built with whatever this machine compiles with."""
    tex = ["\\documentclass{article}", "\\begin{document}"]
    for i, word in enumerate(pages):
        if i:
            tex.append("\\newpage")
        tex.append("\\Huge %s" % word)
    tex.append("\\end{document}")
    work = tempfile.mkdtemp(prefix="burn-tex-")
    src = os.path.join(work, "doc.tex")
    with open(src, "w", encoding="utf-8") as fh:
        fh.write("\n".join(tex))
    env = paper.raster_env()
    try:
        subprocess.run(["pdflatex", "-interaction=nonstopmode", "doc.tex"],
                       cwd=work, env=env, timeout=180,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    except (OSError, subprocess.SubprocessError):
        shutil.rmtree(work, ignore_errors=True)
        return False
    built = os.path.join(work, "doc.pdf")
    if not os.path.isfile(built):
        shutil.rmtree(work, ignore_errors=True)
        return False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    shutil.copy(built, path)
    shutil.rmtree(work, ignore_errors=True)
    return True


def page_text(pdf, n):
    """The words on page `n`, for telling one page from another."""
    try:
        p = subprocess.run(["pdftotext", "-f", str(n), "-l", str(n), pdf, "-"],
                           stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                           timeout=120)
        return p.stdout.decode("utf-8", "replace")
    except (OSError, subprocess.SubprocessError):
        return ""


tmp = tempfile.mkdtemp(prefix="tutor-burn-")
try:
    # ---- the arithmetic, which needs no files ------------------------------
    #
    # Ink is stored in fractions of the page box, counted from the TOP, and a
    # PDF counts from the bottom. Getting this backwards puts a mark about the
    # first line of a proof next to the last one, on a page that still looks
    # plausible.
    ops = burn._ink_ops([{"c": "#ff0000", "w": 2.0,
                          "p": [0.0, 0.0, 1.0, 1.0], "pr": [0.5, 0.5]}],
                        100.0, 200.0).decode("latin-1")
    check("a mark at the top of the box is at the top of the page",
          "0.000 200.000 m" in ops)
    check("and one at the bottom is at the bottom",
          "100.000 0.000 l" in ops)
    check("the page is clipped, so ink outside it does not spill",
          " re W n" in ops)
    check("a colour survives as a PDF colour", "1.0000 0.0000 0.0000 RG" in ops)

    check("an unreadable colour falls back to the pen's rather than crashing",
          burn._rgb("nonsense") == burn._rgb("#e0b45c"))

    # A single point is a dot, and a zero-length line paints nothing in some
    # readers -- so it has to come out as a filled shape, not a stroked one.
    dot = burn._ink_ops([{"c": "#e0b45c", "w": 3.0, "p": [0.5, 0.5],
                          "pr": [0.9]}], 100.0, 100.0).decode("latin-1")
    check("a single tap is drawn as a filled dot", dot.rstrip().endswith("f\nQ"))

    check("pages sort by their number and not by their name",
          [os.path.basename(x) for x in sorted(
              ["/t/page-10.jpg", "/t/page-2.jpg", "/t/page-1.jpg"],
              key=burn._page_number)]
          == ["page-1.jpg", "page-2.jpg", "page-10.jpg"])

    check("a mode nobody offers is refused",
          burn.burn(Repo(tmp), "homework", "clobber").get("why") == "bad-mode")

    # ---- a real document ---------------------------------------------------
    root = os.path.join(tmp, "course")
    repo = Repo(root)
    with open(os.path.join(root, "tutorboard.json"), "w", encoding="utf-8") as fh:
        fh.write('{"name": "T", "mode": "math"}')
    pdf = os.path.join(root, "homework", "hw01", "hw01.pdf")
    built = make_pdf(pdf, ["ALPHA", "BETA", "GAMMA"])

    if not built or not paper.renderer():
        print("\n-- no LaTeX or no rasteriser on this machine; the rest is skipped")
        print("the ink can be kept" if not fails else "%d FAILURES" % len(fails))
        sys.exit(1 if fails else 0)

    with open(os.path.join(repo.live, "hw.json"), "w", encoding="utf-8") as fh:
        json.dump({"ok": True, "set": "hw01", "pdf": "homework/hw01/hw01.pdf"}, fh)

    target, stem = burn.target_for(repo, "homework")
    check("the built write-up is found", target == os.path.realpath(pdf))
    check("and named after the file", stem == "hw01")
    check("a kind nobody offers resolves to nothing",
          burn.target_for(repo, "doc/../../etc")[0] is None)

    # ---- nothing written on it yet -----------------------------------------
    got = burn.burn(repo, "homework", "new")
    check("a clean document says so rather than writing an empty copy",
          got["ok"] is False and got["why"] == "no-ink")

    # ---- ink on page 2 ONLY, which is the case that catches a bad sort ------
    key = "doc/homework/p2"
    with open(os.path.join(repo.notes, writing.ann_file(key) + ".json"),
              "w", encoding="utf-8") as fh:
        json.dump({"card": key, "strokes": [stroke(0.40)], "sent": False}, fh)

    marks = burn.strokes_by_page(repo, "homework", 3)
    check("the marks are read back off the key the viewer wrote",
          list(marks) == [2] and len(marks[2]) == 1)

    # ---- not saving is a real answer, and costs nothing ---------------------
    before = sorted(os.listdir(os.path.dirname(pdf)))
    got = burn.burn(repo, "homework", "none")
    check("choosing not to save reports success", got["ok"] and got["mode"] == "none")
    check("and writes no file at all",
          sorted(os.listdir(os.path.dirname(pdf))) == before)
    check("and leaves the marks in the drawer",
          burn.strokes_by_page(repo, "homework", 3))

    # ---- a new file --------------------------------------------------------
    got = burn.burn(repo, "homework", "new", dpi=120)
    check("a new file is written", got["ok"] and got["mode"] == "new")
    fresh = os.path.join(os.path.dirname(pdf), got["name"])
    check("beside the original, which is untouched",
          os.path.isfile(fresh) and os.path.isfile(pdf))
    check("named for the document, annotated, and dated",
          got["name"].startswith("hw01-annotated-") and got["name"].endswith(".pdf"))
    check("with every page of the original, not just the marked one",
          got["pages"] == 3)

    # Two passes in one evening must not silently land on one file -- which is
    # the whole reason somebody picked "a new file" over "over the original".
    second = burn.burn(repo, "homework", "new", dpi=120)
    check("a second new file does not overwrite the first",
          second["ok"] and second["name"] != got["name"]
          and os.path.isfile(os.path.join(os.path.dirname(pdf), second["name"])))

    # ---- THE ORDER, which is what the first version got wrong ---------------
    check("page 1 of the burn is page 1 of the original",
          "ALPHA" in page_text(pdf, 1))
    check("a burned page carries no text layer, which is the cost of this route",
          page_text(fresh, 1).strip() == "")

    # So the order is checked against the pictures instead: three pages, and the
    # marked one is not the same picture as its neighbours.
    work = tempfile.mkdtemp(prefix="burn-check-")
    try:
        shots = burn._render_jpegs(fresh, work, dpi=72)
        check("the burn has three pages on disk", len(shots) == 3)
        sizes = [os.path.getsize(s) for s in shots]
        check("and the marked page is not the same picture as the others",
              len(shots) == 3 and sizes[1] != sizes[0])
    finally:
        shutil.rmtree(work, ignore_errors=True)

    # ---- over the original -------------------------------------------------
    was = os.path.getsize(pdf)
    got = burn.burn(repo, "homework", "same", dpi=120)
    check("the original can be written over", got["ok"] and got["mode"] == "same")
    check("and it is the same path, changed",
          os.path.isfile(pdf) and os.path.getsize(pdf) != was)
    check("the write-up still has all three pages",
          got["pages"] == 3)

    # The point of it being safe: the strokes are NOT in the PDF. A compile that
    # rewrites the file has not taken the writing with it, because the writing
    # was never in the file.
    check("the marks are still in the drawer after an overwrite",
          burn.strokes_by_page(repo, "homework", 3))
    make_pdf(pdf, ["ALPHA", "BETA", "GAMMA"])
    again = burn.burn(repo, "homework", "same", dpi=120)
    check("so a recompiled document can be written over again, unchanged",
          again["ok"] and again["pages"] == 3)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print()
print("%d FAILURES" % len(fails) if fails else "writing on a document can be kept")
sys.exit(1 if fails else 0)
