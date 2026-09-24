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
# BOARD_STATE_DIR exists so a test can be run without writing the real thing.
# It is not a convenience: a bootstrap test once set this machine's tailnet name
# to the name of a different machine, which silently moved the address the iPad
# app was installed against. State that a test can reach is state a test will
# eventually corrupt.
TS_DIR = os.environ.get("BOARD_STATE_DIR") or os.path.join(paths.HOME, ".local", "state", "tailscale")
TS_SOCK = os.path.join(TS_DIR, "tailscaled.sock")

# Where a system-managed Tailscale keeps its CLI when it is not simply on PATH.
# Unlikely here: a cluster node has no administrator, which is why this tool runs
# its own tailscaled in userspace mode out of `$HOME`.
SYSTEM_TS = [
    "/usr/local/bin/tailscale",
    "/usr/bin/tailscale",
]


TS_NAME_FILE = os.path.join(TS_DIR, "hostname")


def tailnet_hostname():
    """What this machine calls itself on the tailnet.

    Defaults to `board`, which is what makes the address survive moving between
    compute nodes on a shared home. A second machine that is up at the same time
    needs its own name, or the two fight over one identity. Set once with `board
    vpn up --hostname <name>`.
    """
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
    """The netmap, as `tailscale status --json` gives it.

    Cached for a few seconds: who this machine is and what it is called are
    asked more than once in a breath, and neither can meaningfully change in
    between.
    """
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
    """This machine's own tailscale addresses, if it is on a tailnet.

    A board binds these as well as loopback: the tailnet is the trust boundary
    the iPad already crosses, and without them another machine cannot see this
    one's boards at all -- so a course served here can only ever be found from
    here.
    """
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
    # IPv4 only: the second socket is a convenience, and a v6 bind that fails on
    # a machine with no v6 route is noise in a log nobody reads.
    return [a for a in out if a.count(".") == 3]


def tailnet_self(status=None):
    """This machine's own tailnet name, which is not its hostname.

    A compute node is `compute302` to slurm and `compute-node` on the tailnet,
    and only the second one is reachable from anywhere else.
    """
    st = status if status is not None else _ts_status()
    name = ((st.get("Self") or {}).get("DNSName") or "").rstrip(".")
    return name


