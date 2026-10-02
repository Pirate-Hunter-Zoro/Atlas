"""ledger.py -- every round of feedback as numbered requests, and what was done.

**The owner's words:** *"I need some nifty way to keep track of what each edit
request was, and what was done to address it, so that I don't have to read the
whole fucking paper again."* So a round is a list of ITEMS, each item gets an
answer, and each answer is a pin on the new pages.

WHAT IS ON DISK, beside the note `feedback/<day>-v<n>.md`:

    <day>-v<n>.ledger.json   THE CONTRACT WITH THE TURN. The requests (`items`)
                             and the turn's `answers`, one per id. The turn
                             edits `answers` and nothing else.
    <day>-v<n>/              THE ROUND'S OWN DIRECTORY, which only the board
                             writes and nothing ever wipes:
        items.json           the requests exactly as filed, so a turn that
                             mangles the ledger cannot lose them
        R3.1.svg             one crop per inked request: that region of the
                             page with the ink over it
        marked-p<n>.png      the reader's picture of a whole marked page
        before.<ext>         the source as it stood when the round was filed
        after.<ext>          the source once the round landed, taken ONCE and
                             never again: the next round's `before` where there
                             is one, the live source at the first look after
                             the answers came back where there is not
        states.json          accepted / reopened, per id, set from the glass
        unsent.json          present when the revision could not be asked: the
                             round is kept on disk and counted nowhere, and its
                             requests go again, under new ids, with the retry
        checked.json         the validation of the answers, keyed on the
                             ledger's own stat so it runs once per change
        placed-<digest>.json where each answer sits on one build of the PDF
    <day>-v<n>.factory.json  what Paper-Writer's editor actually APPLIED, when
                             the manuscript factory answered the round

WHY THE DERIVED HALF IS NOT IN THE LEDGER. The turn rewrites that file, and a
state set from the glass while it does is a state lost. And a placement written
into it would move the stat the validation is keyed on, so the board would
re-validate its own writes for ever.

AN ID IS STORED, NOT RECOMPUTED. `R3.4` is round 3, item 4, fixed when it is
filed: a reopened item rides every later round under the same id, and a round
deleted later must not renumber a request somebody has already tapped.

Standard library only, and poppler for the text layer and the crops -- the same
tools `course/paper.py` already shells out to.
"""

import base64
import difflib
import html
import json
import os
import re
import shutil
import struct
import subprocess
import time
import unicodedata

from . import paper

# The four answers a request can get. Anything else from a turn is refused by
# the validation and shows as NOT ANSWERED, never as a guess at what it meant.
DISPOSITIONS = ("done", "partly", "not done", "pushed back")
# The two that changed text, and so owe the new wording of what they changed.
WORDED = ("done", "partly")
# Spellings a turn reaches for that mean exactly one of the four.
_SAME = {"not_done": "not done", "not-done": "not done", "notdone": "not done",
         "pushed_back": "pushed back", "pushed-back": "pushed back",
         "pushback": "pushed back", "push back": "pushed back",
         "partial": "partly", "partially": "partly"}

STATES = ("open", "accepted", "reopened")

# HOW NEAR TWO STROKES ARE TO BE ONE REQUEST, in fractions of the page. A ring
# and the arrow out of it are one complaint; two rings a third of a page apart
# are two. Wide enough for handwriting beside a mark, narrow enough that two
# paragraphs' worth of marks do not merge.
GAP = 0.05
# A crop shows a little of the page round the ink, so it can be recognised.
PAD = 0.03
# The width, in pixels, of the page a crop is cut out of.
CROP_WIDTH = 1000
# `annotate.js` `PAGE_REF`: a page stroke's width is stored against this.
PAGE_REF = 1240
# Bounded, because a pasted essay is still one request per paragraph.
TEXT_MAX = 2000
POINTS_MAX = 64

MARKER = ("<!-- ledger: the section below is written by the board from this "
          "round's ledger; edit the ledger rather than this -->")
END_MARKER = "<!-- ledger: end -->"

_EVIDENCE = re.compile(r"^[A-Za-z0-9._-]+\.(png|svg)$")
_COLOUR = re.compile(r"^#[0-9a-fA-F]{3,8}$")
_ID = re.compile(r"\bR\d+\.\d+\b")


# ---------------------------------------------------------------------------
# where things are
# ---------------------------------------------------------------------------
def _stem(note_path):
    return note_path[:-3] if note_path.endswith(".md") else note_path


def ledger_path(note_path):
    return _stem(note_path) + ".ledger.json"


def round_dir(note_path):
    return _stem(note_path)


def factory_path(note_path):
    return _stem(note_path) + ".factory.json"


def _rel(root, path):
    return os.path.relpath(path, root).replace(os.sep, "/")


def _read(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def _write(path, data):
    """Whole or not at all: a reader never sees half a ledger."""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    os.replace(tmp, path)


def _text(path, limit=2000000):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read(limit)
    except OSError:
        return ""


def _stat(path):
    try:
        s = os.stat(path)
        return "%d:%d" % (s.st_mtime_ns, s.st_size)
    except OSError:
        return "-"


def _mtime(path):
    try:
        return os.path.getmtime(path)
    except OSError:
        return 0


# ---------------------------------------------------------------------------
# splitting a round into requests
# ---------------------------------------------------------------------------
def _points(stroke):
    """A stroke's points as (x, y) pairs, whichever of the two stored shapes."""
    p = stroke.get("p") if isinstance(stroke, dict) else stroke
    out = []
    if not isinstance(p, list):
        return out
    num = (int, float)
    if p and isinstance(p[0], (list, tuple)):
        for q in p:
            if len(q) >= 2 and isinstance(q[0], num) and isinstance(q[1], num):
                out.append((float(q[0]), float(q[1])))
    else:
        for i in range(0, len(p) - 1, 2):
            if isinstance(p[i], num) and isinstance(p[i + 1], num):
                out.append((float(p[i]), float(p[i + 1])))
    return out


def _near(a, b, gap):
    return not (a[2] + gap < b[0] or b[2] + gap < a[0]
                or a[3] + gap < b[1] or b[3] + gap < a[1])


def _union(a, b):
    return [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])]


