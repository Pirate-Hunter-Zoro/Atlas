"""What is on the writing surface, and what was handed in from it.
"""

import json
import os
import re


# A page is its number, read from the filename, never its position in a
# list: saved pages have gaps, and a positional index would write a stroke
# onto a neighbour's page. The filename is what the next save addresses.
_PAGE_RE = re.compile(r"^page-(\d+)\.json$")


def page_number(name):
    m = _PAGE_RE.match(name)
    return int(m.group(1)) if m else None


# A typeset given placed on a page (`web/slate-core.js` `placeTex`):
# {id, kind: "tex", tex, fig, x, y, w, h}. What a browser sends is checked
# field by field, and anything else is dropped.
OBJECTS_MAX = 64
_FIG = re.compile(r"\A[0-9a-f]{6,40}\Z")


def clean_objects(raw):
    """The typeset givens a save carries, each whole or not at all."""
    out = []
    for o in raw if isinstance(raw, list) else []:
        if not isinstance(o, dict) or o.get("kind") != "tex":
            continue
        fig = str(o.get("fig") or "")
        try:
            box = [float(o.get(k)) for k in ("x", "y", "w", "h")]
        except (TypeError, ValueError):
            continue
        if not _FIG.match(fig) or box[2] <= 0 or box[3] <= 0 \
                or any(v != v or abs(v) > 1e7 for v in box):
            continue
        out.append({"id": str(o.get("id") or "given")[:40], "kind": "tex",
                    "tex": str(o.get("tex") or "")[:4000], "fig": fig,
                    "x": box[0], "y": box[1], "w": box[2], "h": box[3]})
        if len(out) >= OBJECTS_MAX:
            break
    return out


def stored_objects(path):
    """The typeset givens on the page saved at `path`, or []."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            rec = json.load(fh)
    except (OSError, ValueError):
        return []
    return clean_objects(rec.get("objects")) if isinstance(rec, dict) else []


def read_slate_pages(repo):
    """Full stroke data for every page, each with its number and ordered by
    it (`page-100` sorts before `page-99` by name)."""
    pages = []
    try:
        names = [n for n in os.listdir(repo.slate) if _PAGE_RE.match(n)]
    except OSError:
        names = []
    for name in sorted(names, key=page_number):
        try:
            with open(os.path.join(repo.slate, name), "r", encoding="utf-8") as fh:
                rec = json.load(fh)
        except (OSError, ValueError):
            continue
        if not isinstance(rec, dict):
            continue
        rec["page"] = page_number(name)
        pages.append(rec)
    return pages


def load_slate(repo, limit=40):
    """Saved slate pages, newest last. Only the metadata -- the strokes stay on
    disk until the slate itself asks for them."""
    out = []
    try:
        names = [n for n in os.listdir(repo.slate)
                 if re.match(r"^page-\d+\.png$", n)]
    except OSError:
        names = []
    # By number, not name.
    names.sort(key=lambda n: int(n[5:-4]))
    for name in names[-limit:]:
        path = os.path.join(repo.slate, name)
        out.append({
            "name": name,
            "page": int(name[5:-4]),
            "url": "/slate/" + name,
            "mtime": os.path.getmtime(path),
            "size": os.path.getsize(path),
        })
    return out
