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
import re
import os
import shutil
import subprocess
import sys
import tempfile
import time

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


def library_section(tmp):
    """A MARKED COPY OF A LIBRARY DOCUMENT, through the real routes.

    The owner's ask: *save my markups without overwriting the original paper*.
    So `library/<id>` burns `new` and nothing else, into `live/marked/<id>/` --
    which the library does not walk and git does not carry -- and keeping a copy
    delivers nothing: the ink still goes with the next note.
    """
    import socket
    import threading
    import urllib.error
    import urllib.request
    from http.server import ThreadingHTTPServer

    from tutorboard.course import library
    from tutorboard.course import repo as course_repo
    from tutorboard.server import handler
    from tutorboard.server import hub
    from tutorboard.server import tikz

    ws = os.path.join(tmp, "workspace")
    os.makedirs(ws)
    with open(os.path.join(ws, "tutorboard.json"), "w", encoding="utf-8") as fh:
        fh.write('{"name": "W", "mode": "research"}')
    # A repository with NO rule for `live/`, so the only thing keeping a copy
    # out of git is the copy's own directory.
    subprocess.run(["git", "init", "-q", ws], stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL)
    lrepo = course_repo.Repo(ws)
    here = os.path.join(ws, "writeups", "notes")
    pdf = os.path.join(here, "notes.pdf")
    if not make_pdf(pdf, ["ONE", "TWO", "THREE"]):
        check("a library document could be built", False)
        return
    with open(os.path.join(here, "notes.tex"), "w", encoding="utf-8") as fh:
        fh.write("\\documentclass{article}\\title{Notes}\n")
    os.utime(pdf, None)                     # the PDF is not older than its source

    worker = tikz.TikzWorker(lrepo)
    worker.start()
    board = hub.Hub(lrepo, worker)
    board.payload = json.dumps(board.build())
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), handler.Handler)
    httpd.daemon_threads = True
    httpd.repo = lrepo
    httpd.hub = board
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = "http://127.0.0.1:%d" % port

    def call(path, body=None):
        req = urllib.request.Request(
            base + path, method="POST" if body is not None else "GET",
            data=json.dumps(body).encode("utf-8") if body is not None else None,
            headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                raw = r.read()
                return r.status, raw, r.headers
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read(), exc.headers

    def js(path, body=None):
        status, raw, _h = call(path, body)
        try:
            return status, json.loads(raw.decode("utf-8"))
        except ValueError:
            return status, {}

    def ignored(path):
        return subprocess.run(["git", "-C", ws, "check-ignore", "-q", path],
                              stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL).returncode == 0

    try:
        library.forget()
        docs = library.documents(ws)
        check("the library offers the document", len(docs) == 1)
        ident = docs[0]["id"]
        with open(pdf, "rb") as fh:
            original = fh.read()
        mtime = os.stat(pdf).st_mtime_ns

        status, view = js("/library/view/" + ident)
        check("the pages come with the build they are drawn from",
              status == 200 and view.get("ok")
              and view["build"]["digest"] == view["digest"]
              and view["build"]["pages"] == 3 and view["build"]["at"] > 0)
        check("and nothing is flagged as drawn on another build yet",
              view.get("rebuilt") is None)

        status, got = js("/annotate/burn", {"kind": "library/" + ident,
                                            "mode": "new"})
        check("a copy of a clean document is refused, not written empty",
              status == 400 and got.get("why") == "no-ink")

        key = "doc/%s/p2" % ident
        status, _ = js("/annotate/save", {"card": key, "strokes": [stroke(0.4)],
                                          "build": view["build"]})
        rec_path = os.path.join(lrepo.notes, writing.ann_file(key) + ".json")
        with open(rec_path, "r", encoding="utf-8") as fh:
            rec = json.load(fh)
        check("a saved page is stamped with the build it was drawn on",
              status == 200 and rec.get("build", {}).get("digest") == view["digest"]
              and rec["build"]["pages"] == 3)
        js("/annotate/save", {"card": key, "strokes": [stroke(0.4)]})
        with open(rec_path, "r", encoding="utf-8") as fh:
            rec = json.load(fh)
        check("and a re-save of the same strokes naming no build keeps it",
              rec.get("build", {}).get("digest") == view["digest"])
        js("/annotate/save", {"card": key, "strokes": [stroke(0.4)],
                              "build": view["build"]})

        # ---- NO OVERWRITE FROM THE LIBRARY ---------------------------------
        for mode in ("same", "none"):
            status, got = js("/annotate/burn", {"kind": "library/" + ident,
                                                "mode": mode})
            check("a library document is never written over (%s is refused)" % mode,
                  status == 400 and got.get("why") == "no-overwrite")
        status, got = js("/annotate/burn", {"kind": "library/../../etc",
                                            "mode": "new"})
        check("an id that is not one is refused",
              status == 400 and got.get("why") == "none")

        # ---- A NEW FILE ----------------------------------------------------
        status, got = js("/annotate/burn", {"kind": "library/" + ident,
                                            "mode": "new"})
        copy = os.path.join(ws, *(got.get("path") or "x").split("/"))
        check("POST /annotate/burn with a library id writes a new file",
              status == 200 and got.get("ok") and os.path.isfile(copy))
        check("in live/marked/<id>/, never beside the document",
              (got.get("path") or "").startswith("live/marked/%s/" % ident))
        check("with every page of the document", got.get("pages") == 3)
        check("and the answer names it and where to fetch it",
              got.get("name") == os.path.basename(copy)
              and got.get("url") == "/library/marked/%s/%s" % (ident, got["name"]))
        with open(pdf, "rb") as fh:
            check("the original's bytes are unchanged", fh.read() == original)
        check("and so is its modification time", os.stat(pdf).st_mtime_ns == mtime)
        with open(rec_path, "r", encoding="utf-8") as fh:
            check("keeping a copy is not sending: the ink is still unsent",
                  json.load(fh).get("sent") is False)
        library.forget()
        after = library.documents(ws)
        check("the marked copy is not in library.documents afterwards",
              [d["id"] for d in after] == [ident]
              and not any("marked" in (d.get("rel") or "") for d in after))
        check("and git would not carry it, in a repository with no rule for "
              "live/", ignored(copy))

        status, raw, headers = call(got.get("url") or "/library/marked/x/y.pdf")
        check("the copy is handed over as an attachment, to go to Files",
              status == 200 and raw[:5] == b"%PDF-"
              and "attachment" in (headers.get("Content-Disposition") or ""))
        status, _raw, _h = call("/library/marked/%s/..%%2F..%%2Ftutorboard.json"
                                % ident)
        check("and a name that is not one of the copies is a miss", status == 404)

        guard = os.path.join(lrepo.live, "marked", ".gitignore")
        with open(guard, "r", encoding="utf-8") as fh:
            kept = fh.read()
        with open(guard, "w", encoding="utf-8") as fh:
            fh.write("!*\n")
        status, got2 = js("/annotate/burn", {"kind": "library/" + ident,
                                             "mode": "new"})
        check("a copy git WOULD carry is refused, and nothing is written",
              status == 400 and got2.get("why") == "tracked"
              and len(os.listdir(os.path.dirname(copy))) == 1)
        with open(guard, "w", encoding="utf-8") as fh:
            fh.write(kept)

        # ---- INK KNOWS ITS BUILD -------------------------------------------
        old_digest = view["digest"]
        time.sleep(1.1)
        make_pdf(pdf, ["UNO", "DOS", "TRES"])
        status, view2 = js("/library/view/" + ident)
        flag = view2.get("rebuilt") or {}
        check("a page saved against one build, reopened after a rebuild, "
              "carries the rebuilt-since flag",
              view2.get("digest") != old_digest and flag.get("pages") == [2])
        check("naming when the marks were drawn",
              flag.get("when") == library.when_built(view["build"]["at"])
              and re.match(r"\A\d{1,2} \w{3} \d\d:\d\d\Z", flag.get("when") or ""))
        check("and offering the copy, while that build is still in the cache",
              flag.get("copy") is True)
        # Unstamped ink past the old build's last page: the board viewer's, or
        # a record from before builds were stamped. It goes with whichever
        # build is burned, and this one has only three pages.
        past_key = "doc/%s/p4" % ident
        js("/annotate/save", {"card": past_key, "strokes": [stroke(0.3)]})
        status, got3 = js("/annotate/burn", {"kind": "library/" + ident,
                                             "mode": "new"})
        check("which is burned from the build the marks were drawn on",
              status == 200 and got3.get("ok") and got3.get("drawn") == flag["when"]
              and got3.get("pages") == 3)
        check("and a mark past that build's cached pages is SAID to be left "
              "out, not silently dropped",
              got3.get("dropped") == [4] and "page 4" in (got3.get("detail") or "")
              and "not in it" in (got3.get("detail") or ""))
        # And when EVERY mark is past it, no copy is written: one with none of
        # the ink on it is the unmarked document under another name.
        aside = rec_path + ".aside"
        os.rename(rec_path, aside)
        before = sorted(os.listdir(os.path.dirname(copy)))
        status, got4 = js("/annotate/burn", {"kind": "library/" + ident,
                                             "mode": "new"})
        check("a copy whose every mark is past the build's pages is refused, "
              "and nothing is written",
              status == 400 and got4.get("why") == "past-end"
              and got4.get("dropped") == [4]
              and sorted(os.listdir(os.path.dirname(copy))) == before)
        os.rename(aside, rec_path)
        js("/annotate/save", {"card": past_key, "strokes": []})
        work = tempfile.mkdtemp(prefix="burn-cache-check-")
        try:
            copy3 = os.path.join(ws, *(got3.get("path") or "x").split("/"))
            shots = burn._render_jpegs(copy3, work, dpi=40)
            check("and that copy, made of the cached pages, is a PDF a renderer "
                  "reads back page by page", len(shots) == 3)
        finally:
            shutil.rmtree(work, ignore_errors=True)

        for f in paper.cached(lrepo, old_digest):
            os.remove(os.path.join(paper.cache_dir(lrepo), f))
        status, view3 = js("/library/view/" + ident)
        flag = view3.get("rebuilt") or {}
        check("once that build is out of the cache the flag says a copy "
              "cannot be made",
              flag.get("copy") is False and "page cache" in (flag.get("detail") or ""))
        status, got4 = js("/annotate/burn", {"kind": "library/" + ident,
                                             "mode": "new"})
        check("and the burn refuses rather than put the marks on the wrong pages",
              status == 400 and got4.get("why") == "rebuilt")

        js("/annotate/save", {"card": key, "strokes": [stroke(0.5)],
                              "build": view3["build"]})
        status, view4 = js("/library/view/" + ident)
        check("ink drawn again on the new build is not flagged",
              view4.get("rebuilt") is None)

        # ---- THE FENCE -----------------------------------------------------
        real_find = library.find
        try:
            library.find = lambda root, wanted: {
                "id": "phi-secret", "dir": "phi", "stem": "secret",
                "title": "Session", "rel": "phi/secret.pdf", "source": ""}
            got5 = burn.burn(lrepo, "library/phi-secret", "new")
        finally:
            library.find = real_find
        check("a document inside a fence is refused",
              got5.get("ok") is False and got5.get("why") == "fenced")
        check("and nothing is written for it",
              not os.path.exists(os.path.join(lrepo.live, "marked", "phi-secret")))

        # A FENCED WORKSPACE keeps its copies inside itself and out of git.
        os.makedirs(os.path.join(ws, "phi"), exist_ok=True)
        status, got6 = js("/annotate/burn", {"kind": "library/" + ident,
                                             "mode": "new"})
        copy6 = os.path.join(ws, *(got6.get("path") or "x").split("/"))
        check("in a fenced workspace a copy lands inside that workspace, "
              "and git does not carry it",
              got6.get("ok") and os.path.realpath(copy6).startswith(
                  os.path.realpath(ws) + os.sep) and ignored(copy6))
    finally:
        httpd.shutdown()


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

    # ---- the burned copy agrees with the glass -----------------------------
    #
    # A stroke on a page (`pg`) is in pixels of a page INK_REFERENCE_WIDTH
    # wide, and `annotate.js` paints it at `w * pageWidth / PAGE_REF`: the two
    # constants are one number, or the copy is a different weight from the glass.
    with open(os.path.join(ROOT, "web", "annotate.js"), encoding="utf-8") as fh:
        ann = fh.read()
    ref = re.search(r"var PAGE_REF = (\d+);", ann)
    check("the glass and the burn measure a pen against the same page width",
          ref and float(ref.group(1)) == burn.INK_REFERENCE_WIDTH)
    check("and bring old ink onto the picture by the same rule",
          "H - pic > 4 && H - pic < 80" in ann
          and "4 < H - pic < 80" in open(burn.__file__, encoding="utf-8").read())
    glass_w = 972.0
    new_ink = {"c": "#ff0000", "w": 2.2 * 1240 / glass_w, "pg": 1,
               "p": [0.1, 0.5, 0.9, 0.5], "pr": [0.5, 0.5]}
    wops = burn._ink_ops([new_ink], 600.0, 338.0).decode("latin-1")
    lw = [float(x) for x in re.findall(r"([\d.]+) w\b", wops)]
    check("a line on a page burns at the weight against the page the glass shows",
          lw and abs(lw[0] / 600.0 - round(2.2 * 4) / 4 / glass_w) < 0.25 / glass_w)

    # INK SAVED BEFORE THE PAGE'S BOX WAS THE PICTURE: heights against the
    # picture and a 26px caption, the width in pixels of a 972px page, and the
    # geometry it was painted at beside it.
    aspect = 698 / 1240.0
    pic = glass_w * aspect
    H = round(pic + 26)
    old = {"c": "#ff0000", "w": 2.2, "p": [0.4, 0.9 * pic / H, 0.5, 0.2 * pic / H],
           "pr": [0.5, 0.5], "_k": "972x%d@104,18" % H, "_d": [[1, 2, 0.5]]}
    up = burn.on_page(old, aspect)
    check("old ink lands on the same words of the picture",
          abs(up["p"][1] - 0.9) < 1e-9 and abs(up["p"][3] - 0.2) < 1e-9
          and up["p"][0] == 0.4)
    check("at the weight it had against the page it was drawn on",
          abs(up["w"] - 2.2 * 1240 / glass_w) < 1e-9 and up["pg"] == 1)
    check("and ink drawn on a page with no caption is not stretched",
          burn.on_page({"w": 2.0, "p": [0.5, 0.5], "_k": "800x%d@18,18"
                        % round(800 * aspect)}, aspect)["p"][1] == 0.5)
    check("a stroke with no geometry is taken as already on the picture",
          burn.on_page({"w": 2.0, "p": [0.5, 0.5]}, aspect)["p"] == [0.5, 0.5])

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

    library_section(tmp)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print()
print("%d FAILURES" % len(fails) if fails else "writing on a document can be kept")
sys.exit(1 if fails else 0)
