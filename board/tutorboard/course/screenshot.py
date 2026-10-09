"""screenshot.py -- the lesson as the pixels it was read as, wrapped in a PDF.

The other half of `web/shot.js`. Asked for from the iPad, about the export that
already existed: "for the tutor session export, I don't want the latex dump it
currently gives; I want it as if it were a screenshot of the entire iPad screen
scrolled down over the whole tutoring session."

WHAT IS HERE AND WHAT IS DELIBERATELY NOT. The pixels come from the client,
because the client is the only thing in the system that knows what the lesson
looks like -- there is no headless browser to render a page with. What is here
is everything a client must not be trusted with: where the document goes
(`transcripts/`), what it is called, which version it is, and that it is staged
for the next commit.

THE PDF IS WRITTEN BY HAND, and that is smaller than it sounds. A page holding
one JPEG needs a catalogue, a page tree, a page, a content stream of six
numbers, and an image object -- and a JPEG goes into a PDF *verbatim*, as
`/DCTDecode`, because PDF's image filters are the same ones the file already
uses. There is nothing to encode, so there is nothing to depend on: standard
library, like the rest of the board.

The client sends pages that are already the right shape -- all one size, cut
where a card allowed it to be cut. That is not an accident of convenience: it is
the only side holding the pixels, so it is the only side that can split a proof
taller than a page without a JPEG decoder. This writes what it is given.
"""

import base64
import os
import re
import struct
import subprocess
import time

from . import repo as course_repo


# ---------------------------------------------------------------------------
# where it goes, and what it is called
# ---------------------------------------------------------------------------
OUT_DIR = "transcripts"


def slugify(s):
    s = re.sub(r"[^A-Za-z0-9]+", "-", (s or "").strip().lower()).strip("-")
    return (s or "lesson")[:48]


def next_version(out_dir, stem):
    """v1, v2, v3 -- and never a timestamp: "which one is the latest" should
    not require reading a date. One more than the highest already there,
    counting a `.tex` too, so an old typeset export's number is never reused.
    """
    high = 0
    try:
        names = os.listdir(out_dir)
    except OSError:
        return 1
    pat = re.compile(re.escape(stem) + r"-v(\d+)\.(pdf|tex)$")
    for n in names:
        m = pat.match(n)
        if m:
            high = max(high, int(m.group(1)))
    return high + 1


def author_name(root, state):
    """Whose name goes on it: state.json, then git, then nobody."""
    if state.get("author"):
        return state["author"]
    try:
        p = subprocess.run(["git", "config", "user.name"], cwd=root,
                           stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=5)
        if p.returncode == 0:
            return p.stdout.decode("utf-8", "replace").strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return ""


