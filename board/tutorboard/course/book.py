"""A course's textbook, read into an index from the PDF's own outline.

The outline gives the chapters and usually the sections; the page text gives
the printed page numbers and the exercises. Nothing here calls a model, and
nothing here guesses: what cannot be read is a doubt, and a reference the
index does not hold is "not indexed".

    ingest(root, upload=None, write=False, check=False, say=None)
                             the whole run, resumable; returns a report
    find(root, ref)          one reference: PDF pages, printed pages, the
                             reading excerpt and its page, and the text
    sheet(root, pdf, chapter=None)
                             every reference on an assignment sheet, resolved
    status(root)             what index.json and ingest.json say
    read(root)               index.json, or None
    file_upload(root, path)  an uploaded PDF moved into textbook/

Everything it writes is ignored, under `<course>/textbook/`:

    text/pNNNN.txt   one page's text, from one `pdftotext -layout` run; a page
                     under MIN_TEXT characters is OCR'd by `gs -sDEVICE=ocr`
    index.json       sha256, pages, chapters, sections, label runs, exercises
                     and doubts
    ingest.json      a run's progress: state, step, done of total

`chapters.tsv` is the tracked exception: written only when absent, otherwise
diffed, and rewritten only with `write`.
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET

from .. import paths

TEXTBOOK = "textbook"
TEXT = "text"
INDEX = "index.json"
PROGRESS = "ingest.json"
TSV = "chapters.tsv"
OCR_DONE = "ocr.json"

# A page with fewer characters than this has no text layer worth the name.
MIN_TEXT = 40
# A chapter level is the shallowest outline depth with this many numbered items.
MIN_CHAPTERS = 3
# The most an exercise or section number may jump and still be the next one.
GAP = 5
# How much text `find` hands back.
TEXT_LINES = 60
TEXT_CHARS = 4000

SCRIPTS = os.path.join(paths.TOOL, "scripts")

# The back matter a chapter list stops at.
# "Solutions to Starred Exercises" stops it; "Solution by radicals" does not.
STOP = re.compile(r"(?:(?:hints?\s+(?:and|to)\s+)?(?:solutions?|answers?)"
                  r"(?:\s+(?:to|for|of)\b.*)?\s*$"
                  r"|(?:appendix|appendices|index|references|bibliography)\b)", re.I)
# `1 Groups`, `1. Groups`, `Chapter 1: Groups`; never `1.1 Groups`.
NUMBERED = re.compile(r"^\s*(?:chapter\s+|ch\.?\s*)?(\d{1,3})(?![.\d]\d)[.:]?\s+(\S.*)$",
                      re.I)
SECTION_TITLE = re.compile(r"^\s*(\d{1,3})\.(\d{1,3})\.?\s+(\S.*)$")
# A section heading in page text: flush left, the number, then the title.
SECTION_LINE = re.compile(r"^ ?(\d{1,3})\.(\d{1,3})\.?(\s+)([A-Z].*?)\s*$")
EXERCISES_HEAD = re.compile(r"^\s*(?:exercises?|problems?)\s*$", re.I)
DOTTED = re.compile(r"^\s{0,10}(\*?)(\d{1,3})\.(\d{1,3})\.?\s+\S")
PLAIN = re.compile(r"^\s{0,10}(\*?)(\d{1,3})\.\s+\S")
CHAPTER_LINE = re.compile(r"^\s*chapter\s+(\d{1,3})\b[.:]?\s*(.*)$", re.I)
LONE_NUMBER = re.compile(r"^\s*(\d{1,3})\s*$")


class Refused(Exception):
    """What the caller is told in its own words: no PDF, two PDFs, a
    different book, a tool missing."""


# ---------------------------------------------------------------------------
# where things are
# ---------------------------------------------------------------------------
def textbook_dir(root):
    return os.path.join(root, TEXTBOOK)


def pdfs(root):
    """Every PDF directly in `<root>/textbook/`, sorted."""
    where = textbook_dir(root)
    try:
        names = sorted(os.listdir(where))
    except OSError:
        return []
    return [os.path.join(where, n) for n in names
            if n.lower().endswith(".pdf") and os.path.isfile(os.path.join(where, n))]


def the_pdf(root):
    """The one PDF in textbook/; Refused for none or for more than one."""
    found = pdfs(root)
    if not found:
        raise Refused("no PDF in %s" % textbook_dir(root))
    if len(found) > 1:
        raise Refused("expected exactly one PDF in %s, found %d: %s" % (
            textbook_dir(root), len(found),
            ", ".join(os.path.basename(p) for p in found)))
    return found[0]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    os.replace(tmp, path)


def _read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            got = json.load(fh)
    except (OSError, ValueError):
        return None
    return got if isinstance(got, dict) else None


def read(root):
    """index.json, or None."""
    return _read_json(os.path.join(textbook_dir(root), INDEX))


def progress(root):
    """ingest.json, or None."""
    return _read_json(os.path.join(textbook_dir(root), PROGRESS))


def indexed(root):
    return os.path.isfile(os.path.join(textbook_dir(root), INDEX))


def _need(tool):
    if not shutil.which(tool):
        raise Refused("%s is not installed (brew install %s)" % (
            tool, "poppler" if tool.startswith("pdf") else "ghostscript"))


def _run(argv, timeout=600):
    return subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                          timeout=timeout)


# ---------------------------------------------------------------------------
# filing an upload
# ---------------------------------------------------------------------------
def file_upload(root, path, move=True):
    """Move the PDF at `path` into `<root>/textbook/` (copy it, with `move`
    false); its new path. The same book again (by sha256) is not a second
    one: a moved upload is dropped and the filed copy kept. A different book
    is Refused."""
    if not os.path.isfile(path):
        raise Refused("no such upload: %s" % os.path.basename(path))
    if not path.lower().endswith(".pdf"):
        raise Refused("a textbook is a PDF: %s" % os.path.basename(path))
    have = pdfs(root)
    if have:
        mine = sha256(path)
        for one in have:
            if sha256(one) == mine:
                if move and os.path.realpath(one) != os.path.realpath(path):
                    os.remove(path)
                return one
        raise Refused("this course already has a textbook, %s; a second, "
                      "different PDF is refused" % os.path.basename(have[0]))
    os.makedirs(textbook_dir(root), exist_ok=True)
    dest = os.path.join(textbook_dir(root), os.path.basename(path))
    if move:
        shutil.move(path, dest)
    else:
        shutil.copyfile(path, dest)
    return dest


# ---------------------------------------------------------------------------
# the outline
# ---------------------------------------------------------------------------
def outline(pdf):
    """`[(depth, page or None, title)]` in document order, from
    `pdftohtml -xml`; [] for a PDF with no outline."""
    _need("pdftohtml")
    out = _run(["pdftohtml", "-xml", "-i", "-q", "-stdout", "-f", "1", "-l", "1",
                pdf]).stdout.decode("utf-8", "replace")
    return parse_outline(out)


def parse_outline(xml):
    """The outline out of `pdftohtml -xml`'s output. Only the <outline>
    block is parsed: page one's text is not ours to trust as XML."""
    start, end = xml.find("<outline"), xml.rfind("</outline>")
    if start < 0 or end < 0:
        return []
    try:
        top = ET.fromstring(xml[start:end + len("</outline>")])
    except ET.ParseError:
        return []
    items = []

    def walk(node, depth):
        for child in node:
            if child.tag == "item":
                title = " ".join("".join(child.itertext()).split())
                try:
                    page = int(child.get("page"))
                except (TypeError, ValueError):
                    page = None
                items.append((depth, page, title))
            elif child.tag == "outline":
                walk(child, depth + 1)
    walk(top, 0)
    return items


