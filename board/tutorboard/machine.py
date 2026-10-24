"""What this machine calls itself.

Every record that crosses live/ carries this name and every liveness check
compares it, so if it moves, a machine stops recognising its own work.
"""

import os


# ---------------------------------------------------------------------------
# What this machine calls itself
# ---------------------------------------------------------------------------
# One function names this machine, because `os.uname()` and
# `socket.gethostname()` can disagree; liveness checks compare it.


def _normal_node(name):
    """One form for one machine: the first label, lowercased."""
    return (name or "").strip().split(".")[0].lower() or "unknown"


def system_node_name():
    """Whatever the operating system says."""
    return _normal_node(os.uname().nodename)


def node_name():
    """What this machine calls itself; the environment overrides the system."""
    env = os.environ.get("BOARD_NODE_NAME")
    if env and env.strip():
        return _normal_node(env)
    return system_node_name()
