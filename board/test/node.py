#!/usr/bin/env python3
"""What this machine calls itself, and why it must not be asked twice.

Every record that crosses `live/` carries this name -- board records, agent
records -- and every liveness check compares it before trusting a pid. So the
name is not cosmetic: if it moves, a machine stops recognising its own boards.
`tutor restart` skips them as another node's, the hub reports them running
somewhere else, and a board that is answering perfectly well becomes impossible
to bounce onto new code. A shipped fix then appears not to have landed, which is
the most expensive kind of bug this repository has.

It is derived one way, in `tutorboard/machine.py`, and no caller asks the
system directly: `os.uname()` and `socket.gethostname()` are not required to
agree on one machine. Nothing pins it; boards run on the Mac alone.

Also the cluster's setup script.
"""

import importlib.machinery
import importlib.util
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


# A state directory of its own. BOARD_STATE_DIR exists precisely so a test can
# never write the real one -- a bootstrap test once renamed the live machine on
# the tailnet, which silently moved the address the iPad app was installed
# against.
sandbox = tempfile.mkdtemp(prefix="tutor-node-")
os.environ["BOARD_STATE_DIR"] = sandbox
os.environ.pop("BOARD_NODE_NAME", None)
sys.path.insert(0, ROOT)
from tutorboard import machine, paths


def reload_lib():
    importlib.reload(paths)          # STATE_DIR is read from the environment
    importlib.reload(machine)


reload_lib()

# --- one form for one machine ----------------------------------------------
check("a fully qualified name is just the first label",
      machine._normal_node("board.tail0c6c62.ts.net") == "board")
check("and case is not an identity: Mac-mini and mac-mini are one machine",
      machine._normal_node("Mac-mini") == machine._normal_node("mac-mini") == "mac-mini")
check("and nothing at all is not an empty string in a record",
      machine._normal_node("") == "unknown")

# --- no pinning: the environment, then the system ------------------------------
check("the name is whatever the system says",
      machine.node_name() == machine.system_node_name())
os.environ["BOARD_NODE_NAME"] = "override"
check("the environment wins, for a test or a one-off",
      machine.node_name() == "override")
os.environ.pop("BOARD_NODE_NAME")
check("and nothing pins it: no pin file, no pin function",
      not hasattr(machine, "pin_node_name")
      and not hasattr(machine, "NODE_NAME_FILE")
      and not os.path.exists(os.path.join(sandbox, "nodename")))

# --- nobody derives it for themselves ---------------------------------------
# This is the half that actually broke. Two files asked `socket.gethostname()`
# and one asked `os.uname()`; on a Mac those are allowed to differ, and either
# can follow the network.
import ast  # noqa: E402


def asks_the_system(path):
    """Names of system calls this file makes to find out the hostname.

    Parsed, not grepped. A rule about what the code does must not be broken by
    prose describing it -- the docstring on `this_node` says the words
    `socket.gethostname()` precisely to record what it stopped doing.
    """
    tree = ast.parse(open(path, encoding="utf-8").read())
    found = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        name = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", None)
        if name in ("gethostname", "uname"):
            found.add(name)
    return found


for rel in ("bin/board", "bin/relay", "serve.py"):
    check("%s does not ask the system for the hostname itself" % rel,
          not asks_the_system(os.path.join(ROOT, rel)))

check("tutorboard/machine.py is the one place that may",
      asks_the_system(os.path.join(ROOT, "tutorboard", "machine.py")) == {"uname"})

board_src = open(os.path.join(ROOT, "bin", "board"), encoding="utf-8").read()
check("there is no `board node` and no `board net` any more",
      "def cmd_node(" not in board_src and '"node": cmd_node' not in board_src
      and "def cmd_net(" not in board_src and '"net": cmd_net' not in board_src)
check("nor the userspace daemon's one-node claim",
      "def ts_check_owner(" not in board_src and "def ts_claim(" not in board_src)

# --- the launcher and the board must agree ----------------------------------
from tutorboard.agents import recipes  # noqa: E402

bloader = importlib.machinery.SourceFileLoader("boardcli", os.path.join(ROOT, "bin", "board"))
bspec = importlib.util.spec_from_loader("boardcli", bloader)
board = importlib.util.module_from_spec(bspec)
bloader.exec_module(board)

check("the launcher and the board call this machine the same thing",
      recipes.this_host() == board.this_node() == machine.node_name())

# --- setting the cluster up ------------------------------------------------------
# `scripts/setup-cluster.sh` replaces the compute-node setup: no board and no
# model run there, so it bootstraps, checks ai-config, installs the relay and
# checks the remote.
import subprocess  # noqa: E402

SETUP = os.path.join(ROOT, "scripts", "setup-cluster.sh")
check("there is a cluster setup script, and it is the only setup script",
      os.path.isfile(SETUP)
      and [n for n in os.listdir(os.path.join(ROOT, "scripts"))
           if n.startswith("setup-")] == ["setup-cluster.sh"])
setup_src = open(SETUP, encoding="utf-8").read() if os.path.isfile(SETUP) else ""
check("it is at most sixty lines", len(setup_src.splitlines()) <= 60)
check("it is sound bash", subprocess.run(["bash", "-n", SETUP]).returncode == 0)
check("it bootstraps and checks ai-config",
      "bootstrap.sh" in setup_src and "ai-config" in setup_src)
check("it installs the relay through bin/relay, and names no other launcher",
      'bin/relay" --install' in setup_src and "tutor" not in setup_src)
check("and checks the remote answers", "ls-remote origin" in setup_src)
check("and installs no timer and starts no board or tutor",
      "systemctl" not in setup_src and "restart" not in setup_src
      and "board start" not in setup_src)
check("the systemd units are gone, so nothing can install a timer",
      not os.path.exists(os.path.join(ROOT, "scripts", "systemd")))
install_src = open(os.path.join(ROOT, "install.sh"), encoding="utf-8").read()
check("and install.sh has no systemd branch", "systemctl" not in install_src)
auto = open(os.path.join(ROOT, "scripts", "install-autostart.sh"),
            encoding="utf-8").read()
check("install-autostart keeps only --uninstall",
      "--uninstall" in auto and "--login-hook" not in auto)

shutil.rmtree(sandbox, ignore_errors=True)
print()
print("%d FAILURES" % len(fails) if fails else "a machine knows its own name")
sys.exit(1 if fails else 0)
