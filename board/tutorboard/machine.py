"""What this machine calls itself, and what it is for.

Every record that crosses live/ carries this name and every liveness check
compares it, so if it moves, a machine stops recognising its own work.
"""

import os


def slurm_nodes():
    """Nodes where this user holds an allocation, or None where there is no
    `squeue`: unknown is not empty, and the two lead to opposite decisions."""
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


def machine_shape():
    """A compute node (Slurm answers) or a standalone machine, decided from
    what is true rather than the hostname."""
    if slurm_nodes() is not None:
        return "compute node"
    return "standalone"