def _numbered(title):
    m = NUMBERED.match(title or "")
    if not m:
        return None
    return int(m.group(1)), m.group(2).strip().rstrip(".").strip()


def chapters_from_outline(items, npages, doubts):
    """`(depth, [chapter])`, or `(None, [])` where the outline has no level
    with MIN_CHAPTERS numbered items."""
    depths = sorted(set(d for d, p, t in items))
    level = None
    for d in depths:
        if sum(1 for dd, p, t in items if dd == d and p and _numbered(t)) >= MIN_CHAPTERS:
            level = d
            break
    if level is None:
        return None, []
    shallow = [(i, d, p, t) for i, (d, p, t) in enumerate(items) if d <= level and p]
    found = []
    for k, (i, d, p, t) in enumerate(shallow):
        num = _numbered(t) if d == level else None
        title = num[1] if num else t
        if found and STOP.match(title):
            doubts.append("the chapters stop at %r (PDF page %d)" % (t, p))
            break
        if not num:
            continue
        if STOP.match(title):
            doubts.append("the outline item %r (PDF page %d) is back matter, "
                          "not a chapter" % (t, p))
            continue
        end = None
        for _i, _d, q, _t in shallow[k + 1:]:
            if q > p:
                end = q - 1
                break
            if q < p:
                break
        if end is None:
            end = npages
            later = [q for _i, _d, q, _t in shallow[k + 1:]]
            if later and later[0] < p:
                doubts.append("chapter %d: the outline item after it points "
                              "back to PDF page %d; it is taken to run to the "
                              "last page" % (num[0], later[0]))
            elif not later:
                doubts.append("chapter %d is the outline's last item, so it "
                              "is taken to run to the last page, %d"
                              % (num[0], npages))
        found.append({"num": "%02d" % num[0], "first": p, "last": end,
                      "title": title, "source": "outline", "_item": i})
    _check_sequence(found, doubts)
    return level, found


def _check_sequence(found, doubts):
    for a, b in zip(found, found[1:]):
        if int(b["num"]) != int(a["num"]) + 1:
            doubts.append("chapter %s follows chapter %s" % (b["num"], a["num"]))


def chapters_from_text(pages, doubts):
    """Chapter openers read off the page text, for a PDF with no outline:
    "Chapter N" near the top, or a lone N above a title. Each is a doubt."""
    found, want = [], None
    for n, text in enumerate(pages, 1):
        lines = [l for l in text.splitlines() if l.strip()][:6]
        hit = None
        for j, line in enumerate(lines):
            m = CHAPTER_LINE.match(line)
            if m:
                rest = m.group(2).strip() or (lines[j + 1].strip()
                                              if j + 1 < len(lines) else "")
                hit = (int(m.group(1)), rest)
                break
            m = LONE_NUMBER.match(line)
            if m and j + 1 < len(lines) and not LONE_NUMBER.match(lines[j + 1]):
                hit = (int(m.group(1)), lines[j + 1].strip())
                break
        if found and lines and STOP.match(lines[0].strip()):
            found[-1]["last"] = n - 1
            doubts.append("the chapters stop at %r (PDF page %d)"
                          % (lines[0].strip(), n))
            return found
        if not hit or not hit[1]:
            continue
        if (want is None and hit[0] in (0, 1)) or hit[0] == want:
            if found:
                found[-1]["last"] = n - 1
            found.append({"num": "%02d" % hit[0], "first": n, "last": len(pages),
                          "title": hit[1], "source": "text"})
            want = hit[0] + 1
    for c in found:
        doubts.append("chapter %s (%s, PDF pages %d-%d) was read from the page "
                      "text: the PDF has no outline" % (c["num"], c["title"],
                                                        c["first"], c["last"]))
    return found


