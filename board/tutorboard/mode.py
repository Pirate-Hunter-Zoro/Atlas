"""A session's mode, teach or do, and the one way it changes.

`session.json` `mode` says who writes the code. It changes only through
`set_mode`: `board mode teach|do`, `POST /mode`, or the tutor obeying "do it"
by running `board mode do`. Nothing infers `do`.

A change appends one transcript turn and one inbox line and archives nothing.
The line is written `"wake": false`, so it queues no turn: the next turn takes
it with the rest, and its brief carries the new mode.
"""

import json
import os
import time

from .course import config
from .lesson import turns


# The inbox line, which a turn reads back in its recap.
LINE = {
    "teach": "[mode] This session is now in TEACH mode. Withhold the code being "
             "learned; the method follows TEACHING.md.",
    "do": "[mode] This session is now in DO mode. Write the code yourself, run "
          "it, and report what changed.",
}


def set_mode(repo, mode, by="student"):
    """Set the session's mode. Returns `(mode, changed)`.

    Raises ValueError for anything that is not one of `config.MODES`. Setting
    the mode a session already has writes nothing.
    """
    want = config.clean_mode(mode)
    if not want:
        raise ValueError("not a mode: %r (one of %s)"
                         % (mode, ", ".join(config.MODES)))
    st = repo.state()
    if st.get("mode") == want:
        return want, False
    repo.set_state(mode=want)
    tid = turns.next_turn_id(repo)
    record = {
        "id": tid, "rev": turns.turn_revision(repo, tid), "kind": "text",
        "answers": None,
        "t": time.time(),
        "iso": time.strftime("%Y-%m-%d %H:%M:%S"),
        "from": by, "text": "Mode: %s." % want,
        "signal": "mode", "read": True,
    }
    turns.write_turn(repo, record)
    os.makedirs(os.path.dirname(repo.messages_path), exist_ok=True)
    with open(repo.messages_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(dict(record, text=LINE[want], read=False,
                                 wake=False)) + "\n")
    return want, True
