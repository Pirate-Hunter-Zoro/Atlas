"""Tailscale: who is up, what this machine is called on the tailnet, and how a
board makes itself reachable from the other machine.

Binding the tailnet address directly is the obvious way and it fails on the
one machine that matters, so `publish_board` uses `tailscale serve --tcp`,
which works in userspace mode too.
"""

import json
import os
import shutil
import subprocess
import time

from .. import paths


# ---------------------------------------------------------------------------
# Tailscale
# ---------------------------------------------------------------------------
# Overridable so a test never writes this machine's real tailnet state.
TS_DIR = os.environ.get("BOARD_STATE_DIR") or os.path.join(paths.HOME, ".local", "state", "tailscale")
TS_SOCK = os.path.join(TS_DIR, "tailscaled.sock")

# Where a system Tailscale keeps its CLI off PATH: Homebrew's or the app's,
# since launchd's PATH has neither.
SYSTEM_TS = [
    "/usr/local/bin/tailscale",
    "/usr/bin/tailscale",
    "/opt/homebrew/bin/tailscale",
    "/Applications/Tailscale.app/Contents/MacOS/Tailscale",
]


def _ours(path):
    """Is this binary one we unpacked under this home directory?"""
    home = os.path.realpath(paths.HOME) + os.sep
    return os.path.realpath(path).startswith(home)


def system_tailscale():
    """The path of a Tailscale this tool did not install (Homebrew, the app),
    or None."""
    for p in [shutil.which("tailscale")] + SYSTEM_TS:
        if p and os.path.isfile(p) and not _ours(p):
            return p
    return None


TS_NAME_FILE = os.path.join(TS_DIR, "hostname")


def tailnet_hostname():
    """What this machine calls itself on the tailnet: `board` by default, so
    the address survives a move; a second machine up at once needs its own."""
    env = os.environ.get("BOARD_TAILNET_NAME")
    if env:
        return env
    try:
        with open(TS_NAME_FILE, "r", encoding="utf-8") as fh:
            name = fh.read().strip()
            if name:
                return name
    except OSError:
        pass
    return "board"


def set_tailnet_hostname(name):
    os.makedirs(TS_DIR, exist_ok=True)
    with open(TS_NAME_FILE, "w", encoding="utf-8") as fh:
        fh.write(name.strip() + "\n")



_TS_CACHE = [0.0, None]
TS_CACHE_TTL = 3.0


def _ts_status():
    """`tailscale status --json`, cached a few seconds."""
    now = time.time()
    if _TS_CACHE[1] is not None and now - _TS_CACHE[0] < TS_CACHE_TTL:
        return _TS_CACHE[1]
    prefix, _ = tailscale_cli()
    if not prefix:
        return {}
    import subprocess
    try:
        p = subprocess.run(prefix + ["status", "--json"], stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL, timeout=20)
        st = json.loads(p.stdout.decode("utf-8", "replace")) or {}
    except (OSError, ValueError, subprocess.SubprocessError):
        return {}
    _TS_CACHE[0], _TS_CACHE[1] = now, st
    return st


def tailnet_addresses():
    """This machine's own tailscale addresses, if it is on a tailnet."""
    prefix, _ = tailscale_cli()
    if not prefix:
        return []
    import subprocess
    try:
        p = subprocess.run(prefix + ["ip"], stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL, timeout=10)
        out = p.stdout.decode("utf-8", "replace").split()
    except (OSError, subprocess.SubprocessError):
        return []
    # IPv4 only: a failing v6 bind is noise.
    return [a for a in out if a.count(".") == 3]


def tailnet_self(status=None):
    """This machine's tailnet name, which is not its hostname."""
    st = status if status is not None else _ts_status()
    name = ((st.get("Self") or {}).get("DNSName") or "").rstrip(".")
    return name


def publish_board(port, timeout=20):
    """Let the other machines on this tailnet reach this board, with
    `tailscale serve --tcp` on the board's own port: binding the tailnet
    address directly fails under userspace tailscaled.
    """
    prefix, _ = tailscale_cli()
    if not prefix:
        return False
    import subprocess
    try:
        p = subprocess.run(prefix + ["serve", "--bg", "--tcp", str(port),
                                     "tcp://127.0.0.1:%d" % port],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           timeout=timeout)
        return p.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def unpublish_board(port, timeout=20):
    """Take it off the tailnet again, so a stopped board leaves nothing behind."""
    prefix, _ = tailscale_cli()
    if not prefix:
        return False
    import subprocess
    try:
        p = subprocess.run(prefix + ["serve", "--tcp=%d" % port, "off"],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           timeout=timeout)
        return p.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def daemon_running():
    """Is our tailscaled up on this machine? A system install is asked for its
    `BackendState` (the Mac's daemon is a network extension); ours is found by
    exact process name, since `pgrep -f` matches anything mentioning it.
    """
    if tailscale_cli()[1] == "system":
        return (_ts_status() or {}).get("BackendState") == "Running"
    try:
        p = subprocess.run(["pgrep", "-x", "tailscaled"], stdout=subprocess.PIPE)
        return p.returncode == 0
    except OSError:
        return False


def tailscale_cli():
    """(argv_prefix, kind) for whichever tailscale this machine has: our own
    userspace `tailscaled` over a home-directory socket, or a system install
    already running, which must not be fought."""
    if os.path.exists(TS_SOCK):
        return (["tailscale", "--socket", TS_SOCK], "userspace")
    # A `tailscaled` under this home directory is ours to start, even before
    # its socket exists. One in a system directory belongs to a root daemon
    # already running for the same node key.
    daemon = shutil.which("tailscaled")
    if daemon and _ours(daemon):
        return (["tailscale", "--socket", TS_SOCK], "userspace")
    found = shutil.which("tailscale") or system_tailscale()
    if found:
        return ([found], "system")
    return (None, "missing")


def tailscale_download_hint():
    """The right static build to fetch. Every machine here needs its own."""
    return ("mkdir -p ~/.local/opt/tailscale\n"
            "curl -L https://pkgs.tailscale.com/stable/tailscale_%s_%s.tgz \\\n"
            "  | tar xz --strip-components=1 -C ~/.local/opt/tailscale\n"
            "ln -s ~/.local/opt/tailscale/tailscale{,d} ~/.local/bin/"
            % (latest_version(timeout=6) or FALLBACK_VERSION, _arch()))


# ---------------------------------------------------------------------------
# Which build the hint names
# ---------------------------------------------------------------------------
PKGS_INDEX = "https://pkgs.tailscale.com/stable/?mode=json"

# The fallback version when the index is unreachable; the one field that
# goes stale.
FALLBACK_VERSION = "1.102.3"


def _arch():
    import platform
    machine = platform.machine().lower()
    return {"x86_64": "amd64", "amd64": "amd64",
            "aarch64": "arm64", "arm64": "arm64"}.get(machine, "amd64")


def _is_version(v):
    """A version string, checked because it goes into a URL and a filename."""
    parts = (v or "").split(".")
    return (1 < len(parts) < 6 and len(v) < 32
            and all(p.isdigit() for p in parts))


def latest_version(timeout=15):
    """The version pkgs.tailscale.com serves today, or None when unreachable
    (not an error)."""
    import urllib.request
    try:
        with urllib.request.urlopen(PKGS_INDEX, timeout=timeout) as fh:
            got = json.loads(fh.read(1 << 20).decode("utf-8", "replace")) or {}
    except (OSError, ValueError):
        return None
    v = str((got or {}).get("TarballsVersion") or "").strip()
    return v if _is_version(v) else None
