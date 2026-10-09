"""Ink written on a document, put back into a PDF.

The board could already be written on. A compiled write-up is rasterised by
`paper.py`, each page gets a box, `annotate.js` attaches to the box, and the
strokes are stored against the key `doc/<ident>/p<n>` -- so marking up your own
homework on the glass has worked for as long as the viewer has. What there was
no way to do was KEEP it as a document. The ink lived in `live/annotations/`,
which is the board's own drawer: it comes back when you reopen the page, and it
is not a thing you can hand to anybody, mail to yourself, or read next year.

So: two answers to "keep it".

    new       a marked copy beside the PDF, `<stem>-marked.pdf`, then
              `<stem>-marked-2.pdf`, ...; the PDF itself is never written over
    none      keep nothing; the strokes stay where they are

EVERY DOCUMENT HAS THE SAME WAY OUT: a lesson's built PDF, a library document
(`library/<id>`), an upload or a material (`doc/<id>`, `library.readable`).
The copy goes beside the PDF it was burned from, and only where git would not
carry it -- the root `.gitignore` covers `*-marked.pdf` -- because a copy of
fenced content that a commit could carry cannot be taken back. The library's
walk does not offer a marked copy as a document of its own
(`library.marked_copy`).

The strokes are NOT in the copy's source: they are in the annotation record,
keyed to the page, so burning again after more ink is another copy with all of
it.

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
from . import library
from .. import fenced

# Print resolution for the re-rendered page. The board draws at 1240px across a
# page for the glass, which is about 150dpi on A4 and looks soft on paper.
BURN_DPI = 200

# A stroke on a page (`pg`) carries its width in pixels of a page this wide --
# `paper.PAGE_WIDTH`, the width the pages are drawn at, and `annotate.js`'s
# `PAGE_REF` -- so it burns at the weight against the page that the glass shows
# it at, at any zoom. Ink from before that is brought onto the page first
# (`on_page`).
INK_REFERENCE_WIDTH = float(paper.PAGE_WIDTH)

_GEOMETRY = re.compile(r"^(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)@")


def on_page(s, aspect):
    """One stroke in page units: heights fractions of the picture, `w` in
    pixels of a page `INK_REFERENCE_WIDTH` wide. `aspect` is height / width.

    `annotate.js`'s `onPage`, number for number, and it has to be: a stroke with
    no `pg` was stored against the figure -- the picture and a caption of fixed
    height under it -- with its width in CSS pixels at whatever width the page
    had. `_k`, `"<w>x<h>@..."`, is the box the viewer last painted it in; what of
    that height is not picture was caption, and the heights are stretched back
    over the picture. A stroke with no geometry is taken as already on it.
    """
    if s.get("pg"):
        return s
    m = _GEOMETRY.match(s.get("_k") if isinstance(s.get("_k"), str) else "")
    W, H = (float(m.group(1)), float(m.group(2))) if m else (0.0, 0.0)
    k, w = 1.0, float(s.get("w") or 2.2)
    if W > 0 and H > 0:
        pic = W * aspect
        if 4 < H - pic < 80:
            k = H / pic
        w = w * INK_REFERENCE_WIDTH / W
    p = [float(v) * (k if i % 2 else 1.0) for i, v in enumerate(s.get("p") or [])]
    return {"c": s.get("c"), "w": w, "p": p, "pr": list(s.get("pr") or []), "pg": 1}

MODES = ("new", "none")

# A DOCUMENT IN THE LIBRARY, as a viewer kind: `library/<id>`, the id
# `library.py` handed out. Its ink is under `doc/<id>/p<n>` -- `writing.ANN_DOC`
# -- and under the drawer's name for the same file, which is `mark_idents`.
LIBRARY = "library/"

# WHAT A MARKED COPY IS CALLED, beside its PDF (`library.MARKED`).
MARKED = library.MARKED


# ---------------------------------------------------------------------------
# WHICH DOCUMENT, AND WHOSE INK
# ---------------------------------------------------------------------------

def target_for(repo, kind):
    """The PDF behind a viewer `kind`, as `(path, stem)`, or `(None, None)`.

    The same three shapes the viewer opens -- `lesson`, `homework`, and
    `doc/<ident>` for an upload, a material or something the course points at
    (`library.readable`). Nothing here constructs a path out of the request:
    both branches go through a resolver that matches against what was found.
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
        path, _name = library.readable(repo, ident)
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


