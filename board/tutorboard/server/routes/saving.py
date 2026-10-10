"""Committing the lesson, and exporting it as something to hand to somebody.

Every route here is a SESSION route, served under `/s/<id>/` by that
session's Repo (`handler.UNPREFIXED` lists none of them):

    POST /push          session   commit and push the session's subject
    POST /hw/build      session   build the session's write-up
    POST /export/shot   session   the lesson as the iPad drew it
"""

import time
import json
import os

from . import NOT_MINE
from ...course import screenshot
from ...lesson import git


def post(h, repo, path):
    if path == "/push":
        try:
            payload = json.loads(h.read_body().decode("utf-8") or "{}")
        except Exception:
            payload = {}
        record = git.run_push(repo, (payload.get("message") or "").strip() or None)
        git._DIRTY["value"] = None      # ask again now, not in eight seconds
        # Clear the end-of-session offer either way; a failure shows as a
        # banner with the reason rather than as a standing prompt.
        st = repo.state()
        if st.pop("finished", None) is not None:
            with open(repo.state_path, "w", encoding="utf-8") as fh:
                json.dump(st, fh, indent=2)
        h.hub.worker.dirty.set()
        return h.send_json(record)

    if path == "/hw/build":
        # The write-up compile, the same one `board writeup build` runs.
        try:
            rec = git.run_hw_build(repo)
        except Exception as e:                       # noqa: BLE001
            rec = {"ok": False, "detail": "build failed: %s" % e}
        git._DIRTY["value"] = None      # a new PDF is uncommitted; say so
        h.hub.worker.dirty.set()
        return h.send_json(rec)

    if path == "/export/shot":
        # The lesson as the iPad drew it: the pixels come from the device,
        # which alone knows how it looked; the server chooses where it goes,
        # its name and version, and writes `export.json`, which
        # `/download/lesson` resolves through.
        try:
            payload = json.loads(h.read_body().decode("utf-8") or "{}")
        except Exception:                            # noqa: BLE001
            payload = {}
        images, why = screenshot.decode(payload)
        if why:
            rec = {"ok": False, "detail": why}
        else:
            box = screenshot.page_box(payload)
            try:
                rec = screenshot.build(repo.root, images, box[0], box[1],
                                       state=repo.state())
            except Exception as e:                   # noqa: BLE001
                rec = {"ok": False, "detail": "could not write it: %s" % e}
        rec["at"] = time.time()
        rec["iso"] = time.strftime("%Y-%m-%d %H:%M:%S")
        rec.setdefault("scope", "shot")
        with open(os.path.join(repo.live, "export.json"), "w", encoding="utf-8") as fh:
            json.dump(rec, fh, indent=2)
        git._DIRTY["value"] = None      # the new file is uncommitted; say so
        h.hub.worker.dirty.set()
        return h.send_json(rec)

    return NOT_MINE
