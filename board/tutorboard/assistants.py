"""Which assistants this machine has, for the board to offer.

THE REGISTRY IS IN `bin/tutor` AND STAYS THERE. An agent entry is a command
recipe -- *a second model is a second entry whose `cmd` carries the flag* -- so
the table belongs beside the thing that runs it, and a machine's own
`config.json` merges into it one level deep. Copying the names into a second
list the browser could read is how the two go out of step the first time either
moves.

So this asks the launcher: `tutor --agents --json`. Once per board process,
because the answer changes only when somebody edits a configuration file, and a
subprocess four times a second is not a thing to do to a poll. `TTL` is long for
the same reason -- a board that has been up for a day and has just been given a
new agent picks it up on the next restart, which is when everything else about
the tool arrives too.
"""

import json
import time


TTL = 900.0
_CACHE = {"at": 0.0, "was": None}


def listing():
    """`{"default": name, "agents": [...]}`, or None if it could not be asked.

    None rather than an empty list, and the board has to tell them apart: no
    answer means the chooser is not drawn at all, while an empty one would mean
    this machine has no assistants, which is never true of a machine running a
    board.
    """
    now = time.time()
    if _CACHE["was"] is not None and now - _CACHE["at"] <= TTL:
        return _CACHE["was"]
    from .server import spawn

    code, out = spawn.tutor_cli(["--agents", "--json"], timeout=20)
    got = None
    if code == 0:
        try:
            got = json.loads(out.strip().splitlines()[-1])
        except (ValueError, IndexError):
            got = None
    _CACHE["was"] = got
    _CACHE["at"] = now
    return got


def forget():
    """Drop the cache. For a test, and for a restart that changed the table."""
    _CACHE["at"] = 0.0
    _CACHE["was"] = None