def strokes_by_page(repo, kind, pages_n, idents=None):
    """Every page's marks, as `{page number: [stroke, ...]}`, empty pages absent.

    Read straight out of the board's drawer through the same filename derivation
    the save route uses, because a key is validated there and a filename is
    DERIVED from it -- reproducing the flattening by hand here would be a second
    implementation of the one rule in this system that is load-bearing for
    security.
    """
    from ..server.routes import writing          # local: avoids an import cycle

    import json

    out = {}
    for ident in (idents or [ann_ident(kind)]):
        for n in range(1, int(pages_n or 0) + 1):
            key = "doc/%s/p%d" % (ident, n)
            if not writing.ann_ok(key):
                continue
            rec_path = writing.ann_path(repo, key)
            try:
                with open(rec_path, "r", encoding="utf-8") as fh:
                    rec = json.load(fh)
            except (OSError, ValueError):
                continue
            strokes = [s for s in (rec.get("strokes") or []) if (s or {}).get("p")]
            if strokes:
                out.setdefault(n, []).extend(strokes)
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
    strokes = [on_page(s, h_pt / w_pt) for s in strokes if s] if w_pt else strokes
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

def _png_parts(path):
    """`(width, height, colours, data)` of a PNG a PDF can take as it stands.

    A PNG's IDAT stream is zlib with a per-row predictor byte, which is exactly
    `FlateDecode` with `/Predictor 15` -- so a page out of the glass's cache
    goes into the file untouched, the way a JPEG does. Eight-bit grey or RGB,
    not interlaced, which is what poppler and Ghostscript write; anything else
    is None and the caller says so.
    """
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
    except OSError:
        return None
    if raw[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    at, head, data = 8, None, []
    while at + 8 <= len(raw):
        length, kind = struct.unpack(">I4s", raw[at:at + 8])
        body = raw[at + 8:at + 8 + length]
        if kind == b"IHDR":
            head = struct.unpack(">IIBBBBB", body[:13])
        elif kind == b"IDAT":
            data.append(body)
        elif kind == b"IEND":
            break
        at += 12 + length
    if not head or not data:
        return None
    w, h, depth, colour, _comp, _filt, interlace = head
    if depth != 8 or interlace or colour not in (0, 2):
        return None
    return w, h, (1 if colour == 0 else 3), b"".join(data)


def _image_obj(path, w_px, h_px):
    """One page picture as a PDF image object, JPEG or PNG, or None."""
    if path.lower().endswith(".png"):
        got = _png_parts(path)
        if not got:
            return None
        w, h, colours, data = got
        return (b"<< /Type /XObject /Subtype /Image /Width %d /Height %d "
                b"/ColorSpace /%s /BitsPerComponent 8 /Filter /FlateDecode "
                b"/DecodeParms << /Predictor 15 /Colors %d /BitsPerComponent 8 "
                b"/Columns %d >> /Length %d >>\nstream\n"
                % (w, h, b"DeviceGray" if colours == 1 else b"DeviceRGB",
                   colours, w, len(data))
                + data + b"\nendstream")
    with open(path, "rb") as fh:
        data = fh.read()
    return (b"<< /Type /XObject /Subtype /Image /Width %d /Height %d "
            b"/ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode "
            b"/Length %d >>\nstream\n" % (w_px, h_px, len(data))
            + data + b"\nendstream")


def _write_pdf(out_path, pages):
    """A PDF of `pages`, each `(image, w_px, h_px, ink_ops, w_pt, h_pt)`.

    Written by hand, which is less alarming than it sounds: a page that is one
    image plus one content stream is the simplest document the format has, and
    a JPEG goes in untouched because `DCTDecode` is the same encoding -- as
    does a cached PNG, under `FlateDecode` with the PNG predictor. The only
    fiddly part is the cross-reference table, and it is fiddly in a way that
    either works for every page or fails on the first.

    The page size in points comes WITH the page, because it is the size the
    ink was scaled to: a page box computed a second time here, at a different
    resolution, is ink drawn at the wrong scale.
    """
    objs = [b""]                       # 1-indexed; slot 0 is never written

    def add(body):
        objs.append(body)
        return len(objs) - 1            # objs[n] IS object n; slot 0 is the free head

    kids, page_objs = [], []
    for image, w_px, h_px, ink, w_pt, h_pt in pages:
        body = _image_obj(image, w_px, h_px)
        if body is None:
            raise ValueError("unreadable page picture: %s" % os.path.basename(image))
        img_num = add(body)
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


def new_name(stem):
    """What a marked copy is called: `<stem>-marked.pdf`."""
    return "%s%s.pdf" % (stem, MARKED)


def _free_name(directory, stem):
    """`<stem>-marked.pdf`, or `-marked-2.pdf`, ... where that is taken: a
    copy kept earlier is somebody's pass over the page, and a later one never
    writes over it."""
    first = new_name(stem)
    if not os.path.lexists(os.path.join(directory, first)):
        return first
    for n in range(2, 1000):
        cand = "%s%s-%d.pdf" % (stem, MARKED, n)
        if not os.path.lexists(os.path.join(directory, cand)):
            return cand
    return "%s%s-%d.pdf" % (stem, MARKED, os.getpid())


def _is_copy_name(stem, name):
    """Is `name` a marked copy of the PDF `<stem>.pdf`'s name?"""
    return bool(re.match(r"\A%s%s(?:-\d+)?\.pdf\Z" % (re.escape(stem), MARKED),
                         str(name or "")))


def _pages_from_pdf(target, marks, dpi, env):
    """Every page of `target` drawn at `dpi` with its marks.

    Returns `(pages, work_dir, None)` or `(None, work_dir, why)`. The caller
    removes `work_dir` once the file is written, because the pictures in it are
    read again then.
    """
    work = tempfile.mkdtemp(prefix="tutor-burn-")
    jpegs = _render_jpegs(target, work, dpi=dpi, env=env)
    if not jpegs:
        return None, work, {"ok": False, "why": "render",
                            "detail": "The pages could not be drawn from that PDF."}
    built = []
    for i, jpeg in enumerate(jpegs, start=1):
        size = _jpeg_size(jpeg)
        if not size:
            return None, work, {"ok": False, "why": "render",
                                "detail": "Page %d came back unreadable." % i}
        w_px, h_px = size
        w_pt = w_px * 72.0 / dpi
        h_pt = h_px * 72.0 / dpi
        built.append((jpeg, w_px, h_px,
                      _ink_ops(marks.get(i) or [], w_pt, h_pt), w_pt, h_pt))
    return built, work, None


# How wide a page out of the glass's cache is put on paper. The cache is drawn
# to a pixel width, not a resolution, so the page is given A4's width and the
# height its own picture has -- the ink is fractions of the page box either
# way, so it lands where it was drawn whatever the page measures in points.
CACHE_PAGE_PT = 595.2756


def _pages_from_cache(files, marks):
    """The build the marks were drawn on, out of the page cache.

    `(pages, None)` or `(None, why)`.
    """
    if not files:
        return None, {"ok": False, "why": "rebuilt",
                      "detail": "The build these marks were drawn on is no "
                                "longer in the page cache, so a marked copy of "
                                "it cannot be made."}
    built = []
    for i, png in enumerate(files, start=1):
        got = _png_parts(png)
        if not got:
            return None, {"ok": False, "why": "render",
                          "detail": "Page %d of the build these marks were drawn "
                                    "on cannot be read back out of the page "
                                    "cache." % i}
        w_px, h_px = got[0], got[1]
        w_pt = CACHE_PAGE_PT
        h_pt = h_px * w_pt / float(w_px or 1)
        built.append((png, w_px, h_px,
                      _ink_ops(marks.get(i) or [], w_pt, h_pt), w_pt, h_pt))
    return built, None


def _ignored(root, path):
    """Would git leave this file alone? True where there is no git to ask."""
    try:
        p = subprocess.run(["git", "-C", root, "check-ignore", "-q", path],
                           stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return True
    # 0 ignored, 1 not ignored, 128 not a repository -- nothing to track it.
    return p.returncode != 1


def copy_path(target, stem):
    """`(path, None)` of the marked copy to write beside `target`, or `(None,
    why)`. ASKED OF GIT rather than assumed: a copy a commit could carry is
    refused before anything is drawn."""
    here = os.path.dirname(target)
    out = os.path.join(here, _free_name(here, stem))
    if not _ignored(here, out):
        return None, {"ok": False, "why": "tracked",
                      "detail": "git would carry a marked copy written beside "
                                "%s, and a copy is never tracked. Nothing was "
                                "written." % os.path.basename(target)}
    return out, None


def marked_beside(target, name):
    """The marked copy `name` beside the PDF `target`, as a path, or "".

    A NAME, NEVER A PATH: matched against what is in that directory and
    against the copy's name rule, never joined on unchecked.
    """
    if not target:
        return ""
    here = os.path.dirname(target)
    stem = os.path.splitext(os.path.basename(target))[0]
    if not _is_copy_name(stem, name):
        return ""
    try:
        names = os.listdir(here)
    except OSError:
        return ""
    path = os.path.join(here, name)
    return path if name in names and os.path.isfile(path) else ""


def _fence_of(repo, doc, target):
    """The fenced directory this document sits in, or None."""
    for p in (doc.get("rel"), doc.get("source"), target):
        if not p:
            continue
        full = p if os.path.isabs(p) else os.path.join(repo.root, *p.split("/"))
        rel = os.path.relpath(full, repo.root).replace(os.sep, "/")
        hit = next((x for x in rel.lower().split("/") if x in fenced.NEVER), None)
        hit = hit or fenced.refused_in(repo.root, full)
        if hit:
            return hit
    return None


def marked_file(repo, ident, name):
    """The marked copy `name` of library document `ident`, as a path, or ""."""
    ident = str(ident or "").strip().lower()
    doc = library.find(repo.root, ident) if IDENT.match(ident) else None
    return marked_beside(library.path_of(repo.root, doc, ".pdf") if doc else "",
                         name)


def marked_of(repo, kind, name):
    """The marked copy `name` of the viewer kind `kind` (`homework`,
    `lesson`, `doc/<id>`), as a path, or ""."""
    target, _stem = target_for(repo, kind)
    return marked_beside(target, name)


IDENT = re.compile(r"\A[a-z0-9-]{1,40}\Z")


def burn_library(repo, ident, mode="new", dpi=BURN_DPI):
    """A marked copy of one library document. NEVER over the original.

    The library's documents are rebuilt by whatever made them -- a revision
    round, a `board build`, a `parts/` re-cut -- and the owner's ask was a copy
    *without overwriting*. So `new` is the only mode, and the copy goes beside
    the PDF (`copy_path`). Keeping a copy is not sending: nothing is marked
    delivered, and the ink goes with the next note.
    """
    if mode != "new":
        return {"ok": False, "why": "no-overwrite",
                "detail": "A document in the library is kept as a new marked "
                          "copy and never written over: whatever made it "
                          "rebuilds it, and the original stays as it is."}
    ident = str(ident or "").strip().lower()
    doc = library.find(repo.root, ident) if IDENT.match(ident) else None
    if not doc:
        return {"ok": False, "why": "none",
                "detail": "This workspace has no document by that name."}
    target = library.path_of(repo.root, doc, ".pdf")
    fence = _fence_of(repo, doc, target)
    if fence:
        return {"ok": False, "why": "fenced",
                "detail": "%s is inside %s/, and nothing on this board makes a "
                          "copy of what is in there."
                          % (doc.get("title") or ident, fence)}
    if not target:
        return {"ok": False, "why": "unbuilt",
                "detail": "There is no PDF of this document to write on yet."}
    marks = strokes_by_page(repo, LIBRARY + doc["id"], paper.MAX_PAGES,
                            idents=library.mark_idents(repo.root, doc))
    if not marks:
        return {"ok": False, "why": "no-ink",
                "detail": "Nothing is written on this document yet."}
    n_marks = sum(len(v) for v in marks.values())

    current = paper._digest(target, paper.PAGE_WIDTH)
    drawn = library.drawn_on(repo, doc, current)
    if drawn["refuse"]:
        return {"ok": False, "why": "rebuilt", "detail": drawn["refuse"]}

    out_path, stop = copy_path(target, doc["stem"])
    if stop:
        return stop

    work = None
    try:
        if drawn["digest"] != current:
            files = [paper.page_file(f) for f in paper.cached(drawn["digest"])]
            built, stop = _pages_from_cache(files, marks)
        else:
            env = paper.raster_env()
            if not paper.renderer(env):
                return {"ok": False, "why": "no-renderer",
                        "detail": "This machine has no pdftoppm and no "
                                  "Ghostscript, so the pages cannot be drawn "
                                  "to write on."}
            built, work, stop = _pages_from_pdf(target, marks, dpi, env)
        if stop:
            return stop
        # A COPY WITH NONE OF THE INK ON IT IS NOT A MARKED COPY. Every mark
        # past the last page of the build it would be burned from leaves a file
        # identical to the unmarked one, so nothing is written.
        if all(n > len(built) for n in marks):
            past = sorted(marks)
            return {"ok": False, "why": "past-end", "dropped": past,
                    "detail": "Every mark is on page%s %s, and the %s build it "
                              "would be burned from has %d page%s, so there "
                              "is nothing to write on."
                              % ("" if len(past) == 1 else "s",
                                 ", ".join(str(n) for n in past),
                                 drawn["rebuilt"]["when"] if drawn["rebuilt"]
                                 else "current", len(built),
                                 "" if len(built) == 1 else "s")}
        name = os.path.basename(out_path)
        try:
            _write_pdf(out_path, built)
        except (OSError, ValueError) as exc:
            return {"ok": False, "why": "render",
                    "detail": "The copy could not be written: %s." % exc}
    finally:
        if work:
            shutil.rmtree(work, ignore_errors=True)

    older = drawn["rebuilt"]
    # A MARK PAST THE LAST PAGE IS SAID, NOT DROPPED. The build a copy is burned
    # from -- an older one out of the page cache most of all -- can have fewer
    # pages than the ink is on, and a copy missing a ring somebody drew is a
    # copy they would believe was whole.
    past = sorted(n for n in marks if n > len(built))
    lost = sum(len(marks[n]) for n in past)
    said = ""
    if past:
        said = (" %d mark%s on page%s %s %s not in it: the %s build it was "
                "burned from has %d page%s."
                % (lost, "" if lost == 1 else "s", "" if len(past) == 1 else "s",
                   ", ".join(str(n) for n in past),
                   "is" if lost == 1 else "are",
                   older["when"] if older else "current", len(built),
                   "" if len(built) == 1 else "s"))
    return {"ok": True, "mode": "new",
            "path": os.path.relpath(os.path.realpath(out_path), os.path.realpath(
                repo.root)).replace(os.sep, "/"),
            "name": name, "document": doc["id"],
            "url": "/library/marked/%s/%s" % (doc["id"], name),
            "pages": len(built), "marks": n_marks - lost,
            "dropped": past,
            "drawn": older["when"] if older else "",
            "detail": ("Kept as %s%s.%s The ink stays on the page and still "
                       "goes with the next note."
                       % (name, (", on the %s build it was drawn on"
                                 % older["when"]) if older else "", said))}


def burn(repo, kind, mode="new", dpi=BURN_DPI):
    """Put this document's ink into a PDF. The whole job, and the only entry.

    Returns a dict the route can send as it stands: `ok`, and on success `mode`,
    `path` (repo-relative), `pages` and `marks`. Every failure carries a `why`
    and a sentence, because the board shows the sentence and "failed" sends
    somebody to a laptop to find out what this already knew.

    `library/<id>` is a document in the library and goes to `burn_library`,
    which offers `new` alone. Every other copy goes beside its PDF too, as
    `<stem>-marked.pdf`; nothing is ever written over the PDF itself.
    """
    if mode == "same":
        return {"ok": False, "why": "no-overwrite",
                "detail": "A marked copy goes beside the PDF and never over it: "
                          "the original stays as it is."}
    if mode not in MODES:
        return {"ok": False, "why": "bad-mode",
                "detail": "Keep a marked copy, or keep nothing."}

    if str(kind or "").startswith(LIBRARY):
        return burn_library(repo, str(kind)[len(LIBRARY):], mode, dpi)

    target, stem = target_for(repo, kind)
    if not target:
        return {"ok": False, "why": "none",
                "detail": "There is no compiled document here to write on yet."}

    got = paper.pages(repo, kind) if kind in paper.KINDS \
        else library.drawer_pages(repo, ann_ident(kind))
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

    out_path, stop = copy_path(target, stem)
    if stop:
        return stop
    work = None
    try:
        built, work, stop = _pages_from_pdf(target, marks, dpi, env)
        if stop:
            return stop
        _write_pdf(out_path, built)
    finally:
        if work:
            shutil.rmtree(work, ignore_errors=True)

    try:
        rel = os.path.relpath(os.path.realpath(out_path),
                              os.path.realpath(repo.root)).replace(os.sep, "/")
    except ValueError:
        rel = out_path
    name = os.path.basename(out_path)
    return {"ok": True, "mode": mode, "path": rel, "name": name,
            "url": "/marked/%s/%s" % (kind, name),
            "pages": len(built), "marks": n_marks,
            "detail": "Kept as %s, beside the original. The ink stays on the "
                      "page." % name}

