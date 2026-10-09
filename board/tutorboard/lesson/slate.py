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