def clusters(strokes, gap=GAP):
    """The ink on one page, as regions: `[{box, strokes}]`, top to bottom.

    Single-link over each stroke's bounding box: two strokes within `gap` of
    each other are one request, and so is anything within `gap` of either.
    Points far outside the page (a slip of the nib off the edge) are ignored.
    """
    boxes = []
    for s in strokes or []:
        pts = [(x, y) for x, y in _points(s) if -0.2 <= x <= 1.2 and -0.2 <= y <= 1.2]
        if not pts:
            continue
        xs = [x for x, _ in pts]
        ys = [y for _, y in pts]
        boxes.append(([min(xs), min(ys), max(xs), max(ys)], s))
    parent = list(range(len(boxes)))

    def top(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            if _near(boxes[i][0], boxes[j][0], gap):
                a, b = top(i), top(j)
                if a != b:
                    parent[b] = a
    groups = {}
    for i, (box, s) in enumerate(boxes):
        g = groups.setdefault(top(i), {"box": list(box), "strokes": []})
        g["box"] = _union(g["box"], box)
        g["strokes"].append(s)
    out = list(groups.values())
    out.sort(key=lambda g: (round(g["box"][1], 3), g["box"][0]))
    return out


def paragraphs(text):
    """Typed feedback as requests: one per paragraph, a blank line between."""
    parts = re.split(r"\n[ \t]*\n", (text or "").strip())
    return [p.strip()[:TEXT_MAX] for p in parts if p.strip()]


def _slim(stroke):
    """A stroke as evidence: its colour, its width and at most 64 points.

    Not the whole record -- `annotate.js` persists its screen caches with every
    stroke, and a page of 299 strokes is 1.2 MB of them.
    """
    pts = _points(stroke)
    if len(pts) > POINTS_MAX:
        step = (len(pts) - 1) / float(POINTS_MAX - 1)
        pts = [pts[int(round(i * step))] for i in range(POINTS_MAX)]
    s = stroke if isinstance(stroke, dict) else {}
    c = s.get("c") if isinstance(s.get("c"), str) and _COLOUR.match(s.get("c")) else "#e8746c"
    try:
        w = float(s.get("w") or 2)
    except (TypeError, ValueError):
        w = 2.0
    out = {"c": c, "w": round(w, 2),
           "p": [round(v, 4) for xy in pts for v in xy]}
    if s.get("pg"):
        out["pg"] = 1
    return out


def split(repo, found, text, page=0, merge=()):
    """The requests one round would carry, unnumbered, in the order filed.

    `found` is `library.carried`'s answer: the marked pages that go. Each page's
    ink is clustered into regions, one request each -- unless its page is in
    `merge`, which is the filing panel saying *these marks are one request*.
    Then one request per typed paragraph, about `page` where there is one.
    """
    from ..lesson import notes as lesson_notes        # local: avoids a cycle

    merge = set(int(m) for m in merge or () if str(m).isdigit())
    strokes_of = lesson_notes.load_notes(repo) if found else {}
    items = []
    for mark in found or []:
        strokes = strokes_of.get(mark["key"]) or []
        regions = clusters(strokes)
        if mark["page"] in merge and len(regions) > 1:
            box = regions[0]["box"]
            for r in regions[1:]:
                box = _union(box, r["box"])
            regions = [{"box": box, "strokes": [s for r in regions for s in r["strokes"]]}]
        if not regions:
            # Ink the parser cannot read is still somebody's mark on this page.
            regions = [{"box": None, "strokes": strokes}]
        for r in regions:
            items.append({"kind": "ink", "page": mark["page"], "ann": mark["key"],
                          "box": ([round(v, 4) for v in r["box"]] if r["box"] else None),
                          "count": len(r["strokes"]),
                          "strokes": [_slim(s) for s in r["strokes"]],
                          "png": mark.get("png") or ""})
    for para in paragraphs(text):
        items.append({"kind": "text", "page": int(page or 0), "text": para})
    return items


def number(items, round_no, note_name):
    """Ids onto new requests: `R<round>.<n>` to show, `<note>#<n>` to keep."""
    for n, item in enumerate(items, start=1):
        item["id"] = "R%d.%d" % (round_no, n)
        item["key"] = "%s#%d" % (note_name, n)
    return items


def preview(repo, found, text, page=0, merge=(), round_no=1, reopen=()):
    """What the filing panel shows before anything is sent: the split, and
    the reopened requests that would ride with it. Nothing is written."""
    items = number(split(repo, found, text, page=page, merge=merge),
                   round_no, "")
    pages = {}
    for it in items:
        if it["kind"] == "ink":
            pages[it["page"]] = pages.get(it["page"], 0) + 1
    out = []
    for it in items:
        out.append({"id": it["id"], "kind": it["kind"], "page": it["page"],
                    "count": it.get("count") or 0,
                    "text": (it.get("text") or "")[:200],
                    "together": pages.get(it["page"], 0) if it["kind"] == "ink" else 0,
                    "merged": it["kind"] == "ink" and it["page"] in set(merge or ())})
    for it in reopen or []:
        out.append({"id": it["id"], "kind": "reopened", "page": it.get("page") or 0,
                    "count": 0, "text": (it.get("why") or "")[:200],
                    "together": 0, "merged": False})
    return out


# ---------------------------------------------------------------------------
# the evidence, kept with the round
# ---------------------------------------------------------------------------
def _page_size(pdf, page):
    """(width, height) of one page in points, or (0, 0)."""
    try:
        p = subprocess.run(["pdfinfo", "-f", str(page), "-l", str(page), pdf],
                           env=paper.raster_env(), stdin=subprocess.DEVNULL,
                           stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                           timeout=20)
        m = re.search(r"Page\s+%d size:\s+([\d.]+) x ([\d.]+)" % page,
                      p.stdout.decode("utf-8", "replace"))
        if m:
            return float(m.group(1)), float(m.group(2))
    except (OSError, subprocess.SubprocessError):
        pass
    return 0.0, 0.0


def _png_size(path):
    try:
        with open(path, "rb") as fh:
            head = fh.read(24)
        if head[:8] == b"\x89PNG\r\n\x1a\n":
            return struct.unpack(">II", head[16:24])
    except OSError:
        pass
    return 0, 0


def _padded(box):
    return [max(0.0, box[0] - PAD), max(0.0, box[1] - PAD),
            min(1.0, box[2] + PAD), min(1.0, box[3] + PAD)]


def _crop_png(pdf, page, box, aspect, prefix):
    """That region of the page, cut out by poppler. `(path, px box)` or None."""
    W = CROP_WIDTH
    H = int(round(W * aspect))
    x0, y0 = int(box[0] * W), int(box[1] * H)
    x1, y1 = int(round(box[2] * W)), int(round(box[3] * H))
    if x1 - x0 < 2 or y1 - y0 < 2:
        return None
    try:
        subprocess.run(["pdftoppm", "-png", "-f", str(page), "-l", str(page),
                        "-scale-to-x", str(W), "-scale-to-y", "-1",
                        "-x", str(x0), "-y", str(y0), "-W", str(x1 - x0),
                        "-H", str(y1 - y0), "-singlefile", pdf, prefix],
                       env=paper.raster_env(), stdin=subprocess.DEVNULL,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    got = prefix + ".png"
    return (got, (x0, y0, x1, y1)) if os.path.isfile(got) else None


def _svg(box, aspect, strokes, image=None):
    """One crop: the region `box` of a page, the page under it where there is
    one, and the ink over it. Self-contained, so `<img>` can show it."""
    W = CROP_WIDTH
    H = W * aspect
    vx, vy = box[0] * W, box[1] * H
    vw, vh = max(1.0, (box[2] - box[0]) * W), max(1.0, (box[3] - box[1]) * H)
    out = ['<svg xmlns="http://www.w3.org/2000/svg" '
           'xmlns:xlink="http://www.w3.org/1999/xlink" width="%d" height="%d" '
           'viewBox="%.1f %.1f %.1f %.1f">' % (vw, vh, vx, vy, vw, vh),
           '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="#fff"/>'
           % (vx, vy, vw, vh)]
    if image:
        data, (ix, iy, iw, ih) = image
        out.append('<image x="%.1f" y="%.1f" width="%.1f" height="%.1f" '
                   'xlink:href="data:image/png;base64,%s"/>'
                   % (ix, iy, iw, ih, base64.b64encode(data).decode("ascii")))
    for s in strokes:
        pts = _points(s)
        if not pts:
            continue
        width = s.get("w") or 2
        width = width * W / PAGE_REF if s.get("pg") else width * W / 800.0
        out.append('<polyline fill="none" stroke="%s" stroke-width="%.2f" '
                   'stroke-linecap="round" stroke-linejoin="round" points="%s"/>'
                   % (s.get("c") or "#e8746c", max(1.0, width),
                      " ".join("%.1f,%.1f" % (x * W, y * H) for x, y in pts)))
    out.append("</svg>")
    return "\n".join(out)


def _crop(repo, pdf, current, builds, item, where):
    """Write one inked request's crop into the round. Returns the file name.

    Cut from the PDF itself where the ink was drawn on the build that is on
    disk now, which is the ordinary case -- marked and sent in one sitting.
    From the rendering of the build it WAS drawn on where that one is still in
    the page cache. And ink alone, on white, where neither is: the marks still
    say where the complaint was.
    """
    box = item.get("box")
    if not box:
        return ""
    region = _padded(box)
    page = item["page"]
    drawn = (builds.get(item.get("ann")) or {}).get("digest") or current
    image, aspect = None, 0.0
    if pdf and drawn == current:
        w, h = _page_size(pdf, page)
        if w and h:
            aspect = h / w
            got = _crop_png(pdf, page, region, aspect,
                            os.path.join(where, ".crop-" + item["id"]))
            if got:
                try:
                    with open(got[0], "rb") as fh:
                        image = (fh.read(), got[1])
                finally:
                    try:
                        os.remove(got[0])
                    except OSError:
                        pass
    if image is None and drawn:
        files = paper.cached(repo, drawn)
        if 0 < page <= len(files):
            src = os.path.join(paper.cache_dir(repo), files[page - 1])
            pw, ph = _png_size(src)
            if pw and ph:
                aspect = ph / float(pw)
                try:
                    with open(src, "rb") as fh:
                        image = (fh.read(), (0, 0, CROP_WIDTH, CROP_WIDTH * aspect))
                except OSError:
                    image = None
    if not aspect:
        aspect = 1.294
    name = item["id"] + ".svg"
    with open(os.path.join(where, name), "w", encoding="utf-8") as fh:
        fh.write(_svg(region, aspect, item.get("strokes") or [], image))
    return name


def _git_head(root, src):
    """The commit whose copy of `src` is exactly the snapshot, or ""."""
    from .. import leaving                            # local: avoids a cycle

    try:
        if not leaving.git_here(root) or leaving.uncommitted(root, src):
            return ""
        p = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root,
                           stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL, timeout=10)
        return p.stdout.decode("utf-8", "replace").strip() if p.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def file_round(repo, doc, source_doc, note_path, round_no, items, ask, pdf):
    """Write the round's own directory and its ledger. Returns the ledger.

    THE CROPS AND PICTURES ARE COPIED HERE WHEN THE ROUND IS FILED, not when
    the live marks are wiped: `live/annotations/<page>.png` is one picture per
    page and the last save wins, so a copy taken later is a copy of whatever
    was drawn since.

    THE SOURCE IS SNAPSHOT, NOT COMMITTED. The board does not commit on
    somebody's behalf -- `rework_refused` is the rule and its reason holds for a
    correction too: a commit of a half-finished edit is a worse undo than none.
    `before.<ext>` is the source exactly as the turn found it, and the commit is
    recorded beside it where the source is clean at HEAD, so `git show` answers
    the same. The directory sits in `feedback/`, which is tracked, so
    `save-and-push.sh` carries it with the note and nothing else has to know.
    """
    from ..lesson import notes as lesson_notes        # local: avoids a cycle

    root = repo.root
    where = round_dir(note_path)
    os.makedirs(where, exist_ok=True)
    current = paper._digest(pdf, paper.PAGE_WIDTH) if pdf else ""
    builds = lesson_notes.load_notes_builds(repo) if any(
        i["kind"] == "ink" for i in items) else {}
    marked = {}
    for item in items:
        if item["kind"] != "ink":
            continue
        try:
            item["crop"] = _crop(repo, pdf, current, builds, item, where)
        except OSError:
            item["crop"] = ""
        item["drawn_on"] = (builds.get(item.get("ann")) or {}).get("digest") or current
        # THE WORDS UNDER THE INK, taken while the build they were drawn on is
        # the one on disk. Every later build re-anchors the ink to them, so a
        # pair follows its words through a recompile, not its page coordinates.
        # A round filed on an older build has none, and nothing needs it.
        if pdf and item["drawn_on"] == current and item.get("box"):
            try:
                got = under(pdf, item["page"], item["box"])
            except (OSError, ValueError, IndexError):
                got = None
            if got:
                item["under"] = got
        png = item.pop("png", "")
        if png and item["page"] not in marked:
            name = "marked-p%d.png" % item["page"]
            try:
                shutil.copyfile(os.path.join(root, *png.split("/")),
                                os.path.join(where, name))
                marked[item["page"]] = name
            except OSError:
                marked[item["page"]] = ""
        item["marked"] = marked.get(item["page"], "")
    src = (source_doc or doc).get("source") or ""
    before = {"file": "", "commit": "", "source": src}
    if src:
        ext = os.path.splitext(src)[1] or ".txt"
        try:
            shutil.copyfile(os.path.join(root, *src.split("/")),
                            os.path.join(where, "before" + ext))
            before["file"] = "before" + ext
            before["commit"] = _git_head(root, src)
        except OSError:
            pass
    name = os.path.basename(note_path)
    _write(os.path.join(where, "items.json"), items)
    led = {
        "version": 1,
        "note": name,
        "round": round_no,
        "document": doc["id"],
        "title": doc.get("title") or "",
        "ask": ask,
        "source": src,
        "pdf": doc.get("rel") or "",
        "filed": time.strftime("%Y-%m-%d %H:%M"),
        "before": before,
        "how_to_answer": (
            "One entry in `answers` per id in `items`, keyed by the id: "
            "{\"disposition\": \"done\" | \"partly\" | \"not done\" | "
            "\"pushed back\", \"did\": \"one sentence of what you did; for not "
            "done and pushed back, the reply the owner reads beside their "
            "ink\", \"new\": \"the new wording of the passage you changed, "
            "copied exactly from the source (required for done and partly)\"}. "
            "An id you could not find is still answered: not done, saying so. "
            "Change nothing else in this file."),
        "items": [_for_turn(root, note_path, i) for i in items],
        "answers": {},
    }
    _write(ledger_path(note_path), led)
    return led


def _for_turn(root, note_path, item):
    """A request as the turn reads it: no strokes, the crop as a path."""
    out = {"id": item["id"], "kind": item["kind"], "page": item.get("page") or 0}
    if item.get("text"):
        out["text"] = item["text"]
    if item["kind"] == "ink":
        out["strokes"] = item.get("count") or 0
    crop = _crop_path(note_path, item)
    if crop:
        out["crop"] = _rel(root, crop)
    if item.get("marked"):
        out["page_image"] = _rel(root, os.path.join(round_dir(note_path), item["marked"]))
    if item["kind"] == "reopened":
        out["reopened_because"] = item.get("why") or ""
        if item.get("previous"):
            out["last_answer"] = item["previous"]
    return out


def _crop_path(note_path, item):
    """Where an item's crop is -- in its own round, or the round it was
    first filed in when it has been reopened into this one."""
    crop = item.get("crop") or ""
    if not crop:
        return ""
    home = item.get("from") or os.path.basename(note_path)
    return os.path.join(os.path.dirname(note_path), _stem(home), crop)


# ---------------------------------------------------------------------------
# the rounds on one document
# ---------------------------------------------------------------------------
def rounds(root, doc, every=False):
    """`[(note rec, note path)]` of every round with a ledger, oldest first.

    A round whose revision was never asked (`unsent`) is left out unless
    `every`: nothing is answering it, its requests went again with the retry,
    and counting it would count them twice.
    """
    from . import library                             # local: avoids a cycle

    where = library.feedback_dir(root, doc)
    out = []
    for rec in library.notes(root, doc):
        path = os.path.join(where, rec["name"])
        if os.path.isfile(ledger_path(path)) and (every or not unsent(path)):
            out.append((rec, path))
    return out


def unsent(note_path):
    return os.path.isfile(os.path.join(round_dir(note_path), "unsent.json"))


def mark_unsent(note_path, why=""):
    """The revision for this round could not be asked. The round stays on
    disk as a record and is counted nowhere; the retry files a new one."""
    where = round_dir(note_path)
    try:
        os.makedirs(where, exist_ok=True)
        _write(os.path.join(where, "unsent.json"),
               {"at": time.strftime("%Y-%m-%d %H:%M"), "why": str(why or "")[:400]})
    except OSError:
        pass


def next_round(root, doc):
    """The next round's number: past every round there has been, the unsent
    included. Never a count of the notes on disk, because a note deleted
    would hand its number -- and its ids -- to the next round."""
    from . import library                             # local: avoids a cycle

    high = len(library.notes(root, doc))
    for _rec, path in rounds(root, doc, every=True):
        try:
            high = max(high, int((_read(ledger_path(path), {}) or {}).get("round") or 0))
        except (TypeError, ValueError):
            continue
    return high + 1


def _landed_here(root, doc, note_path):
    """Whether one round has come back, the way `view` decides it: a newer
    sent round filed after it counts."""
    rs = [p for _r, p in rounds(root, doc)]
    if note_path not in rs:
        return False
    later = rs.index(note_path) < len(rs) - 1
    return bool(check(root, doc, note_path, later=later).get("landed"))


def items_of(note_path):
    """The requests of one round, as filed. The round's copy wins over the
    ledger's, which a turn may have rewritten."""
    got = _read(os.path.join(round_dir(note_path), "items.json"))
    if isinstance(got, list):
        return got
    led = _read(ledger_path(note_path), {}) or {}
    return [i for i in led.get("items") or [] if isinstance(i, dict) and i.get("id")]


def states_of(note_path):
    got = _read(os.path.join(round_dir(note_path), "states.json"), {})
    return got if isinstance(got, dict) else {}


def reopened(root, doc):
    """Every request reopened on a landed round and not yet carried into a
    newer one, as items for the next round -- WITH THE ID IT ALREADY HAS."""
    out = []
    rs = rounds(root, doc)
    for n, (rec, path) in enumerate(rs):
        states = states_of(path)
        if not any((v or {}).get("state") == "reopened" and not (v or {}).get("carried")
                   for v in states.values()):
            continue
        # A request is reopened on a round that CAME BACK, never on one the
        # revision is still working on: that one is not done yet, not undone.
        checked = check(root, doc, path, later=n < len(rs) - 1)
        if not checked.get("landed"):
            continue
        answers = checked.get("items") or {}
        for item in items_of(path):
            st = states.get(item["id"]) or {}
            if st.get("state") != "reopened" or st.get("carried"):
                continue
            ans = (answers.get(item["id"]) or {}).get("answer") or {}
            out.append({
                "id": item["id"], "key": item.get("key") or "",
                "kind": "reopened", "page": item.get("page") or 0,
                "was": item.get("was") or item.get("kind"),
                "text": item.get("text") or "",
                "box": item.get("box"), "crop": item.get("crop") or "",
                # The ink rides with it, so the next round's pair still shows
                # what was written and where.
                "strokes": item.get("strokes") or [],
                "drawn_on": item.get("drawn_on") or "",
                "under": item.get("under"),
                "from": item.get("from") or rec["name"],
                "reopened_in": rec["name"],
                "why": st.get("why") or "",
                "previous": ("%s: %s" % (ans.get("disposition"), ans.get("did") or "")
                             if ans else ""),
            })
    return out


def carry(root, doc, items, into):
    """Record that these reopened requests now ride the round `into`."""
    from . import library                             # local: avoids a cycle

    where = library.feedback_dir(root, doc)
    by_round = {}
    for it in items or []:
        if it.get("kind") == "reopened" and it.get("reopened_in"):
            by_round.setdefault(it["reopened_in"], []).append(it["id"])
    for name, ids in by_round.items():
        path = os.path.join(where, name)
        states = states_of(path)
        for i in ids:
            states.setdefault(i, {"state": "reopened"})["carried"] = into
        try:
            _write(os.path.join(round_dir(path), "states.json"), states)
        except OSError:
            continue


def set_state(root, doc, note_name, item_id, state, why=""):
    """Close or reopen one request, from the glass. `{ok, ...}`."""
    from . import library                             # local: avoids a cycle

    state = str(state or "").strip().lower()
    if state not in STATES:
        return {"ok": False, "error": "a request is open, accepted or reopened"}
    found = [r for r in library.notes(root, doc) if r["name"] == note_name]
    if not found:
        return {"ok": False, "error": "no such round of feedback on this document"}
    path = os.path.join(library.feedback_dir(root, doc), found[0]["name"])
    if not any(i["id"] == item_id for i in items_of(path)):
        return {"ok": False, "error": "that round has no request %s" % item_id}
    if unsent(path):
        return {"ok": False, "error": ("that round was never sent: its requests "
                                       "went again with the next one")}
    if not _landed_here(root, doc, path):
        return {"ok": False, "error": ("the revision has not come back yet: a "
                                       "request is accepted or reopened once "
                                       "it has been answered")}
    why = str(why or "").strip()[:TEXT_MAX]
    if state == "reopened" and len(why) < 3:
        return {"ok": False, "error": "say in a line why it is not done yet"}
    states = states_of(path)
    if (states.get(item_id) or {}).get("carried"):
        return {"ok": False, "error": ("%s already rides the round %s: answer it "
                                       "there" % (item_id, states[item_id]["carried"]))}
    states[item_id] = {"state": state, "why": why,
                       "at": time.strftime("%Y-%m-%d %H:%M")}
    os.makedirs(round_dir(path), exist_ok=True)
    _write(os.path.join(round_dir(path), "states.json"), states)
    return {"ok": True, "id": item_id, "state": state, "why": why}


def summary(root, doc):
    """What a document's row says: `{rounds, items, open, reopened}`.

    Every request on the document, counted once: one reopened into a later
    round is counted in the round it rides, not in the one it came from.
    """
    out = {"rounds": 0, "items": 0, "open": 0, "reopened": 0}
    for _rec, path in rounds(root, doc):
        states = states_of(path)
        out["rounds"] += 1
        for it in items_of(path):
            st = states.get(it["id"]) or {}
            if st.get("carried"):
                continue
            out["items"] += 1
            if st.get("state") != "accepted":
                out["open"] += 1
            if st.get("state") == "reopened":
                out["reopened"] += 1
    return out


def evidence(root, doc, note_name, file_name):
    """The path of one file in one round's directory, or "". Names only,
    matched against what is there -- never a path joined from a browser."""
    from . import library                             # local: avoids a cycle

    if not _EVIDENCE.match(file_name or ""):
        return ""
    for rec in library.notes(root, doc):
        if rec["name"] != note_name:
            continue
        where = round_dir(os.path.join(library.feedback_dir(root, doc), rec["name"]))
        try:
            names = os.listdir(where)
        except OSError:
            return ""
        return os.path.join(where, file_name) if file_name in names else ""
    return ""


def keep_evidence(repo, doc):
    """Before the live marks go, every round keeps the pictures it points at.

    `file_round` copies them when a round is filed, so this finds nothing to do
    unless the copy failed then; it is the guard `wipe_delivered` runs first,
    because a mark that was delivered must not be delivered twice, and a
    request must not lose its picture for it.
    """
    root = repo.root
    for _rec, path in rounds(root, doc):
        where = round_dir(path)
        items = items_of(path)
        changed = False
        for it in items:
            if it.get("kind") != "ink" or it.get("marked") or not it.get("ann"):
                continue
            from ..server.routes import writing       # local: avoids a cycle

            live = os.path.join(repo.notes, writing.ann_file(it["ann"]) + ".png")
            name = "marked-p%d.png" % it["page"]
            if not os.path.isfile(os.path.join(where, name)) and os.path.isfile(live):
                try:
                    os.makedirs(where, exist_ok=True)
                    shutil.copyfile(live, os.path.join(where, name))
                except OSError:
                    continue
            if os.path.isfile(os.path.join(where, name)):
                it["marked"] = name
                changed = True
        if changed:
            try:
                _write(os.path.join(where, "items.json"), items)
            except OSError:
                pass


# ---------------------------------------------------------------------------
# the answers: validated, never trusted
# ---------------------------------------------------------------------------
def _answers(led):
    """The turn's answers as `{id: dict}`, whichever of two shapes it wrote."""
    got = (led or {}).get("answers")
    out = {}
    if isinstance(got, dict):
        for k, v in got.items():
            if isinstance(v, dict):
                out[str(k).strip()] = v
    elif isinstance(got, list):
        for v in got:
            if isinstance(v, dict) and v.get("id"):
                out[str(v["id"]).strip()] = v
    return out


def disposition(word):
    w = re.sub(r"\s+", " ", str(word or "").strip().lower())
    w = _SAME.get(w, w)
    return w if w in DISPOSITIONS else ""


def landed(root, doc, note_path, later=False):
    """Did this round come back? A newer round filed after it, an answer in
    its ledger, the factory's record beside it, the board's own summary under
    the note, or a PDF built after the note was written."""
    from . import library                             # local: avoids a cycle

    if later:
        return True
    if _answers(_read(ledger_path(note_path), {})):
        return True
    if os.path.isfile(factory_path(note_path)):
        return True
    if "## What was changed" in _text(note_path, library.NOTE_BYTES):
        return True
    pdf = library.path_of(root, doc, ".pdf")
    return bool(pdf) and _mtime(pdf) >= _mtime(note_path)


def from_factory(items, record):
    """Paper-Writer's applied edits as answers. `(answers, extra)`.

    THE FACTORY'S RECORD IS OF WHAT LANDED, not of what was proposed: its
    editor's `{issue, find, replace}` edits with whether each applied. An edit
    names the request it answers by the id in its `issue`. A request with every
    edit applied is done, one with some is partly, one whose edits all failed
    is not done -- and one no edit names is not answered. Edits naming no
    request are the factory's own, and are listed rather than dropped.
    """
    ids = set(i["id"] for i in items)
    by_id, extra = {}, []
    for e in (record or {}).get("edits") or []:
        if not isinstance(e, dict):
            continue
        named = [m for m in _ID.findall(str(e.get("issue") or "")) if m in ids]
        if not named:
            extra.append({"issue": str(e.get("issue") or "")[:400],
                          "old": str(e.get("find") or "")[:800],
                          "new": str(e.get("replace") or "")[:800],
                          "applied": bool(e.get("applied"))})
            continue
        for i in named:
            by_id.setdefault(i, []).append(e)
    out = {}
    for i, edits in by_id.items():
        applied = [e for e in edits if e.get("applied")]
        # An issue the editor retried on a later sweep and landed is landed: a
        # refusal it then got past is not a part left undone.
        issues = {}
        for e in edits:
            k = re.sub(r"\s+", " ", str(e.get("issue") or "")).strip().lower()
            issues[k] = issues.get(k, False) or bool(e.get("applied"))
        disp = ("done" if all(issues.values())
                else "partly" if applied else "not done")
        first = (applied or edits)[0]
        did = re.sub(r"^\s*\[?R\d+\.\d+\]?[:\s-]*", "", str(first.get("issue") or ""))
        if not applied:
            did = "the factory's edit did not apply: %s" % (
                first.get("why") or "its anchor was not found")
        new = "\n".join(str(e.get("replace") or "") for e in applied
                        if str(e.get("replace") or "").strip())[:1600]
        rec = {"disposition": disp, "did": did[:400],
               "old": "\n".join(str(e.get("find") or "") for e in applied)[:1600],
               "new": new, "by": "paper-writer"}
        # A STRUCTURAL EDIT -- a section moved or cut -- has no new wording and
        # did apply. It is placed by what it moved rather than flagged for
        # wording it never had.
        if applied and not new:
            rec["anchor"] = "\n".join(str(e.get("find") or "") for e in applied)[:400]
        out[i] = rec
    return out, extra


# The shape of `checked.json`. A change to what an answer carries bumps it, so
# a cache written before the change is validated again rather than read short.
CHECK_V = "v2:"


def check(root, doc, note_path, later=False):
    """The round's answers, validated against its requests. Cached in the
    round's directory on the ledger's own stat, so it runs once per change.

    `{key, landed, items: {id: {status, answer, problems}}, unknown, extra}`,
    where `status` is `answered`, `not answered`, or `waiting` for a round
    whose turn has not come back yet. A turn that answers nothing leaves every
    request NOT ANSWERED once the round lands; it is never a silent round.
    """
    where = round_dir(note_path)
    is_in = landed(root, doc, note_path, later)
    fac = factory_path(note_path)
    key = "%s%s|%s|%d" % (CHECK_V, _stat(ledger_path(note_path)), _stat(fac),
                          int(is_in))
    cache = os.path.join(where, "checked.json")
    got = _read(cache, {}) or {}
    if got.get("key") == key:
        return got
    led = _read(ledger_path(note_path), None)
    items = items_of(note_path)
    answers = _answers(led)
    extra = []
    if os.path.isfile(fac) and all(a.get("by") == "paper-writer"
                                   for a in answers.values()):
        fresh, extra = from_factory(items, _read(fac, {}))
        # THE LEDGER IS THE CONTRACT, whoever answered it: the factory's
        # answers are written into it, and again only if a re-delivery changed
        # them -- so the stat moves once per delivery.
        if fresh != answers:
            answers = fresh
            if isinstance(led, dict):
                led["answers"] = answers
                try:
                    _write(ledger_path(note_path), led)
                except OSError:
                    pass
                key = "%s%s|%s|%d" % (CHECK_V, _stat(ledger_path(note_path)),
                                      _stat(fac), int(is_in))
    before, after = _snapshots(root, doc, led or {}, note_path,
                               is_in and bool(answers))
    out, ids = {}, set()
    for item in items:
        ids.add(item["id"])
        a = answers.get(item["id"])
        if not a:
            out[item["id"]] = {"status": "not answered" if is_in else "waiting",
                               "answer": None, "problems": []}
            continue
        problems = []
        disp = disposition(a.get("disposition"))
        if not disp:
            problems.append("its disposition, %r, is not one of %s"
                            % (str(a.get("disposition") or "")[:40],
                               ", ".join(DISPOSITIONS)))
        new = str(a.get("new") or a.get("new_wording") or "").strip()[:TEXT_MAX]
        anchor = str(a.get("anchor") or "").strip()[:400]
        if disp in WORDED and not new and not anchor:
            problems.append("it says %s but gives no new wording" % disp)
        old, now = _pair_for(before, after, new)
        old_from = "before"
        if not old and a.get("old"):
            old, now, old_from = str(a.get("old")).strip()[:TEXT_MAX], "", "turn"
        if not old:
            old_from = ""
        out[item["id"]] = {
            "status": "answered" if disp else "not answered",
            "answer": ({"disposition": disp, "did": str(a.get("did") or "").strip()[:600],
                        "new": new, "old": old, "old_from": old_from,
                        "now": now,
                        "anchor": anchor,
                        "by": a.get("by") or "turn"} if disp else None),
            "problems": problems}
    got = {"key": key, "landed": is_in, "items": out,
           "unknown": sorted(k for k in answers if k not in ids), "extra": extra,
           # A ledger the turn left as something other than JSON: every request
           # is then unanswered, and the reader says why.
           "broken": led is None and os.path.isfile(ledger_path(note_path))}
    try:
        os.makedirs(where, exist_ok=True)
        _write(cache, got)
    except OSError:
        pass
    if is_in:
        try:
            _summarise(root, note_path, led or {}, items, got)
        except OSError:
            pass
    return got


def _snapshots(root, doc, led, note_path, take_after):
    """`(before, after)` source text.

    THE AFTER-COPY IS TAKEN ONCE, and an existing one is never replaced: a
    re-validation (a checkout, a clone, a touch moves the ledger's stat) must
    not copy a later round's edits over this round's answer. Taken from the
    next round's `before` where one was filed, which is the source as this
    round left it; from the live source otherwise.
    """
    where = round_dir(note_path)
    b = (led.get("before") or {}).get("file") or ""
    before = _text(os.path.join(where, b)) if b else ""
    src = led.get("source") or ""
    after = ""
    if src:
        ext = os.path.splitext(src)[1] or ".txt"
        dest = os.path.join(where, "after" + ext)
        if take_after and not os.path.isfile(dest):
            origin = _next_before(root, doc, note_path, src) \
                or os.path.join(root, *src.split("/"))
            try:
                shutil.copyfile(origin, dest)
            except OSError:
                pass
        after = _text(dest)
    return before, after


def _next_before(root, doc, note_path, src):
    """The `before` snapshot of the first round filed after this one on the
    same source, or ""."""
    rs = [p for _r, p in rounds(root, doc, every=True)]
    if note_path not in rs:
        return ""
    for path in rs[rs.index(note_path) + 1:]:
        led = _read(ledger_path(path), {}) or {}
        if led.get("source") != src:
            continue
        b = (led.get("before") or {}).get("file") or ""
        got = os.path.join(round_dir(path), b) if b else ""
        if got and os.path.isfile(got):
            return got
    return ""


def _old_for(before, after, new):
    """The exact old wording of the passage `new` now occupies, or "".

    Out of the snapshots rather than out of the turn's memory: find the new
    wording in the after-copy, diff the two copies line by line, and take the
    before side of every change that touches those lines.
    """
    return _pair_for(before, after, new)[0]


def _pair_for(before, after, new):
    """`(old, now)`: both sides of every line change touching `new`.

    `now` is the after side of the same changes, so a word diff of the two
    compares like with like -- whole changed lines -- rather than a paragraph
    against the one sentence of it the turn quoted.
    """
    if not (before and after and new):
        return "", ""
    at = after.find(new)
    if at < 0:
        at = _fuzzy_find(after, new)
    if at < 0:
        return "", ""
    a_lines = after.splitlines(True)
    b_lines = before.splitlines(True)
    # which after-lines the new wording spans
    pos, first, last = 0, None, None
    end = at + len(new)
    for n, line in enumerate(a_lines):
        if first is None and pos + len(line) > at:
            first = n
        if pos < end:
            last = n
        pos += len(line)
    if first is None:
        return "", ""
    old, now = [], []
    sm = difflib.SequenceMatcher(None, b_lines, a_lines, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        if not (j2 > first and j1 <= last or (j1 == j2 and first <= j1 <= last + 1)):
            continue
        if tag == "replace" and (i2 - i1 > 1 or j2 - j1 > 1):
            # ONE BLOCK OF SEVERAL CHANGED PARAGRAPHS: each new line the wording
            # spans is paired with the old line most like it, so two requests
            # answered in neighbouring paragraphs do not share one diff.
            mine = [j for j in range(j1, j2) if first <= j <= last]
            took = []
            for j in mine:
                aw = a_lines[j].split()
                best, score = None, 0.0
                for i in range(i1, i2):
                    r = difflib.SequenceMatcher(None, b_lines[i].split(), aw,
                                                autojunk=False).ratio()
                    if r > score:
                        best, score = i, r
                if best is not None and score >= 0.3 and best not in took:
                    took.append(best)
            if mine and took:
                old.extend(b_lines[i] for i in sorted(took))
                now.extend(a_lines[j] for j in mine)
                continue
        old.extend(b_lines[i1:i2])
        now.extend(a_lines[j1:j2])
    return "".join(old).strip()[:TEXT_MAX], "".join(now).strip()[:TEXT_MAX]


def _fuzzy_find(text, passage):
    """Where `passage` starts in `text` with whitespace ignored, or -1."""
    words = passage.split()
    if not words:
        return -1
    pat = r"\s+".join(re.escape(w) for w in words[:40])
    m = re.search(pat, text)
    return m.start() if m else -1


def _summarise(root, note_path, led, items, got):
    """`## What was changed` under the note, WRITTEN FROM THE LEDGER.

    The note stays the human-readable record and the ledger is the contract,
    so the prose is generated rather than written twice. Everything after the
    marker is the board's and is rewritten each time the answers change.
    """
    text = _text(note_path)
    tail = ""
    if MARKER in text:
        head, rest = text.split(MARKER, 1)
        # Anything written after the board's block -- a turn's own prose, say --
        # is somebody else's and survives the block being rewritten.
        tail = rest.split(END_MARKER, 1)[1] if END_MARKER in rest else ""
        text = head.rstrip() + "\n"
    rows = got["items"]
    answered = sum(1 for i in items if rows.get(i["id"], {}).get("status") == "answered")
    lines = ["", MARKER, "", "## What was changed", "",
             "Written by the board from `%s`: %d of %d request%s answered."
             % (_rel(root, ledger_path(note_path)), answered, len(items),
                "" if len(items) == 1 else "s"), ""]
    for item in items:
        r = rows.get(item["id"]) or {}
        a = r.get("answer")
        where = " (page %d)" % item["page"] if item.get("page") else ""
        if not a:
            lines.append("- **%s**%s -- NOT ANSWERED: the turn wrote nothing a "
                         "reader can use for this request." % (item["id"], where))
            continue
        lines.append("- **%s**%s -- %s: %s" % (item["id"], where, a["disposition"],
                                              a["did"] or "(no sentence given)"))
        for p in r.get("problems") or []:
            lines.append("  - but %s" % p)
    for x in got.get("extra") or []:
        lines.append("- the factory's own: %s" % x["issue"])
    lines += ["", END_MARKER, ""]
    with open(note_path, "w", encoding="utf-8") as fh:
        fh.write(text.rstrip() + "\n" + "\n".join(lines) + tail.lstrip("\n"))


# ---------------------------------------------------------------------------
# placing an answer on the new pages
# ---------------------------------------------------------------------------
_WORDS = {}
_WORD_RE = re.compile(
    r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</word>')
_PAGE_RE = re.compile(r'<page width="([\d.]+)" height="([\d.]+)">')
_FOLD = {"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
         "\u2013": "-", "\u2014": "-", "\u2212": "-", "\u00ad": "-"}


def _norm(word):
    """One word as it is compared: ligatures and quotes folded, case and
    punctuation gone, and hyphens dropped, so `counter-factual` in a source
    meets `counter-` / `factual` broken across two lines of the PDF."""
    w = unicodedata.normalize("NFKC", word or "")
    for a, b in _FOLD.items():
        w = w.replace(a, b)
    w = w.lower().replace("-", "")
    return re.sub(r"[^\w]", "", w)


def words(pdf):
    """Every word of a PDF with where it is: `(pages, [(page, x0, y0, x1, y1,
    norm)])`. `pages` is `[(width, height)]` in points, origin top-left. A
    word hyphenated across a line break comes back as one word."""
    key = (os.path.realpath(pdf), _mtime(pdf))
    if key in _WORDS:
        return _WORDS[key]
    try:
        p = subprocess.run(["pdftotext", "-bbox", pdf, "-"], env=paper.raster_env(),
                           stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL, timeout=60)
        xml = p.stdout.decode("utf-8", "replace")
    except (OSError, subprocess.SubprocessError):
        xml = ""
    sizes, raw = [], []
    for chunk in xml.split("</page>"):
        m = _PAGE_RE.search(chunk)
        if not m:
            continue
        sizes.append((float(m.group(1)), float(m.group(2))))
        n = len(sizes)
        for w in _WORD_RE.finditer(chunk[m.end():]):
            raw.append([n, float(w.group(1)), float(w.group(2)), float(w.group(3)),
                        float(w.group(4)), html.unescape(w.group(5))])
    out = []
    i = 0
    while i < len(raw):
        w = raw[i]
        text = unicodedata.normalize("NFKC", w[5])
        if (text.endswith("-") or text.endswith("\u00ad")) and i + 1 < len(raw) \
                and raw[i + 1][0] == w[0] and raw[i + 1][2] > w[2]:
            nxt = raw[i + 1]
            out.append((w[0], w[1], w[2], w[3], w[4], _norm(text[:-1] + nxt[5]),
                        (nxt[1], nxt[2], nxt[3], nxt[4])))
            i += 2
            continue
        norm = _norm(text)
        if norm:
            out.append((w[0], w[1], w[2], w[3], w[4], norm, None))
        i += 1
    if len(_WORDS) > 16:
        _WORDS.clear()
    _WORDS[key] = (sizes, out)
    return sizes, out


_TEX_DROP = re.compile(r"\\(?:cite\w*|ref|eqref|label|autoref|cref|Cref|url|footnote)"
                       r"\s*(?:\[[^\]]*\])*\s*\{[^}]*\}")
_TEX_CMD = re.compile(r"\\[a-zA-Z@]+\*?\s*(?:\[[^\]]*\])?")
_MATH = re.compile(r"\$\$.*?\$\$|\$[^$]*\$|\\\(.*?\\\)|\\\[.*?\\\]", re.S)


# Inline math as the diff shows it: the few symbols a sentence carries, by
# their glyph. Anything else loses its backslash and keeps its name.
_GLYPH = {"alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "epsilon": "ε",
          "lambda": "λ", "mu": "μ", "pi": "π", "rho": "ρ", "sigma": "σ",
          "tau": "τ", "theta": "θ", "chi": "χ", "le": "≤", "leq": "≤", "ge": "≥",
          "geq": "≥", "ne": "≠", "neq": "≠", "approx": "≈", "times": "×",
          "pm": "±", "to": "→", "infty": "∞", "cdot": "·", "sim": "~"}


def _math_words(m):
    """One piece of math as it reads: delimiters, braces and backslashes off."""
    t = m.group(0)
    t = re.sub(r"^(\$\$|\$|\\\(|\\\[)|(\$\$|\$|\\\)|\\\])$", "", t)
    t = re.sub(r"\\([a-zA-Z]+)", lambda c: _GLYPH.get(c.group(1), c.group(1)), t)
    t = re.sub(r"[{}^_\\]", "", t)
    return " %s " % t.strip()


def plain(source_text, tex=True, math=False):
    """Source wording as it reads on the page: LaTeX and Markdown taken off.

    `%` starts a comment in LaTeX only. In Markdown -- what Paper-Writer
    delivers -- it is a percent sign, and `5% were excluded` is five words.
    Math is dropped for matching against the PDF's words; with `math`, as a
    diff shows it to the owner, it is kept as it reads (`k=300`, `α=1`), so
    "near $k=300$" never reads as "near".
    """
    t = source_text or ""
    if tex:
        t = re.sub(r"(?<!\\)%.*", " ", t)
    t = _MATH.sub(_math_words if math else " ", t)
    t = _TEX_DROP.sub(" ", t)
    t = _TEX_CMD.sub(" ", t)
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", t)
    t = re.sub(r"[{}~*_`#>|\\]", " ", t)
    return t


def place(pdf, wording, hint=0, tex=True):
    """Where `wording` is on the PDF: `{page, box, by, score}`, or None.

    Scored rather than first-found: *considered* is on five pages of the deck
    this was built against. The rarest of the passage's first few words anchors
    every candidate, each candidate window is scored by how much of the passage
    it holds in order, and a tie goes to the page nearest `hint`. The box is the
    matched words on the page the match starts on, in fractions of that page.
    """
    tokens = [t for t in (_norm(w) for w in plain(wording, tex).split()) if t][:40]
    if not tokens:
        return None
    sizes, ws = words(pdf)
    if not ws:
        return None
    seq = [w[5] for w in ws]
    freq = {}
    for t in seq:
        freq[t] = freq.get(t, 0) + 1
    head = tokens[:4]
    offset = min(range(len(head)), key=lambda k: (freq.get(head[k], 0) or 10 ** 9))
    anchor = head[offset]
    if not freq.get(anchor):
        present = [k for k, t in enumerate(tokens) if freq.get(t)]
        if not present:
            return None
        offset = min(present, key=lambda k: freq[tokens[k]])
        anchor = tokens[offset]
    span = len(tokens) + 6
    best = None
    for i, t in enumerate(seq):
        if t != anchor:
            continue
        start = max(0, i - offset - 2)
        window = seq[start:start + span]
        sm = difflib.SequenceMatcher(None, window, tokens, autojunk=False)
        blocks = [b for b in sm.get_matching_blocks() if b.size]
        got = sum(b.size for b in blocks)
        score = got / float(len(tokens))
        hit = [start + b.a + k for b in blocks for k in range(b.size)]
        page = ws[hit[0]][0] if hit else ws[i][0]
        rank = (round(score, 3), -abs(page - hint) if hint else 0)
        if best is None or rank > best[0]:
            best = (rank, score, hit, page)
    if not best or best[1] < (1.0 if len(tokens) < 3 else 0.6):
        return None
    _rank, score, hit, page = best
    boxes = []
    for k in hit:
        w = ws[k]
        if w[0] == page:
            boxes.append(w[1:5])
    if not boxes:
        return None
    pw, ph = sizes[page - 1]
    box = [min(b[0] for b in boxes) / pw, min(b[1] for b in boxes) / ph,
           max(b[2] for b in boxes) / pw, max(b[3] for b in boxes) / ph]
    return {"page": page, "box": [round(v, 4) for v in box], "by": "text",
            "score": round(score, 3)}


# HOW MANY WORDS UNDER A MARK ARE KEPT. Enough to find the passage again on a
# rebuilt PDF; a ring round a whole paragraph is still found by its first forty.
UNDER_MAX = 40
# How far past the ink a word may sit and still be under it: a ring is drawn
# round a word, not on it.
UNDER_PAD = 0.006
# The fewest words a half of them may be looked for by, when the whole run is
# not on the page any more: fewer is a phrase found anywhere.
PART_MIN = 5


def under(pdf, page, box):
    """The words of `pdf` under the ink box on `page`: `{page, box, text}`.

    WHOLE LINES, not the words inside the box: a ring round half a line, or
    a note in the margin beside it, is about that line, and the words of a
    line are a run `place` can find again -- the scattered right halves of
    three lines are not. The lines level with the box, a little padded, in
    reading order; past `UNDER_MAX` words, the run of that many centred on
    the word nearest the middle of the mark. As the folded words `place`
    compares. None where the page has no words level with the ink.
    """
    if not (pdf and box and page):
        return None
    sizes, ws = words(pdf)
    if not (0 < page <= len(sizes)):
        return None
    pw, ph = sizes[page - 1]
    y0, y1 = box[1] - UNDER_PAD, box[3] + UNDER_PAD
    hit = [w for w in ws if w[0] == page and w[2] / ph <= y1 and w[4] / ph >= y0]
    if not hit:
        return None
    if len(hit) > UNDER_MAX:
        cx, cy = (box[0] + box[2]) / 2 * pw, (box[1] + box[3]) / 2 * ph
        mid = min(range(len(hit)), key=lambda i: (
            ((hit[i][1] + hit[i][3]) / 2 - cx) ** 2
            + ((hit[i][2] + hit[i][4]) / 2 - cy) ** 2))
        start = max(0, min(mid - UNDER_MAX // 2, len(hit) - UNDER_MAX))
        hit = hit[start:start + UNDER_MAX]
    return {"page": page,
            "box": [round(min(w[1] for w in hit) / pw, 4),
                    round(min(w[2] for w in hit) / ph, 4),
                    round(max(w[3] for w in hit) / pw, 4),
                    round(max(w[4] for w in hit) / ph, 4)],
            "text": " ".join(w[5] for w in hit)}


def ink_where(pdf, digest, item):
    """Where an inked request's words are on THIS build: `{by, page, box, dx, dy}`.

    `same` where the ink was drawn on this very build, so it sits where it
    was drawn. `text` where the words under it were found again, with the
    shift from where they were. `gone` where they are not in the document any
    more. None for a request with no ink.
    """
    if not item.get("strokes") and not item.get("under"):
        return None
    page = int(item.get("page") or 0)
    if digest and item.get("drawn_on") == digest:
        return {"by": "same", "page": page, "box": item.get("box"), "dx": 0, "dy": 0}
    was = item.get("under") or {}
    if not was.get("text"):
        # FILED OFF AN OLDER BUILD, so no words were kept to look for. That is
        # not evidence the words went: the ink sits where it was drawn, as the
        # live ink on a rebuilt page does.
        return {"by": "drawn", "page": page, "box": item.get("box"), "dx": 0, "dy": 0}
    found = place(pdf, was.get("text") or "", hint=page, tex=False) \
        if pdf and was.get("text") else None
    if found and found.get("box") and was.get("box"):
        return {"by": "text", "page": found["page"], "box": found["box"],
                "dx": round(found["box"][0] - was["box"][0], 4),
                "dy": round(found["box"][1] - was["box"][1], 4)}
    # THE WORDS WERE EDITED, NOT ALL OF THEM GONE. The revision usually
    # rewrites the line the ink was about and leaves its neighbours, so the
    # run's first words are looked for alone, then its last: the top of what
    # is found against the top of what was, or bottom against bottom.
    ws = (was.get("text") or "").split()
    if pdf and was.get("box") and len(ws) >= 2 * PART_MIN:
        half = max(PART_MIN, len(ws) // 2)
        for part, end in ((ws[:half], 1), (ws[-half:], 3)):
            got = place(pdf, " ".join(part), hint=page, tex=False)
            if got and got.get("box") and got.get("page") == page:
                return {"by": "part", "page": page, "box": None, "dx": 0,
                        "dy": round(got["box"][end] - was["box"][end], 4)}
    return {"by": "gone"}


def placements(repo, doc, note_path, pdf, digest, got, items):
    """Every request of one round on ONE BUILD of the PDF, cached by digest.

    `digest` is `paper._digest` -- the key `drawn_on` and the reader's own
    `build` already use -- so the pins the server hands back are for exactly
    the pages on the glass. Keyed as well on the validation, so an answer that
    changes is placed again.
    """
    return anchors(repo, doc, note_path, pdf, digest, got, items)[0]


# The shape of a placement cache's `ink_at`: a change to how ink re-anchors
# bumps it, so a cache written by the old rule is placed again.
ANCHOR_V = 2


def anchors(repo, doc, note_path, pdf, digest, got, items):
    """`(placed, ink_at)` for one round on one build: where each answer is,
    and where each request's ink is (`ink_where`). One cache file for both."""
    where = round_dir(note_path)
    cache = os.path.join(where, "placed-%s.json" % digest)
    hit = _read(cache, {}) or {}
    if hit.get("key") == got.get("key") and hit.get("v") == ANCHOR_V:
        return hit.get("placed") or {}, hit.get("ink_at") or {}
    n = len(words(pdf)[0]) if pdf else 0
    src = str((_read(ledger_path(note_path), {}) or {}).get("source") or "")
    tex = not src or src.lower().endswith((".tex", ".ltx", ".sty", ".cls"))
    out = {}
    for item in items:
        a = (got["items"].get(item["id"]) or {}).get("answer") or {}
        wording = a.get("new") or a.get("anchor") or ""
        found = place(pdf, wording, hint=item.get("page") or 0, tex=tex) \
            if pdf and wording else None
        if found and not a.get("new"):
            found["by"] = "anchor"
        if not found:
            page = int(item.get("page") or 0)
            found = ({"page": min(page, n) if n else page, "box": None, "by": "page"}
                     if page else {"page": 0, "box": None, "by": "none"})
        out[item["id"]] = found
    inks = {}
    for item in items:
        got_ink = ink_where(pdf, digest, item)
        if got_ink:
            inks[item["id"]] = got_ink
    try:
        os.makedirs(where, exist_ok=True)
        _write(cache, {"key": got.get("key"), "v": ANCHOR_V, "digest": digest,
                       "placed": out, "ink_at": inks})
        # Four builds' placements are kept, as the page cache keeps four sets.
        old = sorted((f for f in os.listdir(where) if f.startswith("placed-")),
                     key=lambda f: _mtime(os.path.join(where, f)))
        for f in old[:-4]:
            os.remove(os.path.join(where, f))
    except OSError:
        pass
    return out, inks


# A run of unchanged words longer than this is cut to its ends in a diff.
DIFF_KEEP = 16
DIFF_END = 6


def _span(words_, passage):
    """`(start, end)` of `passage`'s words inside `words_`, compared folded,
    or None. Anchored on its first words, and on its last ones for the end."""
    want = [_norm(w) for w in passage.split()]
    want = [w for w in want if w]
    have = [_norm(w) for w in words_]
    if not want or len(want) >= len(have):
        return None
    head, tail = want[:4], want[-4:]
    for s in range(len(have) - len(head) + 1):
        if have[s:s + len(head)] == head:
            for e in range(len(have), s, -1):
                if have[max(s, e - len(tail)):e] == tail:
                    return s, e
            return s, min(len(have), s + len(want))
    return None


def _readable(text, tex):
    """The words of `text` as the diff shows them: math kept (`plain`), and a
    stop or comma left alone after it put back on the word before."""
    out = []
    for w in plain(text or "", tex, math=True).split():
        if out and re.fullmatch(r"[.,;:!?)\]]+", w):
            out[-1] += w
        else:
            out.append(w)
    return out


def word_diff(old, new, tex=True, focus=""):
    """Old wording against new, word by word: `[["=", t], ["-", t], ["+", t]]`.

    Markup taken off first (`plain`), so the diff is of what the page reads.
    `focus` is the passage the turn quoted, where `new` is the whole changed
    paragraph round it: only the changes touching it are kept, so two
    requests answered in one paragraph each show their own. An unchanged run
    past `DIFF_KEEP` words keeps `DIFF_END` at each end it touches a change
    on, and an ellipsis between. None where there is nothing to compare.
    """
    a = _readable(old, tex)
    b = _readable(new, tex)
    if not a and not b:
        return None
    ops = []

    def put(op, ws):
        if not ws:
            return
        if ops and ops[-1][0] == op:
            ops[-1][1] += " " + " ".join(ws)
        else:
            ops.append([op, " ".join(ws)])

    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    codes = sm.get_opcodes()
    span = _span(b, " ".join(_readable(focus, tex))) if focus else None
    if span:
        s, e = span
        kept = []
        for c in codes:
            tag, i1, i2, j1, j2 = c
            touches = (j1 < e and j2 > s) if j2 > j1 else (s <= j1 <= e)
            if tag == "equal":
                # Context: only the part of an unchanged run inside the focus.
                lo, hi = max(j1, s), min(j2, e)
                if lo < hi:
                    kept.append(("equal", i1 + lo - j1, i1 + hi - j1, lo, hi))
            elif touches:
                kept.append(c)
        if any(c[0] != "equal" for c in kept):
            codes = kept
    for tag, i1, i2, j1, j2 in codes:
        if tag == "equal":
            put("=", a[i1:i2])
            continue
        put("-", a[i1:i2])
        put("+", b[j1:j2])
    out = []
    for n, (op, text) in enumerate(ops):
        ws = text.split()
        if op == "=" and len(ws) > DIFF_KEEP:
            first, last = n == 0, n == len(ops) - 1
            if first and last:
                text = " ".join(ws[:DIFF_END]) + " … " + " ".join(ws[-DIFF_END:])
            elif first:
                text = "… " + " ".join(ws[-DIFF_END:])
            elif last:
                text = " ".join(ws[:DIFF_END]) + " …"
            else:
                text = " ".join(ws[:DIFF_END]) + " … " + " ".join(ws[-DIFF_END:])
        out.append([op, text])
    return out


# ---------------------------------------------------------------------------
# what the glass is handed
# ---------------------------------------------------------------------------
def settle(repo, doc):
    """Validate every round that has changed. Run where the wipe runs, on the
    same two GETs, because there is no hook after a turn outside `bin/tutor`."""
    rs = rounds(repo.root, doc)
    for n, (_rec, path) in enumerate(rs):
        check(repo.root, doc, path, later=n < len(rs) - 1)


def view(repo, doc):
    """Every round's requests with their answers, pins and states. Newest first."""
    from . import library                             # local: avoids a cycle

    root = repo.root
    pdf = library.path_of(root, doc, ".pdf")
    digest = paper._digest(pdf, paper.PAGE_WIDTH) if pdf else ""
    try:
        pages_now = int(doc.get("pages") or 0)
    except (TypeError, ValueError):
        pages_now = 0
    rs = rounds(root, doc)
    out = []
    for n, (rec, path) in enumerate(rs):
        got = check(root, doc, path, later=n < len(rs) - 1)
        items = items_of(path)
        placed, inks = (anchors(repo, doc, path, pdf, digest, got, items)
                        if pdf and got.get("landed") else ({}, {}))
        if pdf and not got.get("landed"):
            # A NOT-FIXED PAIR RIDING A ROUND STILL BEING REVISED: its live ink
            # went when the last round landed, so the glass draws it back from
            # the archive, and needs to know where its words are now.
            for item in items:
                if item.get("kind") == "reopened" and item.get("strokes"):
                    got_ink = ink_where(pdf, digest, item)
                    if got_ink:
                        inks[item["id"]] = got_ink
        states = states_of(path)
        led = _read(ledger_path(path), {}) or {}
        src = str(led.get("source") or "")
        tex = not src or src.lower().endswith((".tex", ".ltx", ".sty", ".cls"))
        rows = []
        for item in items:
            r = got["items"].get(item["id"]) or {}
            st = states.get(item["id"]) or {}
            crop = item.get("crop") or ""
            home = item.get("from") or rec["name"]
            pair = _pair(item, r.get("answer"), placed.get(item["id"]),
                         inks.get(item["id"]), pages_now, tex)
            rows.append(dict(pair, **{
                "id": item["id"], "kind": item["kind"],
                "was": item.get("was") or "",
                "page": item.get("page") or 0,
                "text": item.get("text") or "",
                "why": item.get("why") or "",
                "previous": item.get("previous") or "",
                "count": item.get("count") or 0,
                "crop": ("/library/evidence/%s/%s/%s" % (doc["id"], home, crop)
                         if crop else ""),
                "marked": ("/library/evidence/%s/%s/%s" % (doc["id"], rec["name"],
                                                           item["marked"])
                           if item.get("marked") else ""),
                "status": r.get("status") or "waiting",
                "answer": r.get("answer"),
                "problems": r.get("problems") or [],
                "placed": placed.get(item["id"]),
                "state": st.get("state") or "open",
                "state_why": st.get("why") or "",
                "carried": st.get("carried") or "",
            }))
        _number(rows)
        landed_ = bool(got.get("landed"))
        open_ = sum(1 for x in rows
                    if x["state"] != "accepted" and not x["carried"])
        out.append({"note": rec["name"], "round": led.get("round") or n + 1,
                    "filed": led.get("filed") or "", "ask": led.get("ask") or "",
                    "landed": landed_,
                    "answered": sum(1 for x in rows if x["status"] == "answered"),
                    "open": open_,
                    "judged": sum(1 for x in rows if x["state"] != "open"),
                    # EVERY PAIR SAID FINE (or carried into a later round): the
                    # round collapses to one line on the glass.
                    "done": landed_ and bool(rows) and not open_,
                    "items": rows, "extra": got.get("extra") or [],
                    "unknown": got.get("unknown") or [],
                    "broken": bool(got.get("broken"))})
    out.reverse()
    return {"ok": True, "document": doc["id"], "digest": digest,
            "summary": summary(root, doc), "rounds": out}


def _pair(item, answer, placed, ink_at, pages_now, tex):
    """The half of a row that makes it a PAIR: what was written, and the
    revision that answers it, and where both are on the build on the glass.

        ink      `{page, box, strokes, drawn_on}`, the slimmed strokes as filed
        ink_at   where the ink's words are on this build (`ink_where`), or
                 where its answer is when they are gone (`by: "answer"`,
                 shifted down the page only)
        at       `{page, y, box, by}`: where the pip goes and what a tap
                 brings onto the glass -- the answer's box, else the ink's
        diff     word ops, old against new (`word_diff`)
        reply    the turn's sentence, where it answered without an edit
        gone     the words it was written on are not in the document, and
                 nothing else could be placed
    """
    strokes = item.get("strokes") or []
    ink = ({"page": int(item.get("page") or 0), "box": item.get("box"),
            "strokes": strokes, "drawn_on": item.get("drawn_on") or ""}
           if strokes else None)
    ink_at = dict(ink_at) if ink_at else None
    ref = (item.get("under") or {}).get("box") or item.get("box")
    # Words gone but the answer on the same page: the ink follows the answer
    # down the page. Never onto another page, where it would sit over words it
    # was never written about.
    if ink_at and ink_at.get("by") == "gone" and placed and placed.get("box") and ref \
            and placed.get("page") == int(item.get("page") or 0):
        ink_at = {"by": "answer", "page": placed["page"], "box": None,
                  "dx": 0, "dy": round(placed["box"][1] - ref[1], 4)}
    at = None
    if placed and placed.get("page") and placed.get("box"):
        at = {"page": placed["page"], "y": placed["box"][1], "box": placed["box"],
              "by": "answer"}
    elif ink_at and ink_at.get("page") and ink_at.get("box"):
        at = {"page": ink_at["page"], "y": ink_at["box"][1], "box": ink_at["box"],
              "by": "ink"}
    elif ink_at and ink_at.get("by") == "same" and item.get("box"):
        at = {"page": ink_at["page"], "y": item["box"][1], "box": item["box"],
              "by": "ink"}
    elif placed and placed.get("page"):
        at = {"page": placed["page"], "y": 0.02, "box": None, "by": "page"}
    if at and pages_now and not 0 < at["page"] <= pages_now:
        at = None
    diff, reply = None, ""
    if answer:
        if answer.get("disposition") in ("pushed back", "not done"):
            reply = answer.get("did") or ""
        old = answer.get("old") or ""
        new = answer.get("now") or answer.get("new") or ""
        focus = answer.get("new") if answer.get("now") else ""
        if old or new:
            diff = (word_diff(old, new, tex, focus=focus or "") if old
                    else [["+", " ".join(_readable(answer.get("new") or new, tex))]])
    gone = bool(ink_at and ink_at.get("by") == "gone"
                and not (placed and placed.get("box")))
    return {"ink": ink, "ink_at": ink_at, "at": at, "diff": diff,
            "reply": reply, "gone": gone}


def _number(rows):
    """`n` onto a round's pairs, 1..N in document order: by page, then down the
    page. A pair with nowhere to be goes last, in the order it was filed. The
    pip and the row carry the same number."""
    def pos(k):
        r = rows[k]
        at = r.get("at")
        if at:
            return (0, at["page"], at.get("y") or 0, k)
        return (1, int(r.get("page") or 0) or 10 ** 6, 0, k)
    for n, k in enumerate(sorted(range(len(rows)), key=pos), start=1):
        rows[k]["n"] = n
