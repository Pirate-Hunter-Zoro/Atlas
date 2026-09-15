"""Ink written on a document, put back into a PDF.

The board could already be written on. A compiled write-up is rasterised by
`paper.py`, each page gets a box, `annotate.js` attaches to the box, and the
strokes are stored against the key `doc/<ident>/p<n>` -- so marking up your own
homework on the glass has worked for as long as the viewer has. What there was
no way to do was KEEP it as a document. The ink lived in `live/annotations/`,
which is the board's own drawer: it comes back when you reopen the page, and it
is not a thing you can hand to anybody, mail to yourself, or read next year.

So: three ways to leave, and they are the three anybody means by "save".

    same      the PDF being viewed, overwritten in place
    new       a new file beside it, named and dated, nothing touched
    none      keep nothing; the strokes stay in the board's drawer

**Overwriting a compiled write-up is a real overwrite, and it is meant.** The
next `make homework CH=04` rewrites that file from the .tex and the burned ink
goes with it. That is not a bug to be designed around, because the strokes are
NOT in the PDF -- they are in the annotation record, keyed to the page, and they
survive the compile that destroys their rendering. Burning again puts them back
on the fresh pages. The PDF is a rendering of two things that are both still on
disk, which is the only reason overwriting it is safe to offer.

HOW THE PAGE SURVIVES, given no PDF library on this machine and none coming --
`AI_INSTRUCTIONS.md` says a dependency pit is the thing to avoid, and the server
is standard library. A PDF cannot be edited in place without a parser, so it is
not edited: each page is re-rendered to a JPEG at print resolution by the
rasteriser `paper.py` already found, and a new PDF is assembled here with the
page as an image and the ink as vector paths over it. One file, no imports.

What that costs is the text layer: the output is a picture of the page, so it
cannot be searched or selected. What it buys is that this works on every machine
that can already show a document on the board, which is the bar every other path
through `paper.py` is held to.
"""

import datetime
import glob
import os
import re
import shutil
import struct
import subprocess
import tempfile
import zlib

from . import paper
from . import reading

# Print resolution for the re-rendered page. The board draws at 1240px across a
# page for the glass, which is about 150dpi on A4 and looks soft on paper.
BURN_DPI = 200

# The pen's width is in CSS pixels, taken against whatever the panel happened to
# be when the mark was made, and the panel is not recorded. Every stroke is
# therefore scaled as a fraction of ONE nominal page width, and this is it --
# `paper.PAGE_WIDTH`, the width the pages themselves are drawn at. A mark made
# on a narrow panel and a mark made on a wide one come out the same weight,
# which is right: the person was drawing on a page, not on a number of pixels.
INK_REFERENCE_WIDTH = float(paper.PAGE_WIDTH)

MODES = ("same", "new", "none")


# ---------------------------------------------------------------------------
# WHICH DOCUMENT, AND WHOSE INK
# ---------------------------------------------------------------------------

def target_for(repo, kind):
    """The PDF behind a viewer `kind`, as `(path, stem)`, or `(None, None)`.

    The same three shapes the viewer opens -- `lesson`, `homework`, and
    `doc/<ident>` for something the course points at rather than built. Nothing
    here constructs a path out of the request: both branches go through the
    resolver that already refuses anything outside the repository.
    """
    kind = str(kind or "").strip()
    if kind in paper.KINDS:
        path, filename = paper.resolve(repo, kind)
        if not path:
            return None, None
        return path, os.path.splitext(os.path.basename(path))[0]
    if kind.startswith("doc/"):
        ident = kind[len("doc/"):]
        if not re.match(r"\A[a-z0-9-]{1,40}\Z", ident):
            return None, None
        path, _name = reading.find(repo.root, ident)
        if not path:
            return None, None
        return path, os.path.splitext(os.path.basename(path))[0]
    return None, None


