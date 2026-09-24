"""Which assistants this machine has, for the board to offer.

THE REGISTRY IS IN `bin/tutor` AND STAYS THERE. An agent entry is a command
recipe -- *a second model is a second entry whose `cmd` carries the flag* -- so
the table belongs beside the thing that runs it, and a machine's own
`config.json` merges into it one level deep. Copying the names into a second
list the browser could read is how the two go out of step the first time either
moves.

So this asks the launcher: `tutor --agents --json`. Once per board process,
because the answer changes only when somebody edits a configuration file -- and a
subprocess four times a second is not a thing to do to a poll.

THE TTL IS A MINUTE RATHER THAN A QUARTER OF AN HOUR, and the reason is that the
answer stopped being only about configuration. `unavailable` in that payload is
an allowance that has run out and a provider whose hostname this machine cannot
open, both of which move while the board is up and neither of which a person
edits a file to change. Fifteen minutes of a chooser offering a provider that
went dark fourteen minutes ago is fifteen minutes of a tap that lands nowhere.
A minute is still a poll every four hundredth request rather than every one.
"""

import json
import time


TTL = 60.0
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