def track(root, paths):
    """Stage the export, so the next push carries it. Staged rather than
    committed: a commit in the middle of a lesson is the person's decision."""
    rel = [os.path.relpath(p, root) for p in paths if os.path.exists(p)]
    if not rel:
        return False
    try:
        p = subprocess.run(["git", "add", "--"] + rel, cwd=root,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
        return p.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


# A JPEG's own header says how big it is, and the PDF has to agree with it to
# the pixel or the page is stretched. Trusting the client's arithmetic here
# would be trusting a number over the wire against bytes on disk.
def jpeg_size(data):
    """Width and height out of a JPEG's frame header, or None if it is not one.

    Also the validator: this is bytes off the network being written into a
    repository, and "the client said it was a JPEG" is not a property that
    survives. A file that has no SOF marker is not a photograph of anything.
    """
    if len(data) < 4 or data[0:2] != b"\xff\xd8":
        return None
    i = 2
    n = len(data)
    while i + 3 < n:
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
            i += 2
            continue
        if marker == 0xD9:                      # end of image, no frame seen
            return None
        if i + 4 > n:
            return None
        seglen = struct.unpack(">H", data[i + 2:i + 4])[0]
        # SOF0..SOF15, less the four that are not frame headers.
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            if i + 9 > n:
                return None
            height, width = struct.unpack(">HH", data[i + 5:i + 9])
            if width <= 0 or height <= 0:
                return None
            return width, height
        i += 2 + max(seglen, 2)
    return None


def _esc(text):
    return (text or "").replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def write_pdf(path, pages, page_w, page_h, title="", author=""):
    """One PDF, one JPEG per page, each filling its page.

    Objects are laid out in a fixed order and their byte offsets recorded as
    they are written, because that table is the only way a reader finds anything
    in a PDF and an offset that is one byte out is a file no reader will open.
    """
    if not pages:
        raise ValueError("there are no pages to write")

    objects = []            # index -> bytes of the object body

    def add(body):
        objects.append(body)
        return len(objects)         # object numbers are 1-based

    catalog = add(b"")              # 1, filled in once the page tree exists
    tree = add(b"")                 # 2, likewise
    info = add(("<< /Title (%s) /Author (%s) /Producer (Tutor-Board) "
                "/CreationDate (D:%s) >>"
                % (_esc(title), _esc(author),
                   time.strftime("%Y%m%d%H%M%S"))).encode("utf-8"))

    kids = []
    for data in pages:
        size = jpeg_size(data)
        if not size:
            raise ValueError("a page arrived that is not a JPEG")
        width, height = size
        img = add(("<< /Type /XObject /Subtype /Image /Width %d /Height %d "
                   "/ColorSpace /DeviceRGB /BitsPerComponent 8 "
                   "/Filter /DCTDecode /Length %d >>" % (width, height, len(data))
                   ).encode("utf-8") + b"\nstream\n" + data + b"\nendstream")
        # Full bleed: the client already left the margin inside the picture, so
        # the picture IS the page. Anything else would letterbox a screenshot.
        stream = ("q %.2f 0 0 %.2f 0 0 cm /Im Do Q"
                  % (page_w, page_h)).encode("ascii")
        content = add(("<< /Length %d >>" % len(stream)).encode("ascii")
                      + b"\nstream\n" + stream + b"\nendstream")
        page = add(("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %.2f %.2f] "
                    "/Resources << /XObject << /Im %d 0 R >> >> "
                    "/Contents %d 0 R >>" % (page_w, page_h, img, content)
                    ).encode("utf-8"))
        kids.append(page)

    objects[tree - 1] = ("<< /Type /Pages /Count %d /Kids [%s] >>"
                         % (len(kids), " ".join("%d 0 R" % k for k in kids))
                         ).encode("utf-8")
    objects[catalog - 1] = ("<< /Type /Catalog /Pages %d 0 R >>" % tree).encode("utf-8")

    out = [b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"]
    offsets = []
    at = len(out[0])
    for i, body in enumerate(objects, start=1):
        chunk = ("%d 0 obj\n" % i).encode("ascii") + body + b"\nendobj\n"
        offsets.append(at)
        out.append(chunk)
        at += len(chunk)

    start = at
    table = [("xref\n0 %d\n" % (len(objects) + 1)).encode("ascii"),
             b"0000000000 65535 f \n"]
    for off in offsets:
        table.append(("%010d 00000 n \n" % off).encode("ascii"))
    out.append(b"".join(table))
    out.append(("trailer\n<< /Size %d /Root %d 0 R /Info %d 0 R >>\n"
                "startxref\n%d\n%%%%EOF\n"
                % (len(objects) + 1, catalog, info, start)).encode("ascii"))

    tmp = path + ".part"
    with open(tmp, "wb") as fh:
        fh.write(b"".join(out))
    os.replace(tmp, path)
    return path


# A page from a tablet at ratio 2 is around 1500x2100; anything far outside that
# is not a photograph of a board. The ceiling is what keeps a malformed or
# malicious payload from becoming a gigabyte in somebody's repository.
MAX_PAGES = 400
MAX_PAGE_BYTES = 8 * 1024 * 1024
A4 = (595.28, 841.89)


def build(root, pages, page_w=None, page_h=None):
    """The pixels, into the repository, named and numbered: v1, v2, v3 of
    the same lesson, through `next_version`."""
    if not pages:
        return {"ok": False, "detail": "the lesson came back with no pages in it"}
    if len(pages) > MAX_PAGES:
        return {"ok": False,
                "detail": "that is %d pages; something is wrong" % len(pages)}
    for data in pages:
        if len(data) > MAX_PAGE_BYTES:
            return {"ok": False, "detail": "a page arrived far too large to be one"}
        if not jpeg_size(data):
            return {"ok": False, "detail": "a page arrived that is not a JPEG"}

    state = course_repo.session_state(root)
    title = state.get("chapter") or state.get("course") or "Lesson"
    stem = slugify(title)
    out_dir = os.path.join(root, OUT_DIR)
    os.makedirs(out_dir, exist_ok=True)
    version = next_version(out_dir, stem)
    name = "%s-v%d" % (stem, version)
    pdf_path = os.path.join(out_dir, name + ".pdf")

    try:
        write_pdf(pdf_path, pages,
                  page_w or A4[0], page_h or A4[1],
                  title=title, author=author_name(root, state))
    except (OSError, ValueError) as exc:
        return {"ok": False, "detail": "could not write the document: %s" % exc}

    return {"ok": True, "name": name, "version": version, "scope": "shot",
            "kind": "shot", "pages": len(pages), "tex": None,
            "pdf": os.path.relpath(pdf_path, root), "detail": "",
            "tracked": track(root, [pdf_path])}


def decode(payload):
    """The page images out of a request body, or a reason there are none.

    Base64 rather than multipart: there are a few dozen of these, they are
    generated in one pass on the device, and a JSON body is the one shape both
    ends already agree about. The padding is repaired rather than rejected --
    a stripped `=` is the single most common way base64 arrives wrong and it
    costs nothing to accept.
    """
    raw = payload.get("pages")
    if not isinstance(raw, list) or not raw:
        return None, "no pages arrived"
    out = []
    for item in raw:
        if not isinstance(item, str):
            return None, "a page arrived that is not an image"
        text = re.sub(r"^data:[^,]*,", "", item.strip())
        text += "=" * (-len(text) % 4)
        try:
            out.append(base64.b64decode(text, validate=False))
        except Exception:                                    # noqa: BLE001
            return None, "a page arrived that could not be decoded"
    return out, None


def page_box(payload):
    """The paper the client asked for, clamped to something a printer knows.

    A4 unless it says otherwise, and never a number that would make the document
    unopenable -- a MediaBox of zero is a file every reader rejects, and it would
    arrive from a device that had simply measured a hidden element.
    """
    box = payload.get("page") or {}
    try:
        w = float(box.get("w") or A4[0])
        h = float(box.get("h") or A4[1])
    except (TypeError, ValueError):
        return A4
    if not (72 <= w <= 2000) or not (72 <= h <= 2000):
        return A4
    return w, h
