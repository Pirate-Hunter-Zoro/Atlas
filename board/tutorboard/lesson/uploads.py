"""Photographs and PDFs handed to the board.
"""

import json
import os
import urllib.parse


def load_uploads(repo, limit=40):
    out = []
    try:
        names = sorted(os.listdir(repo.uploads))
    except OSError:
        names = []
    for name in names[-limit:]:
        path = os.path.join(repo.uploads, name)
        if not os.path.isfile(path):
            continue
        out.append({
            "name": name,
            "size": os.path.getsize(path),
            "url": "/uploads/" + urllib.parse.quote(name),
            "mtime": os.path.getmtime(path),
        })
    return out