def publish_board(port, timeout=20):
    """Let the other machines on this tailnet reach this board.

    Binding the tailnet address directly is the obvious way and it does not work
    where it is most needed: a machine with no administrator rights runs
    tailscaled in USERSPACE mode, where the address exists but no interface
    carries it, and `bind()` returns "cannot assign requested address". Measured
    on the compute node, which is exactly the machine that has to be reachable.

    `tailscale serve --tcp` is the mechanism that works in both modes: tailscaled
    itself accepts the connection on the tailnet and forwards it to loopback. One
    per board, on the board's own port, so a course is reachable from the other
    machine at the same number it uses here -- which is what makes
    `locate_course` work without anything being published anywhere.
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
    """Is OUR tailscaled up on THIS machine?

    By process NAME. Asking `pgrep -f` for a string inside the command line
    matches anything that merely MENTIONS it -- every `srun bash -c` wrapper and
    every shell one-liner written to ask the question -- and a false yes is the
    worst answer available here: the caller concludes the link is up, never
    starts one, and the board serves on loopback at an address the iPad cannot
    reach, with every process looking healthy.
    """
    try:
        p = subprocess.run(["pgrep", "-x", "tailscaled"], stdout=subprocess.PIPE)
        return p.returncode == 0
    except OSError:
        return False


def tailscale_cli():
    """(argv_prefix, kind) for talking to whichever tailscale this machine has.

    Two shapes exist. On a machine with no administrator rights we run our own
    `tailscaled` in userspace mode and talk to it over a socket in the home
    directory. On a machine where Tailscale is already installed and running --
    a Mac, most obviously -- there is nothing to start and no socket to name;
    the system CLI is already connected and we should not fight it.
    """
    if os.path.exists(TS_SOCK):
        return (["tailscale", "--socket", TS_SOCK], "userspace")
    # A `tailscaled` WE CAN RUN, under this home directory, means the daemon is
    # ours to start and there is no system install to defer to.
    #
    # Deciding that on the socket file alone -- the line above, which used to be
    # the whole of it -- is a chicken and egg that can only be resolved by luck.
    # The socket exists only while our daemon is running, so on a node that has
    # not linked yet this fell through to the CLI we installed OURSELVES under
    # ~/.local/bin and called it a system install, and `board vpn up` then took
    # the "nothing to start, do not fight it" branch and started nothing. A fresh
    # node could therefore never bring the link up at all.
    #
    # It worked for a year by accident: Slurm SIGKILLs a node's processes when an
    # allocation ends, which leaves the socket file behind on the shared home,
    # and the next node read that leftover as "userspace". A graceful `board vpn
    # down` removes it -- so handing the board over deliberately, which is the
    # one time this has to work, was the one time it could not.
    #
    # In a system directory it is not ours: a root-run daemon is already there
    # and starting a second one would fight it for the same node key.
    daemon = shutil.which("tailscaled")
    if daemon and os.path.realpath(daemon).startswith(os.path.realpath(paths.HOME) + os.sep):
        return (["tailscale", "--socket", TS_SOCK], "userspace")
    found = shutil.which("tailscale")
    if found:
        return ([found], "system")
    for p in SYSTEM_TS:
        if os.path.exists(p):
            return ([p], "system")
    return (None, "missing")


def tailscale_download_hint():
    """The right static build to fetch. Every machine here needs its own."""
    return ("mkdir -p ~/.local/opt/tailscale\n"
            "curl -L https://pkgs.tailscale.com/stable/tailscale_%s_%s.tgz \\\n"
            "  | tar xz --strip-components=1 -C ~/.local/opt/tailscale\n"
            "ln -s ~/.local/opt/tailscale/tailscale{,d} ~/.local/bin/"
            % (latest_version(timeout=6) or FALLBACK_VERSION, _arch()))


# ---------------------------------------------------------------------------
# Keeping it current, which nothing else on this machine does
# ---------------------------------------------------------------------------
# An unprivileged Tailscale is a tarball somebody unpacked into their home
# directory once. No package manager knows about it, `tailscale update` refuses
# a static build, and there is no administrator to notice -- so it sits at
# whatever version the afternoon it was installed happened to serve, while the
# thing it talks to is a hosted control plane that moves. That is the same
# problem `vendor/colibri` has and it gets the same answer: the login hook, and
# the daily timer that stands in for a login on a machine left up for a week.
TS_OPT = os.environ.get("BOARD_TAILSCALE_DIR") or os.path.join(
    paths.HOME, ".local", "opt", "tailscale")
PKGS_INDEX = "https://pkgs.tailscale.com/stable/?mode=json"

# What the installer prints when the index cannot be reached. It is the version
# this was last known to work on, and it is the one field here that goes stale.
FALLBACK_VERSION = "1.102.3"

# Every compute node's login runs this against ONE shared home directory, so
# two of them arriving at the same minute would both download 76 MB into the
# same place. Stale after half an hour: a node killed mid-download leaves the
# file behind, and a lock nothing can clear is a machine that never updates
# again.
UPDATE_LOCK = os.path.join(TS_DIR, "update.lock")
LOCK_STALE = 1800

# ASKED AT MOST ONCE A DAY, because a login is not a rare event: a person opens
# four terminals on a node in a morning and each one runs the login hook. The
# stamp is written whether or not the index answered, so a node with no egress
# costs one timeout a day rather than one per terminal.
UPDATE_STAMP = os.path.join(TS_DIR, "update.checked")


def _arch():
    import platform
    machine = platform.machine().lower()
    return {"x86_64": "amd64", "amd64": "amd64",
            "aarch64": "arm64", "arm64": "arm64"}.get(machine, "amd64")


def _is_version(v):
    """A version string, and nothing that could be a path or a sentence.

    It goes into a URL and into a filename, so it is checked rather than
    trusted: this is a document on the internet, not a constant.
    """
    parts = (v or "").split(".")
    return (1 < len(parts) < 6 and len(v) < 32
            and all(p.isdigit() for p in parts))


def latest_version(timeout=15):
    """The version pkgs.tailscale.com is serving today, or None.

    None is a network answer, not an error: the index is unreachable from a
    node whose egress is down, and that is not a reason to say anything on a
    login.
    """
    import urllib.request
    try:
        with urllib.request.urlopen(PKGS_INDEX, timeout=timeout) as fh:
            got = json.loads(fh.read(1 << 20).decode("utf-8", "replace")) or {}
    except (OSError, ValueError):
        return None
    v = str((got or {}).get("TarballsVersion") or "").strip()
    return v if _is_version(v) else None


def installed_version():
    """The version of the Tailscale under this home, or None if there is none.

    Asked of the binary rather than of a file we wrote, because the binary is
    the thing that is actually going to run.
    """
    exe = os.path.join(TS_OPT, "tailscale")
    if not os.path.isfile(exe):
        return None
    try:
        p = subprocess.run([exe, "version"], stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    lines = p.stdout.decode("utf-8", "replace").strip().splitlines()
    v = lines[0].strip() if lines else ""
    return v if _is_version(v) else None


def _checked_today():
    try:
        with open(UPDATE_STAMP, "r", encoding="utf-8") as fh:
            return fh.read().strip() == time.strftime("%Y-%m-%d")
    except OSError:
        return False


def _mark_checked():
    try:
        os.makedirs(os.path.dirname(UPDATE_STAMP), exist_ok=True)
        with open(UPDATE_STAMP, "w", encoding="utf-8") as fh:
            fh.write(time.strftime("%Y-%m-%d") + "\n")
    except OSError:
        pass


def _take_lock(retry=True):
    try:
        os.makedirs(os.path.dirname(UPDATE_LOCK), exist_ok=True)
        fd = os.open(UPDATE_LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        try:
            stale = time.time() - os.path.getmtime(UPDATE_LOCK) > LOCK_STALE
        except OSError:
            return False
        if not stale or not retry:
            return False
        try:
            os.unlink(UPDATE_LOCK)
        except OSError:
            return False
        return _take_lock(retry=False)
    except OSError:
        # Nowhere to write a lock is not a reason to stop: a second download is
        # cheaper than a machine that never updates.
        return True
    os.close(fd)
    return True


def _drop_lock():
    try:
        os.unlink(UPDATE_LOCK)
    except OSError:
        pass


def update_userspace(quiet=False, force=False, timeout=300):
    """Move the userspace Tailscale in `$HOME` forward, and say so if it moved.

    `None` where there is nothing here of ours to update, `False` where it was
    tried and could not be done, `True` otherwise -- the shape `pull_vendor` in
    `bin/tutor` returns, because this is called from the same two places and by
    the same rules: quiet when there is nothing to do, and never fatal.

    Four decisions, and each one is a thing that would otherwise be wrong:

    * **Only the copy under this home.** A `/usr/bin/tailscale` belongs to root,
      there is no sudo on these nodes, and a second opinion about a root
      daemon's binary is worse than an old one.
    * **THE RUNNING DAEMON IS NOT RESTARTED.** Replacing the file leaves the
      live `tailscaled` on the inode it opened, so it goes on serving the
      tailnet name at the old version and the new binary is what the NEXT
      `board vpn up` starts -- on a compute node, the next allocation.
      Restarting it here would take the address down under somebody holding an
      iPad, which is the one thing this tool may not do to repair itself.
    * **Staged, then moved.** The archive is unpacked into a temporary directory
      beside the install and each binary is moved in with `os.replace`, which is
      atomic on one filesystem. A download that dies halfway can then never be
      the CLI.
    * **And PROVED before it is moved**, by running it and reading its version
      back. A tarball for the wrong architecture unpacks perfectly and is a
      machine with no Tailscale at all.
    """
    import shutil as _shutil
    import tarfile
    import tempfile
    import urllib.request

    def say(msg):
        if not quiet:
            print("  " + msg)

    if not os.path.isfile(os.path.join(TS_OPT, "tailscaled")):
        return None                      # not ours, or not here; nothing to do

    if not force and _checked_today():
        return True
    _mark_checked()

    have = installed_version()
    want = latest_version()
    if not want:
        return False                     # no index, no news; silent on a login
    if have == want:
        return True                      # current, and silent about that too

    if not _take_lock():
        return True                      # another node has it; not ours to say

    work = None
    try:
        work = tempfile.mkdtemp(prefix=".tailscale-update-",
                                dir=os.path.dirname(TS_OPT))
        tgz = os.path.join(work, "tailscale.tgz")
        url = ("https://pkgs.tailscale.com/stable/tailscale_%s_%s.tgz"
               % (want, _arch()))
        with urllib.request.urlopen(url, timeout=timeout) as fh:
            with open(tgz, "wb") as out:
                _shutil.copyfileobj(fh, out)

        # Two files out of the archive, by basename, so nothing it names can
        # decide where it lands. The systemd units in there are for a machine
        # with an administrator.
        with tarfile.open(tgz) as tar:
            for member in tar.getmembers():
                base = os.path.basename(member.name)
                if member.isfile() and base in ("tailscale", "tailscaled"):
                    member.name = base
                    tar.extract(member, work)
        staged = [os.path.join(work, n) for n in ("tailscale", "tailscaled")]
        if not all(os.path.isfile(f) for f in staged):
            say("tailscale %s: the archive did not carry both binaries" % want)
            return False
        for f in staged:
            os.chmod(f, 0o755)

        p = subprocess.run([staged[0], "version"], stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL, timeout=30)
        got = p.stdout.decode("utf-8", "replace").strip().splitlines()
        if p.returncode != 0 or not got or got[0].strip() != want:
            say("tailscale %s: the downloaded binary does not run here; "
                "leaving %s in place" % (want, have or "what is installed"))
            return False

        for f in staged:
            os.replace(f, os.path.join(TS_OPT, os.path.basename(f)))
    except (OSError, ValueError, tarfile.TarError,
            subprocess.SubprocessError) as exc:
        say("tailscale not updated: %s" % exc)
        return False
    finally:
        if work:
            _shutil.rmtree(work, ignore_errors=True)
        _drop_lock()

    say("tailscale %s -> %s; the running daemon keeps %s until it is next "
        "started" % (have or "an unknown version", want, have or "the old one"))
    return True
