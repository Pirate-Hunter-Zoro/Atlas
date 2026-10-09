"""Photographs and PDFs handed to the board: the session's `uploads/`.
"""

import os
import urllib.parse


def load_uploads(repo, limit=40):
    """The newest `limit` uploads, oldest first: `[{name, size, url, mtime}]`.
    A `.part-*` file still arriving, and any other dot file, is not one."""
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
    out.sort(key=lambda u: (u["mtime"], u["name"]))
    return out[-limit:]
