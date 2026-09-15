"""Files: the app shell, the fonts, a compiled figure, a result, a photograph.

Everything here is bytes off disk, and everything a person handed in is
served with the headers that stop a browser executing it.
"""

import json
import os
import re

from . import NOT_MINE
from .. import multipart
from ... import paths
from ...course import results


def get(h, repo, path):
    if path == "/manifest.webmanifest":
        return h.send_bytes(open(os.path.join(paths.WEB, "manifest.webmanifest"), "rb").read(),
                               "application/manifest+json")

    if path == "/sw.js":
        return h.send_file(os.path.join(paths.WEB, "sw.js"))

    if path.startswith("/static/"):
        rel = path[len("/static/"):]
        target = os.path.normpath(os.path.join(paths.WEB, rel))
        if not target.startswith(paths.WEB):
            return h.send_bytes(b"nope", "text/plain", status=403)
        return h.send_file(
            target, cache=rel.startswith("katex/") or rel.startswith("fonts/"))

    if path.startswith("/figure/"):
        digest = multipart.safe_filename(path[len("/figure/"):]).replace(".svg", "")
        return h.send_file(os.path.join(repo.tikz, digest + ".svg"), cache=True)

    if path.startswith("/result/"):
        # A FIGURE THE PIPELINE MADE, ADDRESSED BY AN ID RATHER THAN BY A PATH.
        #
        # `/figure/` above is TikZ the tutor wrote and this board compiled. This
        # is somebody's own output, out of their workspace, and the difference
        # that matters here is where the name came from: a digest this board
        # produced can be joined onto a directory, and a name out of a browser
        # cannot. So it is looked up in what discovery found -- `results.find`
        # is the whole of the check, the same rule as `reading.find` and
        # `walk.resolve` -- and a miss is a miss.
        ident = path[len("/result/"):]
        if not re.match(r"^[a-z0-9-]{1,80}$", ident):
            return h.send_bytes(b"not found", "text/plain", status=404)
        target, _name = results.find(repo.root, ident)
        if not target:
            return h.send_bytes(b"not found", "text/plain", status=404)
        # NOT CACHED. The next job writes a new figure at the same name, and the
        # id is derived from that name -- so a hard cache here serves last
        # week's result under this week's label. `web/sw.js` keeps the same rule
        # on its side.
        return h.send_file(target)

    if path.startswith("/uploads/"):
        name = multipart.safe_filename(path[len("/uploads/"):])
        return h.send_file(os.path.join(repo.uploads, name), untrusted=True)

    if path.startswith("/answers/"):
        name = multipart.safe_filename(path[len("/answers/"):])
        return h.send_file(os.path.join(repo.answers, name))
    return NOT_MINE