# ---------------------------------------------------------------------------
# page text
# ---------------------------------------------------------------------------
def npages(pdf):
    _need("pdfinfo")
    out = _run(["pdfinfo", pdf]).stdout.decode("utf-8", "replace")
    m = re.search(r"^Pages:\s+(\d+)", out, re.M)
    if not m:
        raise Refused("pdfinfo cannot read %s" % os.path.basename(pdf))
    return int(m.group(1))


def _page_file(cache, n):
    return os.path.join(cache, "p%04d.txt" % n)


def page_text(root, n):
    try:
        with open(_page_file(os.path.join(textbook_dir(root), TEXT), n), "r",
                  encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def extract(pdf, cache, total, sha, note=None):
    """Every page's text in `cache`, from one `pdftotext -layout` run, then
    each page under MIN_TEXT characters OCR'd one at a time. Resumes: pages
    already there are kept, and a page already OCR'd is not OCR'd again.
    Returns `(pages, ocr'd page numbers, pages OCR could not read)`."""
    stamp = os.path.join(cache, ".sha256")
    try:
        same = open(stamp, encoding="utf-8").read().strip() == sha
    except OSError:
        same = False
    if not same and os.path.isdir(cache):
        shutil.rmtree(cache)
    os.makedirs(cache, exist_ok=True)
    with open(stamp, "w", encoding="utf-8") as fh:
        fh.write(sha + "\n")
    if any(not os.path.isfile(_page_file(cache, n)) for n in range(1, total + 1)):
        _need("pdftotext")
        if note:
            note("text", 0, total)
        raw = _run(["pdftotext", "-layout", pdf, "-"], timeout=1800).stdout
        parts = raw.decode("utf-8", "replace").split("\f")
        for n in range(1, total + 1):
            if not os.path.isfile(_page_file(cache, n)):
                with open(_page_file(cache, n), "w", encoding="utf-8") as fh:
                    fh.write(parts[n - 1] if n - 1 < len(parts) else "")
    pages = []
    for n in range(1, total + 1):
        with open(_page_file(cache, n), "r", encoding="utf-8", errors="replace") as fh:
            pages.append(fh.read())
    done_path = os.path.join(cache, OCR_DONE)
    done = _read_json(done_path) or {}
    tried = set(done.get("ocr") or [])
    failed = set(done.get("failed") or [])
    short = [n for n in range(1, total + 1)
             if len(pages[n - 1].strip()) < MIN_TEXT and n not in tried | failed]
    if short and not shutil.which("gs"):
        failed.update(short)
        short = []
    for k, n in enumerate(short):
        if note:
            note("ocr", k, len(short))
        got = ocr_page(pdf, n)
        if got is None:
            failed.add(n)
        else:
            tried.add(n)
            if len(got.strip()) > len(pages[n - 1].strip()):
                pages[n - 1] = got
                with open(_page_file(cache, n), "w", encoding="utf-8") as fh:
                    fh.write(got)
        _write_json(done_path, {"ocr": sorted(tried), "failed": sorted(failed)})
    return pages, sorted(tried), sorted(failed)


def ocr_page(pdf, n):
    """Page `n`'s text by ghostscript's OCR device at 300 dpi, or None."""
    fd, out = tempfile.mkstemp(suffix=".txt", prefix="board-ocr-")
    os.close(fd)
    try:
        got = _run(["gs", "-q", "-dSAFER", "-dBATCH", "-dNOPAUSE", "-sDEVICE=ocr",
                    "-r300", "-dFirstPage=%d" % n, "-dLastPage=%d" % n,
                    "-sOutputFile=" + out, pdf], timeout=300)
        if got.returncode != 0:
            return None
        with open(out, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except (OSError, subprocess.SubprocessError):
        return None
    finally:
        try:
            os.remove(out)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# printed page numbers
# ---------------------------------------------------------------------------
def _label_candidates(text):
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    found = set()
    for line in lines[:2] + lines[-2:]:
        m = re.match(r"^(\d{1,4})\b", line)
        if m:
            found.add(int(m.group(1)))
        m = re.search(r"\b(\d{1,4})$", line)
        if m:
            found.add(int(m.group(1)))
    return found


def label_runs(pages):
    """Runs of constant offset (PDF page minus printed page), never one
    offset for the book. A page's number is read from its first or last two
    lines; it counts only where a neighbouring page agrees, and a run needs
    three such pages. Each run reaches back over the unnumbered pages before
    it, and the last reaches to the end: `[{first, last, offset}]`."""
    total = len(pages)
    offs = []
    for n, text in enumerate(pages, 1):
        offs.append(set(n - k for k in _label_candidates(text) if 0 < k and n - k > -20))
    sure = {}
    for i in range(total):
        agreed = set(o for o in offs[i]
                     if (i > 0 and o in offs[i - 1]) or (i + 1 < total and o in offs[i + 1]))
        if agreed:
            sure[i + 1] = agreed
    runs = []
    for n in sorted(sure):
        here = sure[n]
        if runs and runs[-1]["offset"] in here:
            runs[-1]["last"] = n
            runs[-1]["seen"] += 1
            continue
        o = min(here, key=lambda x: (abs(x - runs[-1]["offset"]) if runs else 0, x))
        runs.append({"first": n, "last": n, "offset": o, "seen": 1})
    runs = [r for r in runs if r["seen"] >= 3]
    merged = []
    for r in runs:
        if merged and merged[-1]["offset"] == r["offset"]:
            merged[-1]["last"] = r["last"]
        else:
            merged.append(dict(r))
    for k, r in enumerate(merged):
        r["first"] = merged[k - 1]["last"] + 1 if k else 1
        r.pop("seen", None)
    if merged:
        merged[-1]["last"] = total
    return merged


def printed_of(labels, pdf_page):
    """The printed number of a PDF page, or None."""
    for r in labels or []:
        if r["first"] <= pdf_page <= r["last"]:
            k = pdf_page - r["offset"]
            return k if k > 0 else None
    return None


def pdf_of(labels, printed):
    """Every PDF page printed `printed`, in order."""
    return [printed + r["offset"] for r in labels or []
            if r["first"] <= printed + r["offset"] <= r["last"]]


# ---------------------------------------------------------------------------
# sections and exercises
# ---------------------------------------------------------------------------
def sections_from_outline(items, level, chapters):
    out = []
    for k, c in enumerate(chapters):
        start = c.get("_item")
        if start is None:
            continue
        num = int(c["num"])
        for d, p, t in items[start + 1:]:
            if d <= level:
                break
            m = SECTION_TITLE.match(t)
            if m and int(m.group(1)) == num and p:
                out.append({"num": "%d.%d" % (num, int(m.group(2))), "chapter": c["num"],
                            "title": m.group(3).strip(), "page": p, "source": "outline"})
    return out


def _chapter_pages(c, pages):
    for n in range(c["first"], min(c["last"], len(pages)) + 1):
        yield n, pages[n - 1].splitlines()


def sections_from_text(c, pages, ocr):
    """`N.M  Title` heading lines in chapter `c`'s pages, keeping the
    increasing run."""
    num, last, out = int(c["num"]), 0, []
    for n, lines in _chapter_pages(c, pages):
        for line in lines:
            m = SECTION_LINE.match(line)
            if not m or int(m.group(1)) != num:
                continue
            title = m.group(4)
            if len(m.group(3)) < 2 and not (n in ocr and len(title) <= 60):
                continue
            if title.endswith((".", ",", ";")) or len(title) > 90:
                continue
            k = int(m.group(2))
            if last < k <= last + GAP:
                out.append({"num": "%d.%d" % (num, k), "chapter": c["num"],
                            "title": title, "page": n, "source": "text"})
                last = k
    return out


def _is_heading(line, known):
    """Is `line` the heading of one of `known` sections ({(ch, m): title})?"""
    m = SECTION_LINE.match(line) or SECTION_TITLE.match(line)
    if not m:
        return False
    title = known.get((int(m.group(1)), int(m.group(2))))
    if not title:
        return False
    said = (m.group(4) if m.re is SECTION_LINE else m.group(3)).split()
    want = title.split()
    return bool(said and want and said[0].lower() == want[0].lower())


def exercises(c, pages, sections):
    """Chapter `c`'s exercises: the numbered lines after a line reading
    "Exercises" or "Problems", until the next section heading, keeping the
    increasing run. `7.6` or `6.` styles, whichever the chapter's first
    exercise uses."""
    num = int(c["num"])
    known = dict(((int(s["num"].split(".")[0]), int(s["num"].split(".")[1])), s["title"])
                 for s in sections if s["chapter"] == c["num"])
    style, last, on, out = None, 0, False, []
    for n, lines in _chapter_pages(c, pages):
        for i, line in enumerate(lines):
            if EXERCISES_HEAD.match(line):
                on = True
                continue
            if not on:
                continue
            if _is_heading(line, known) or STOP.match(line.strip()) and len(line.strip()) < 20:
                on = False
                continue
            got = None
            if style in (None, "dotted"):
                m = DOTTED.match(line)
                if m and int(m.group(2)) == num:
                    got = ("dotted", int(m.group(3)), m.group(1))
            if got is None and style in (None, "plain"):
                m = PLAIN.match(line)
                if m:
                    got = ("plain", int(m.group(2)), m.group(1))
            if got is None:
                continue
            kind, k, star = got
            if not (last < k <= last + GAP):
                continue
            style, last = kind, k
            out.append({"chapter": c["num"], "n": k,
                        "label": ("%d.%d" % (num, k)) if kind == "dotted" else str(k),
                        "page": n, "line": i, "starred": bool(star)})
    return out


# ---------------------------------------------------------------------------
# the index
# ---------------------------------------------------------------------------
def build_index(pdf, items, pages, ocr=(), failed=(), sha=""):
    """index.json's content, from the outline and the page text."""
    doubts = []
    total = len(pages)
    level, chapters = chapters_from_outline(items, total, doubts) if items else (None, [])
    if not chapters:
        if items:
            doubts.append("the outline has no level with %d numbered items; the "
                          "chapters were read from the page text" % MIN_CHAPTERS)
        chapters = chapters_from_text(pages, doubts)
    if not chapters:
        doubts.append("no chapters found, in the outline or the text")
    sections = sections_from_outline(items, level, chapters) if level is not None else []
    have = set(s["chapter"] for s in sections)
    ocr = set(ocr)
    for c in chapters:
        if c["num"] in have:
            continue
        got = sections_from_text(c, pages, ocr)
        sections.extend(got)
    labels = label_runs(pages)
    if not labels:
        doubts.append("no printed page numbers could be read: a printed page "
                      "reference is not indexed")
    found = []
    for c in chapters:
        found.extend(exercises(c, pages, sections))
    for n in failed:
        doubts.append("PDF page %d has no text and OCR could not read it" % n)
    for c in chapters:
        c.pop("_item", None)
    sections.sort(key=lambda s: (s["chapter"], int(s["num"].split(".")[1])))
    return {
        "pdf": os.path.basename(pdf), "sha256": sha, "pages": total,
        "outline": len(items), "chapters": chapters, "sections": sections,
        "labels": labels, "exercises": found, "ocr": sorted(ocr),
        "doubts": doubts,
        "made": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


# ---------------------------------------------------------------------------
# chapters.tsv
# ---------------------------------------------------------------------------
TSV_HEAD = """# Single source of truth for the chapter layout of this course.
# Written by `board textbook ingest` from the textbook's PDF outline; used by
# `board textbook split` and `board textbook scaffold`.
#
# Columns (TAB separated):
#   num  first_pdf_page  last_pdf_page  slug  title
#
# Page numbers are PDF page indices into textbook/%s, not the book's
# printed page numbers: `board textbook find "p. N"` turns one into the other.
"""


def slug_of(title):
    words = re.sub(r"[^a-z0-9]+", " ", title.lower().replace("'", "")
                   .replace("’", "")).split()
    if words and words[0] in ("the", "a", "an") and len(words) > 1:
        words = words[1:]
    out = ""
    for w in words:
        if out and len(out) + 1 + len(w) > 50:
            break
        out = (out + "-" + w) if out else w
    return out or "chapter"


def read_tsv(root):
    """`(comment lines, [{num, first, last, slug, title}])`, or (None, None)."""
    path = os.path.join(root, TSV)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return None, None
    head, rows = [], []
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            if not rows:
                head.append(line)
            continue
        cols = line.split("\t")
        if len(cols) < 5:
            continue
        try:
            first, last = int(cols[1]), int(cols[2])
        except ValueError:
            continue
        rows.append({"num": cols[0].strip(), "first": first, "last": last,
                     "slug": cols[3].strip(), "title": cols[4].strip()})
    return head, rows


def _norm(title):
    return " ".join(title.replace("’", "'").split()).lower()


def diff_rows(have, want):
    """The chapter-row differences between the tracked table `have` and the
    book's `want`, as lines; slugs are the table's and are not compared."""
    out = []
    by = dict((int(r["num"]), r) for r in have)
    book = dict((int(r["num"]), r) for r in want)
    for n in sorted(set(by) | set(book)):
        a, b = by.get(n), book.get(n)
        if a and not b:
            out.append("- ch%02d %d-%d %s (the book has no chapter %d)"
                       % (n, a["first"], a["last"], a["title"], n))
        elif b and not a:
            out.append("+ ch%02d %d-%d %s" % (n, b["first"], b["last"], b["title"]))
        elif (a["first"], a["last"]) != (b["first"], b["last"]) \
                or _norm(a["title"]) != _norm(b["title"]):
            out.append("~ ch%02d table %d-%d %s | book %d-%d %s"
                       % (n, a["first"], a["last"], a["title"],
                          b["first"], b["last"], b["title"]))
    return out


def write_tsv(root, chapters, pdf_name, head=None, slugs=None):
    slugs = slugs or {}
    lines = list(head) if head else (TSV_HEAD % pdf_name).splitlines()
    for c in chapters:
        lines.append("\t".join([c["num"], str(c["first"]), str(c["last"]),
                                slugs.get(int(c["num"])) or slug_of(c["title"]),
                                c["title"]]))
    tmp = os.path.join(root, TSV + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    os.replace(tmp, os.path.join(root, TSV))


# ---------------------------------------------------------------------------
# the run
# ---------------------------------------------------------------------------
def ingest(root, upload=None, write=False, check=False, say=None, split=True,
           move=True):
    """File `upload` (a path) if given, read the one PDF in textbook/, write
    index.json, then chapters.tsv where it is absent (or with `write`), then
    split and scaffold. `check` writes no chapters.tsv and splits nothing.
    Progress goes to ingest.json throughout. Returns the report; raises
    Refused in its own words."""
    say = say or (lambda line: None)
    root = os.path.realpath(root)
    prog_path = os.path.join(textbook_dir(root), PROGRESS)
    started = time.time()

    def note(step, done=0, total=0, **more):
        rec = {"state": "running", "step": step, "done": done, "total": total,
               "started": started, "t": time.time()}
        rec.update(more)
        _write_json(prog_path, rec)

    try:
        if upload:
            filed = file_upload(root, upload, move=move)
            say("filed %s" % os.path.relpath(filed, root))
        pdf = the_pdf(root)
        note("reading")
        sha = sha256(pdf)
        total = npages(pdf)
        items = outline(pdf)
        say("%s: %d pages, %d outline items" % (os.path.basename(pdf), total, len(items)))
        pages, ocr, failed = extract(pdf, os.path.join(textbook_dir(root), TEXT),
                                     total, sha, note=note)
        if ocr:
            say("OCR'd %d page(s) with no text layer" % len(ocr))
        note("index")
        index = build_index(pdf, items, pages, ocr, failed, sha)
        _write_json(os.path.join(textbook_dir(root), INDEX), index)
        report = summary(index)
        say("index: %d chapters, %d sections, %d exercises, %d printed-page run(s)"
            % (report["chapters"], report["sections"], report["exercises"],
               report["labels"]))
        for d in index["doubts"]:
            say("doubt: " + d)

        head, rows = read_tsv(root)
        if rows is None:
            if check:
                report["tsv"] = "absent"
                say("chapters.tsv: absent (not written under --check)")
            elif index["chapters"]:
                write_tsv(root, index["chapters"], index["pdf"])
                report["tsv"] = "written"
                say("chapters.tsv: written, %d chapters" % len(index["chapters"]))
            else:
                report["tsv"] = "absent"
        else:
            diff = diff_rows(rows, index["chapters"])
            report["diff"] = diff
            say("chapters.tsv: %d chapter-row difference(s)" % len(diff))
            for line in diff:
                say("  " + line)
            if not diff:
                report["tsv"] = "same"
            elif write and not check and index["chapters"]:
                write_tsv(root, index["chapters"], index["pdf"], head=head,
                          slugs=dict((int(r["num"]), r["slug"]) for r in rows))
                report["tsv"] = "rewritten"
                say("chapters.tsv: rewritten from the book")
            else:
                report["tsv"] = "differs"
                say("chapters.tsv: kept; `board textbook ingest <course> --write` "
                    "rewrites it from the book")

        if split and not check and report["tsv"] in ("written", "same", "rewritten"):
            note("split")
            for name, args in (("split-textbook.sh", []),
                               ("scaffold.sh", ["--chapter-homework"])):
                got = subprocess.run(["bash", os.path.join(SCRIPTS, name), root] + args,
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                     universal_newlines=True)
                report[name.split("-")[0].split(".")[0]] = got.returncode
                tail = [l for l in got.stdout.splitlines() if l.strip()]
                say("%s: %s" % (name, tail[-1] if tail else "exit %d" % got.returncode))
                if got.returncode != 0:
                    raise Refused("%s failed: %s" % (name, "\n".join(tail[-5:])))
        _write_json(prog_path, {"state": "done", "step": "done", "started": started,
                                "t": time.time(), "report": report})
        return report
    except Exception as exc:
        try:
            _write_json(prog_path, {"state": "failed", "step": "failed",
                                    "started": started, "t": time.time(),
                                    "error": str(exc)})
        except OSError:
            pass
        raise


def summary(index):
    """The counts a report, a status and a `[textbook]` line carry."""
    return {"ok": True, "pdf": index.get("pdf"), "pages": index.get("pages"),
            "chapters": len(index.get("chapters") or []),
            "sections": len(index.get("sections") or []),
            "exercises": len(index.get("exercises") or []),
            "labels": len(index.get("labels") or []),
            "doubts": list(index.get("doubts") or [])}


# ---------------------------------------------------------------------------
# finding
# ---------------------------------------------------------------------------
RE_PAGE = re.compile(r"^\s*(?:pp?\.?|pages?)\s*(\d{1,4})\s*$", re.I)
RE_SECTION = re.compile(r"^\s*(?:§|sections?|sec\.?)\s*(\d{1,3})\.(\d{1,3})\s*$", re.I)
RE_CH_EX = re.compile(r"^\s*ch(?:apter)?\.?\s*(\d{1,3})\s*[,:]?\s*(?:#|no\.?|"
                      r"exercises?|ex\.?|problems?|prob\.?)\s*\*?(\d{1,3})\s*$", re.I)
RE_EX = re.compile(r"^\s*(?:(exercises?|ex\.?|problems?|prob\.?)\s*)?\*?(\d{1,3})\.(\d{1,3})\s*$",
                   re.I)
RE_CHAPTER = re.compile(r"^\s*ch(?:apter)?\.?\s*(\d{1,3})\s*$", re.I)
RE_BARE_EX = re.compile(r"^\s*(?:exercises?|ex\.?|problems?|prob\.?|#)\s*\*?(\d{1,3})\s*$",
                        re.I)


def _not(ref, why):
    return {"ok": False, "ref": ref, "error": "not indexed: " + why}


def _reading(root, index, chapter, pdf_page):
    """`(rel path, page within it)` of the chapter excerpt holding
    `pdf_page`, by chapters.tsv (which is what split cuts by)."""
    _head, rows = read_tsv(root)
    for r in rows or []:
        try:
            same = int(r["num"]) == int(chapter)
        except ValueError:
            continue
        if same and r["first"] <= pdf_page <= r["last"]:
            rel = os.path.join("chapters", "ch%s-%s" % (r["num"], r["slug"]),
                               "reading", "ch%s.pdf" % r["num"])
            return rel, pdf_page - r["first"] + 1
    return None, None


def _chapter_of(index, pdf_page):
    for c in index.get("chapters") or []:
        if c["first"] <= pdf_page <= c["last"]:
            return c
    return None


def _answer(root, index, ref, kind, page, text, chapter=None, label=None, also=None):
    c = chapter or _chapter_of(index, page)
    out = {"ok": True, "ref": ref, "kind": kind, "label": label or ref,
           "pdf_page": page, "printed": printed_of(index.get("labels"), page),
           "chapter": {"num": c["num"], "title": c["title"]} if c else None,
           "reading": None, "reading_page": None, "text": text}
    if c:
        out["reading"], out["reading_page"] = _reading(root, index, c["num"], page)
    if also:
        out["also"] = also
    return out


def _clip(lines):
    text = "\n".join(lines[:TEXT_LINES]).strip("\n")
    return text[:TEXT_CHARS]


def _exercise_text(root, index, ex):
    every = index.get("exercises") or []
    k = every.index(ex)
    nxt = every[k + 1] if k + 1 < len(every) else None
    lines = page_text(root, ex["page"]).splitlines()
    if nxt and nxt["page"] == ex["page"]:
        return _clip(lines[ex["line"]:nxt["line"]])
    taken = lines[ex["line"]:]
    if nxt and nxt["page"] == ex["page"] + 1:
        taken += page_text(root, nxt["page"]).splitlines()[:nxt["line"]]
    return _clip(taken)


def _section_text(root, s):
    lines = page_text(root, s["page"]).splitlines()
    want = s["num"]
    for i, line in enumerate(lines):
        if line.strip().startswith(want):
            return _clip(lines[i:])
    return _clip(lines)


def exercise(index, chapter, n):
    for ex in index.get("exercises") or []:
        if int(ex["chapter"]) == chapter and ex["n"] == n:
            return ex
    return None


def section(index, chapter, m):
    for s in index.get("sections") or []:
        if s["num"] == "%d.%d" % (chapter, m):
            return s
    return None


def find(root, ref):
    """One reference resolved, or `{ok: False, error: "not indexed: ..."}`.

    "Exercise 3.4", "3.4", "Ch 4 #34", "Section 2.1", "§2.1", "p. 295",
    "Ch 7". A bare "3.4" is the exercise; where a section 3.4 exists too it
    is named in `also`.
    """
    ref = str(ref or "").strip()
    index = read(root)
    if index is None:
        return _not(ref, "this course's textbook has no index; run `board "
                         "textbook ingest <course>`")
    m = RE_PAGE.match(ref)
    if m:
        printed = int(m.group(1))
        got = pdf_of(index.get("labels"), printed)
        if not got:
            return _not(ref, "no PDF page carries printed page %d" % printed)
        out = _answer(root, index, ref, "page", got[0],
                      _clip(page_text(root, got[0]).splitlines()), label="p. %d" % printed)
        if len(got) > 1:
            out["also"] = ["PDF page %d" % p for p in got[1:]]
        return out
    m = RE_SECTION.match(ref)
    if m:
        s = section(index, int(m.group(1)), int(m.group(2)))
        if not s:
            return _not(ref, "the index has no section %s.%s" % (m.group(1), m.group(2)))
        return _answer(root, index, ref, "section", s["page"], _section_text(root, s),
                       label="Section %s %s" % (s["num"], s["title"]))
    m = RE_CH_EX.match(ref)
    pair = (int(m.group(1)), int(m.group(2))) if m else None
    bare = False
    if not pair:
        m = RE_EX.match(ref)
        if m:
            pair = (int(m.group(2)), int(m.group(3)))
            bare = not m.group(1)
    if pair:
        ex = exercise(index, *pair)
        s = section(index, *pair) if bare else None
        if not ex:
            if s:
                return _answer(root, index, ref, "section", s["page"],
                               _section_text(root, s),
                               label="Section %s %s" % (s["num"], s["title"]))
            return _not(ref, "the index has no exercise %d in chapter %d"
                        % (pair[1], pair[0]))
        also = ["Section %s %s, PDF page %d" % (s["num"], s["title"], s["page"])] if s else None
        return _answer(root, index, ref, "exercise", ex["page"],
                       _exercise_text(root, index, ex),
                       label="Exercise %s" % ("%d.%d" % pair if "." in ex["label"]
                                              else "%d (chapter %d)" % (pair[1], pair[0])),
                       also=also)
    m = RE_CHAPTER.match(ref)
    if m:
        want = int(m.group(1))
        for c in index.get("chapters") or []:
            if int(c["num"]) == want:
                return _answer(root, index, ref, "chapter", c["first"],
                               _clip(page_text(root, c["first"]).splitlines()),
                               chapter=c, label="Chapter %s %s" % (c["num"], c["title"]))
        return _not(ref, "the book has no chapter %d" % want)
    if RE_BARE_EX.match(ref):
        return _not(ref, "an exercise number needs its chapter: \"Ch 4 #34\" or \"4.34\"")
    return _not(ref, "not a reference this reads: try \"Exercise 3.4\", \"Ch 4 #34\", "
                     "\"Section 2.1\" or \"p. 295\"")


# ---------------------------------------------------------------------------
# an assignment sheet
# ---------------------------------------------------------------------------
SHEET_REFS = re.compile(
    r"(?:\bch(?:apter)?\.?\s*\d{1,3}\s*[,:]?\s*(?:#|no\.?\s*|exercises?\s*|problems?\s*)\*?\d{1,3}"
    r"|\b(?:exercises?|problems?|ex\.)\s*\*?\d{1,3}\.\d{1,3}(?:\s*(?:,|and|or|&)\s*\*?\d{1,3}\.\d{1,3})*"
    r"|(?:§|\bsections?\s*)\s*\d{1,3}\.\d{1,3}"
    r"|\bpp?\.\s*\d{1,4})", re.I)
SHEET_CHAPTER = re.compile(r"\bch(?:apter)?\.?\s*(\d{1,3})\b(?!\s*[#.]\s*\d)", re.I)
LIST_LINE = re.compile(r"^(?:\s|,|;|\.|\*|\d{1,3}|\bor\b|\band\b|&|\balong\s+with\b)+$", re.I)


def sheet_refs(text):
    """`(explicit references, bare exercise numbers, chapters named)` read
    off a sheet's text."""
    refs = []
    for m in SHEET_REFS.finditer(text):
        got = " ".join(m.group(0).split())
        head = re.match(r"(?i)(exercises?|problems?|ex\.)\s*", got)
        if head and re.search(r"\d\.\d.*\d\.\d", got):
            for one in re.findall(r"\*?\d{1,3}\.\d{1,3}", got):
                refs.append("Exercise " + one.lstrip("*"))
        else:
            refs.append(got)
    bare = []
    for line in text.splitlines():
        if not line.strip() or not LIST_LINE.match(line):
            continue
        nums = re.findall(r"\*?(\d{1,3})(?!\.\d)", line)
        if len(nums) >= 2:
            bare.extend(int(n) for n in nums)
    chapters = sorted(set(int(n) for n in SHEET_CHAPTER.findall(text)))
    return refs, bare, chapters


def sheet(root, pdf, chapter=None):
    """Every reference on the assignment sheet `pdf`, resolved. A bare list
    of numbers ("1, 7, 9 or 10") needs a chapter: `chapter`, else the one
    chapter the sheet names; without one each is "not indexed"."""
    _need("pdftotext")
    if not os.path.isfile(pdf):
        raise Refused("no such sheet: %s" % pdf)
    text = _run(["pdftotext", "-layout", pdf, "-"]).stdout.decode("utf-8", "replace")
    refs, bare, named = sheet_refs(text)
    out = [find(root, r) for r in refs]
    ch = chapter if chapter is not None else (named[0] if len(named) == 1 else None)
    for n in bare:
        ref = "Ch %d #%d" % (ch, n) if ch is not None else "#%d" % n
        if ch is None:
            out.append(_not(ref, "the sheet lists exercise %d but names no one chapter; "
                                 "give it: board textbook find <course> \"Ch N\" "
                                 "--sheet <pdf>" % n))
        else:
            out.append(find(root, ref))
    return out


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------
def status(root):
    """What there is: the PDF, the index's counts and doubts, chapters.tsv
    against the book, and the last run's progress."""
    out = {"ok": True, "pdfs": [os.path.basename(p) for p in pdfs(root)],
           "indexed": False, "progress": progress(root)}
    index = read(root)
    if index:
        out.update(summary(index))
        out["indexed"] = True
        out["label_runs"] = index.get("labels") or []
        out["ocr"] = index.get("ocr") or []
        out["sha256"] = index.get("sha256")
        _head, rows = read_tsv(root)
        out["tsv"] = "absent" if rows is None else (
            "differs" if diff_rows(rows, index.get("chapters") or []) else "same")
        if rows is not None:
            out["diff"] = diff_rows(rows, index.get("chapters") or [])
    return out


def line_for(root, report=None, error=None, name=None):
    """The `[textbook]` line a finished ingest wakes its session with."""
    if error:
        return ("[textbook] Indexing %s failed: %s. `board textbook status` says "
                "where it stopped; `board textbook ingest <course>` resumes it."
                % (name or "the textbook", error))
    r = report or {}
    doubts = r.get("doubts") or []
    tsv = {"written": "chapters.tsv was written from the book",
           "same": "chapters.tsv matches the book",
           "rewritten": "chapters.tsv was rewritten from the book",
           "differs": "chapters.tsv differs from the book in %d row(s) and was kept"
                      % len(r.get("diff") or []),
           "absent": "there is no chapters.tsv"}.get(r.get("tsv"), "")
    out = ("[textbook] %s is indexed: %d pages, %d chapters, %d sections, %d "
           "exercises, printed pages in %d run(s). %s. " % (
               r.get("pdf") or "The textbook", r.get("pages") or 0, r.get("chapters", 0),
               r.get("sections", 0), r.get("exercises", 0), r.get("labels", 0), tsv))
    if doubts:
        out += "%d doubt(s): %s. Settle each by reading its pages (`board textbook " \
               "find`), and say what you found. " % (len(doubts), "; ".join(doubts[:8]))
    else:
        out += "No doubts. "
    out += ("Then write TUTOR.md \"Where things are\" with `board memo`: the book, "
            "its index, and the readings under chapters/. Commit chapters.tsv and "
            "the new chapter .tex files with `board push`.")
    return out
