"""A session's agent record: `agent.json` in the session directory.

`agent_state` merges into it; the runner (`runner/service.py`) writes it
around every turn, naming this machine and the server's own pid. Nothing here
starts anything: every turn runs inside the board server.
"""

import json
import os
import subprocess
import time

def agent_state(live, **kw):
    path = os.path.join(live, "agent.json")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            st = json.load(fh)
    except (OSError, ValueError):
        st = {}
    st.update(kw)
    st["last_seen"] = time.time()
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(st, fh, indent=2)
    os.replace(tmp, path)
    return st


def agent_record_at(live):
    """`<live>/agent.json` as a dict, or None."""
    try:
        with open(os.path.join(live, "agent.json"), "r", encoding="utf-8") as fh:
            got = json.load(fh)
    except (OSError, ValueError):
        return None
    return got if isinstance(got, dict) else None


def owed_message(live):
    """A message a turn took and never answered, or None: the other half of
    `loop.owe`. The runner answers it before anything new in the inbox, since
    the lines it came from are already marked read."""
    try:
        with open(os.path.join(live, "agent.json"), "r", encoding="utf-8") as fh:
            got = (json.load(fh) or {}).get("owed")
    except (OSError, ValueError):
        return None
    return got if isinstance(got, str) and got.strip() else None


def not_this_agents_failure(live, agent_name):
    """The fields that drop a failure belonging to somebody else, or `{}`.

    Written wherever the agent ON the record changes -- a start, and a
    climb-down between turns -- because the board reads the agent and the
    failure out of the same record and puts them in one sentence. A failure that
    outlives the provider it happened to is then a sentence about the wrong
    provider, which is a new way to mislead rather than the honest history the
    retention is for.
    """
    try:
        with open(os.path.join(live, "agent.json"), "r", encoding="utf-8") as fh:
            was = json.load(fh) or {}
    except (OSError, ValueError):
        return {}
    if not was.get("last_error"):
        return {}
    whose = was.get("failed_agent") or was.get("agent")
    if whose == agent_name:
        return {}
    return {"last_error": None, "failed_at": 0, "failed_agent": None}


def pid_alive(pid, needle=None):
    """Is this pid alive here, and does it still look like what was recorded?

    Pids are recycled, so where the command line can be read the recorded
    command (`needle`) has to still be in it."""
    if not pid:
        return False
    try:
        os.kill(int(pid), 0)
    except (OSError, TypeError, ValueError):
        return False
    if not needle:
        return True
    args = _cmdline(pid)
    if args is None:
        return True          # cannot tell; the pid is alive, so believe it
    return os.path.basename(str(needle)) in args


def attached(record, host):
    """Does this record name a live process on `host`? The host is compared
    before the pid is believed; a record with no pid is believed for two
    minutes after it was last written."""
    if not record:
        return False
    if record.get("host") and record["host"] != host:
        return False
    if record.get("pid"):
        return pid_alive(record["pid"])
    try:
        return time.time() - float(record.get("last_seen") or 0) <= 120
    except (TypeError, ValueError):
        return False


def _cmdline(pid):
    try:
        out = subprocess.run(["ps", "-p", str(pid), "-o", "args="],
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                             timeout=5)
        return out.stdout.decode("utf-8", "replace") if out.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None