def ann_ident(kind):
    """The `ident` half of the annotation key the viewer writes.

    `board.js` uses the kind itself for a built document and the tail for one
    the course points at, so `homework` and `doc/ch04` both land on
    `doc/<ident>/p<n>`. Read it back exactly the way it was written; guessing a
    second spelling here is how ink goes missing while still being on disk.
    """
    kind = str(kind or "").strip()
    return kind[len("doc/"):] if kind.startswith("doc/") else kind


def strokes_by_page(repo, kind, pages_n):
    """Every page's marks, as `{page number: [stroke, ...]}`, empty pages absent.

    Read straight out of the board's drawer through the same filename derivation
    the save route uses, because a key is validated there and a filename is
    DERIVED from it -- reproducing the flattening by hand here would be a second
    implementation of the one rule in this system that is load-bearing for
    security.
    """
    from ..server.routes import writing          # local: avoids an import cycle

    import json

    ident = ann_ident(kind)
    out = {}
    for n in range(1, int(pages_n or 0) + 1):
        key = "doc/%s/p%d" % (ident, n)
        if not writing.ann_ok(key):
            continue
        rec_path = os.path.join(repo.notes, writing.ann_file(key) + ".json")
        try:
            with open(rec_path, "r", encoding="utf-8") as fh:
                rec = json.load(fh)
        except (OSError, ValueError):
            continue
        strokes = [s for s in (rec.get("strokes") or []) if (s or {}).get("p")]
        if strokes:
            out[n] = strokes
    return out


# ---------------------------------------------------------------------------
# THE PAGES, AS PICTURES
# ---------------------------------------------------------------------------

def _jpeg_size(path):
    """`(width, height)` of a JPEG, off its own start-of-frame marker.

    Twenty lines rather than an image library, for the same reason as everything
    else in this file. Only the frame header is read; the scan is never touched.
    """
    with open(path, "rb") as fh:
        if fh.read(2) != b"\xff\xd8":
            return None
        while True:
            b = fh.read(1)
            while b and b != b"\xff":
                b = fh.read(1)
            if not b:
                return None
            marker = fh.read(1)
            while marker == b"\xff":
                marker = fh.read(1)
            if not marker:
                return None
            code = marker[0]
            if code in (0xD8, 0xD9) or 0xD0 <= code <= 0xD7:
                continue
            head = fh.read(2)
            if len(head) < 2:
                return None
            length = struct.unpack(">H", head)[0]
            # Start of frame, any flavour except the four that are not frames.
            if 0xC0 <= code <= 0xCF and code not in (0xC4, 0xC8, 0xCC):
                body = fh.read(5)
                if len(body) < 5:
                    return None
                h, w = struct.unpack(">HH", body[1:5])
                return w, h
            fh.seek(length - 2, os.SEEK_CUR)


def _render_jpegs(pdf_path, out_dir, dpi=BURN_DPI, env=None):
    """Every page of a PDF as a JPEG in `out_dir`, in order, or `[]`.

    poppler and Ghostscript both do this and the board already prefers whichever
    it found for the glass. The failure that matters is a machine with neither,
    and it is reported rather than raised -- `paper.py`'s own rule.
    """
    env = env or paper.raster_env()
    found = paper.renderer(env)
    if not found:
        return []
    name, tool = found
    prefix = os.path.join(out_dir, "page")
    if name in ("pdftoppm", "pdftocairo"):
        cmd = [tool, "-jpeg", "-r", str(int(dpi)), pdf_path, prefix]
    else:
        cmd = [tool, "-dSAFER", "-dBATCH", "-dNOPAUSE", "-sDEVICE=jpeg",
               "-r%d" % int(dpi), "-dJPEGQ=92",
               "-sOutputFile=%s-%%d.jpg" % prefix, pdf_path]
    try:
        subprocess.run(cmd, cwd=out_dir, env=env, timeout=600,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       check=True)
    except (OSError, subprocess.SubprocessError):
        return []
    files = glob.glob(prefix + "*.jpg") + glob.glob(prefix + "*.jpeg")
    return sorted(files, key=_page_number)


