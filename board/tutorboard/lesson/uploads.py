"""Photographs and PDFs handed to the board: the session's `uploads/`.
"""

import os
import urllib.parse


def load_uploads(repo, limit=40):
    """The newest `limit` uploads, oldest first: `[{name, size, url, mtime}]`,
    and a PDF's `doc`, the id the board's reader opens it as
    (`library.uploads`). A `.part-*` file still arriving, and any other dot
    file, is not one."""
    from ..course import library                       # local: heavy
    docs = dict((u["name"], u["id"]) for u in library.uploads(repo))
    out = []
    try:
        names = os.listdir(repo.uploads)
    except OSError:
        names = []
    for name in names:
        path = os.path.join(repo.uploads, name)
        if name.startswith(".") or not os.path.isfile(path):
            continue
        st = os.stat(path)
        out.append({
            "name": name,
            "size": st.st_size,
            "url": "/uploads/" + urllib.parse.quote(name),
            "mtime": st.st_mtime,
        })
        if docs.get(name):
            out[-1]["doc"] = docs[name]
    out.sort(key=lambda u: (u["mtime"], u["name"]))
    return out[-limit:]
