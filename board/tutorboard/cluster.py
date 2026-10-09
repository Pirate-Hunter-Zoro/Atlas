"""cluster.py -- where what the cluster says lands on the Mac.

`wake(subject, session, line)` is the one door: a job's ending (`jobs.drop`)
and a held step's check (`holds.wake`) both come through it. It writes
today's per-workspace inbox, `messages.jsonl` under the subject's session
directory (`course/repo.py`), which the next turn takes; `session` is carried
on the line and does not yet choose where it goes.

`wake=False` writes the line already read: it is on the record and wakes no
turn.

Standard library only.
"""

import json
import os
import time


def wake(subject, session, line, wake=True, signal="job", request=None,
         now=None):
    """Put one machinery line in the inbox of `subject` (its root). The line.

    `line` is the text. `signal` is how `turn_signal` reads it (`job`,
    `repair`, `coach`); `request` is a relay request id, so `board brief`
    can name it; `session` is the Mac session id the request was filed from,
    or None.
    """
    from .course.repo import Repo
    from .lesson import turns
    now = float(now or time.time())
    target = Repo(subject)
    os.makedirs(target.inbox, exist_ok=True)
    msg = {
        # From the lesson's own id series, and NOT in `turns.jsonl`: the
        # machinery is reporting, nobody said anything.
        "id": turns.next_turn_id(target), "rev": 0, "kind": "text",
        "answers": None, "t": now, "iso": time.strftime("%Y-%m-%d %H:%M:%S"),
        "from": "student", "text": str(line), "signal": signal,
        "read": not wake,
    }
    if request:
        msg["request"] = str(request)
    if session:
        msg["session"] = str(session)
    with open(target.messages_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(msg) + "\n")
    return msg