def _page_number(path):
    """The page a rendered file is, off its own name.

    `paper.py` has one of these and it matches `.png`, because that is what the
    glass is drawn in. These are JPEGs, so that one returns 0 for every file
    here and `sorted` falls back to whatever order the directory came back in --
    which put page 3 first and the ink on the wrong page. Numbers are also not
    padded consistently between poppler and Ghostscript, so the digits are read
    rather than the string being compared.
    """
    m = re.search(r"-(\d+)\.(?:jpe?g|png)$", path)
    return int(m.group(1)) if m else 0


# ---------------------------------------------------------------------------
# THE INK, AS PATHS
# ---------------------------------------------------------------------------

def _rgb(colour):
    """`#rrggbb` to three PDF numbers. An unreadable colour draws as the pen's."""
    m = re.match(r"\A#?([0-9a-fA-F]{6})\Z", str(colour or ""))
    hexed = m.group(1) if m else "e0b45c"
    return tuple(int(hexed[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def _width_at(pr_a, pr_b, base):
    """The same taper `annotate.js` paints, so burned ink matches drawn ink.

    Quarter-unit quantisation included: it is what lets consecutive segments of
    equal width become one path there, and it is what makes them one path here.
    """
    return round(base * (0.65 + 0.7 * ((pr_a + pr_b) / 2.0)) * 4) / 4.0


def _ink_ops(strokes, w_pt, h_pt):
    """One page's marks as PDF content-stream operators.

    Fractions of the page box become points, and the y axis turns over: the box
    counts down from the top and a PDF counts up from the bottom.

    A stroke may legitimately sit outside the page -- `annotate.js` stopped
    clamping so that a ring drawn round something near an edge keeps its curve
    -- so the content is clipped to the page rather than the coordinates being
    squashed back inside it, which would straighten exactly those rings.
    """
    scale = w_pt / INK_REFERENCE_WIDTH
    ops = ["q", "%.2f %.2f %.2f %.2f re W n" % (0, 0, w_pt, h_pt),
           "1 J", "1 j"]
    for s in strokes:
        flat = s.get("p") or []
        n = len(flat) // 2
        if n < 1:
            continue
        pr = s.get("pr") or []
        base = float(s.get("w") or 2.2) * scale
        r, g, b = _rgb(s.get("c"))
        pts = []
        for i in range(n):
            x = float(flat[2 * i]) * w_pt
            y = h_pt - float(flat[2 * i + 1]) * h_pt
            p = float(pr[i]) if i < len(pr) else 0.5
            pts.append((x, y, p))
        ops.append("%.4f %.4f %.4f RG" % (r, g, b))
        ops.append("%.4f %.4f %.4f rg" % (r, g, b))
        if n == 1:
            # A dot. A zero-length path with a round cap paints nothing in some
            # readers, so it is drawn as a filled circle, the way the canvas
            # draws it -- four Beziers, the usual 0.5523 kappa.
            x, y, p = pts[0]
            rad = base * (0.65 + 0.7 * p) / 2.0
            k = rad * 0.5523
            ops.append("%.3f %.3f m" % (x - rad, y))
            ops.append("%.3f %.3f %.3f %.3f %.3f %.3f c"
                       % (x - rad, y + k, x - k, y + rad, x, y + rad))
            ops.append("%.3f %.3f %.3f %.3f %.3f %.3f c"
                       % (x + k, y + rad, x + rad, y + k, x + rad, y))
            ops.append("%.3f %.3f %.3f %.3f %.3f %.3f c"
                       % (x + rad, y - k, x + k, y - rad, x, y - rad))
            ops.append("%.3f %.3f %.3f %.3f %.3f %.3f c"
                       % (x - k, y - rad, x - rad, y - k, x - rad, y))
            ops.append("f")
            continue
        i = 1
        while i < len(pts):
            w = _width_at(pts[i - 1][2], pts[i][2], base)
            ops.append("%.3f w" % max(w, 0.1))
            ops.append("%.3f %.3f m" % (pts[i - 1][0], pts[i - 1][1]))
            ops.append("%.3f %.3f l" % (pts[i][0], pts[i][1]))
            i += 1
            while i < len(pts) and _width_at(pts[i - 1][2], pts[i][2], base) == w:
                ops.append("%.3f %.3f l" % (pts[i][0], pts[i][1]))
                i += 1
            ops.append("S")
    ops.append("Q")
    return "\n".join(ops).encode("latin-1", "replace")


# ---------------------------------------------------------------------------
# THE FILE
# ---------------------------------------------------------------------------

def _write_pdf(out_path, pages):
    """A PDF of `pages`, each `(jpeg_path, w_px, h_px, ink_ops_bytes)`.

    Written by hand, which is less alarming than it sounds: a page that is one
    image plus one content stream is the simplest document the format has, and
    a JPEG goes in untouched because `DCTDecode` is the same encoding. The only
    fiddly part is the cross-reference table, and it is fiddly in a way that
    either works for every page or fails on the first.
    """
    objs = [b""]                       # 1-indexed; slot 0 is never written

    def add(body):
        objs.append(body)
        return len(objs) - 1            # objs[n] IS object n; slot 0 is the free head

    kids, page_objs = [], []
    for jpeg, w_px, h_px, ink in pages:
        with open(jpeg, "rb") as fh:
            data = fh.read()
        w_pt = w_px * 72.0 / BURN_DPI
        h_pt = h_px * 72.0 / BURN_DPI
        img_num = add(
            b"<< /Type /XObject /Subtype /Image /Width %d /Height %d "
            b"/ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode "
            b"/Length %d >>\nstream\n" % (w_px, h_px, len(data))
            + data + b"\nendstream")
        content = (b"q\n%.4f 0 0 %.4f 0 0 cm\n/Im0 Do\nQ\n"
                   % (w_pt, h_pt)) + ink
        packed = zlib.compress(content)
        con_num = add(b"<< /Length %d /Filter /FlateDecode >>\nstream\n"
                      % len(packed) + packed + b"\nendstream")
        page_objs.append((img_num, con_num, w_pt, h_pt))

    # The Pages object is written AFTER its children and has to be numbered
    # before them, because each child names it as /Parent. Two objects went in
    # per page above and one goes in per page below, so it lands here.
    pages_num = len(objs) + len(page_objs)
    for img_num, con_num, w_pt, h_pt in page_objs:
        num = add(b"<< /Type /Page /Parent %d 0 R /MediaBox [0 0 %.4f %.4f] "
                  b"/Resources << /XObject << /Im0 %d 0 R >> >> "
                  b"/Contents %d 0 R >>"
                  % (pages_num, w_pt, h_pt, img_num, con_num))
        kids.append(num)

    pages_obj = add(b"<< /Type /Pages /Kids [%s] /Count %d >>"
                    % (b" ".join(b"%d 0 R" % k for k in kids), len(kids)))
    root = add(b"<< /Type /Catalog /Pages %d 0 R >>" % pages_obj)

    stamp = datetime.datetime.now().strftime("D:%Y%m%d%H%M%S")
    info = add(b"<< /Producer (Tutor-Board) /CreationDate (%s) >>"
               % stamp.encode("latin-1"))

    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0] * (len(objs) + 1)
    for num in range(1, len(objs)):
        offsets[num] = len(out)
        out += b"%d 0 obj\n" % num + objs[num] + b"\nendobj\n"
    start = len(out)
    out += b"xref\n0 %d\n" % len(objs)
    out += b"0000000000 65535 f \n"
    for num in range(1, len(objs)):
        out += b"%010d 00000 n \n" % offsets[num]
    out += (b"trailer\n<< /Size %d /Root %d 0 R /Info %d 0 R >>\nstartxref\n%d\n%%%%EOF\n"
            % (len(objs), root, info, start))

    tmp = out_path + ".part"
    with open(tmp, "wb") as fh:
        fh.write(bytes(out))
    os.replace(tmp, out_path)
    return out_path


def new_name(stem, when=None):
    """What a `new` save is called: the document, annotated, and the day.

    The date is in it because this is the option somebody picks when they want
    to keep THIS pass over the page and go on marking. Two passes on one evening
    collide, and a counter settles it -- silently overwriting the file chosen
    precisely so that nothing would be overwritten is the one outcome this mode
    exists to prevent.
    """
    day = (when or datetime.date.today()).strftime("%Y-%m-%d")
    return "%s-annotated-%s.pdf" % (stem, day)


def _free_name(directory, stem, when=None):
    first = new_name(stem, when)
    if not os.path.exists(os.path.join(directory, first)):
        return first
    base = os.path.splitext(first)[0]
    for n in range(2, 100):
        cand = "%s-%d.pdf" % (base, n)
        if not os.path.exists(os.path.join(directory, cand)):
            return cand
    return "%s-%d.pdf" % (base, os.getpid())


def burn(repo, kind, mode="new", dpi=BURN_DPI):
    """Put this document's ink into a PDF. The whole job, and the only entry.

    Returns a dict the route can send as it stands: `ok`, and on success `mode`,
    `path` (repo-relative), `pages` and `marks`. Every failure carries a `why`
    and a sentence, because the board shows the sentence and "failed" sends
    somebody to a laptop to find out what this already knew.
    """
    if mode not in MODES:
        return {"ok": False, "why": "bad-mode",
                "detail": "Save it over the original, as a new file, or not at all."}

    target, stem = target_for(repo, kind)
    if not target:
        return {"ok": False, "why": "none",
                "detail": "There is no compiled document here to write on yet."}

    got = paper.pages(repo, kind) if kind in paper.KINDS \
        else reading.pages(repo, ann_ident(kind))
    pages_n = len(got.get("pages") or []) if got.get("ok") else 0
    marks = strokes_by_page(repo, kind, pages_n or paper.MAX_PAGES)

    if not marks:
        return {"ok": False, "why": "no-ink",
                "detail": "Nothing is written on this document yet."}

    n_marks = sum(len(v) for v in marks.values())

    # KEEPING NOTHING IS A REAL ANSWER, and it is answered before any rendering:
    # the person said not to write a file, so no file is written and no minute
    # is spent drawing pages for one. The strokes stay in the drawer, where they
    # already were -- "do not save" means "do not make a document of it", not
    # "throw away what I drew".
    if mode == "none":
        return {"ok": True, "mode": "none", "path": None,
                "pages": len(marks), "marks": n_marks,
                "detail": "Kept on the board and not written to a file."}

    env = paper.raster_env()
    if not paper.renderer(env):
        return {"ok": False, "why": "no-renderer",
                "detail": "This machine has no pdftoppm and no Ghostscript, so "
                          "the pages cannot be drawn to write on."}

    work = tempfile.mkdtemp(prefix="tutor-burn-")
    try:
        jpegs = _render_jpegs(target, work, dpi=dpi, env=env)
        if not jpegs:
            return {"ok": False, "why": "render",
                    "detail": "The pages could not be drawn from that PDF."}
        built = []
        for i, jpeg in enumerate(jpegs, start=1):
            size = _jpeg_size(jpeg)
            if not size:
                return {"ok": False, "why": "render",
                        "detail": "Page %d came back unreadable." % i}
            w_px, h_px = size
            w_pt = w_px * 72.0 / dpi
            h_pt = h_px * 72.0 / dpi
            built.append((jpeg, w_px, h_px,
                          _ink_ops(marks.get(i) or [], w_pt, h_pt)))

        if mode == "same":
            out_path = target
        else:
            out_path = os.path.join(os.path.dirname(target),
                                    _free_name(os.path.dirname(target), stem))
        _write_pdf(out_path, built)
    finally:
        shutil.rmtree(work, ignore_errors=True)

    try:
        rel = os.path.relpath(out_path, repo.root)
    except ValueError:
        rel = out_path
    return {"ok": True, "mode": mode, "path": rel,
            "name": os.path.basename(out_path),
            "pages": len(built), "marks": n_marks,
            "detail": ("Written back over %s." % os.path.basename(out_path))
                      if mode == "same"
                      else ("Saved as %s." % os.path.basename(out_path))}
