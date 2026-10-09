"""What this machine calls itself, and what it is for.

Every record that crosses live/ carries this name and every liveness check
compares it, so if it moves, a machine stops recognising its own work.
"""

import os


def slurm_nodes():
    """Nodes where this user currently holds an allocation, or None if unknown.

    Platform knowledge, so it lives here: `board` uses it to decide whether a
    lock belongs to a job that has ended. Where
    there is no `squeue` the answer is None -- unknown, not empty -- and every
    caller must treat those differently, because "no allocations" and "not a
    cluster" lead to opposite decisions.
    """
    import re
    import subprocess
    try:
        p = subprocess.run(["squeue", "-h", "-u", os.environ.get("USER", ""), "-o", "%N"],
                           stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=10)
        if p.returncode != 0:
            return None
        out = p.stdout.decode("utf-8", "replace")
        nodes = set()
        for tok in re.findall(r"compute\[?([0-9,\-]+)\]?", out):
            for part in tok.split(","):
                if "-" in part:
                    a, b = part.split("-", 1)
                    for n in range(int(a), int(b) + 1):
                        nodes.add("compute%d" % n)
                else:
                    nodes.add("compute" + part)
        return nodes
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return None


# ---------------------------------------------------------------------------
# What this machine calls itself
# ---------------------------------------------------------------------------
# Every record that crosses `live/` carries this name, and every liveness check
# compares it before trusting a pid, so there is one function and no caller asks
# the system directly: `os.uname()` and `socket.gethostname()` can disagree on
# one machine.


def _normal_node(name):
    """One form for one machine.

    First label, lowercased: `board.tail0c6c62.ts.net` and `Compute304` and
    `compute304` must not be three machines, because a record written under one
    spelling has to be believed under another.
    """
    return (name or "").strip().split(".")[0].lower() or "unknown"


def system_node_name():
    """Whatever the operating system says."""
    return _normal_node(os.uname().nodename)


def node_name():
    """What this machine calls itself. The only place that decides.

    The environment first (for a test, or a one-off), then the system.
    """
    env = os.environ.get("BOARD_NODE_NAME")
    if env and env.strip():
        return _normal_node(env)
    return system_node_name()


def machine_shape():
    """What this machine is: a compute node, or a standalone machine.

    Guessing this from the hostname is how it gets subtly wrong, so it is
    decided from what is actually true: a compute node is where Slurm answers,
    and everything else is a standalone machine. The difference is whether this
    machine can be taken away -- an allocation ends and the node stops being
    yours, which is why a board here is brought back by a login rather than by a
    supervisor.
    """
    if slurm_nodes() is not None:
        return "compute node"
    return "standalone"
