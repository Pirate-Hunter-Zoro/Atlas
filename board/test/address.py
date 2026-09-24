#!/usr/bin/env python3
"""The tailnet address belongs to a course, and a deploy must not move it.

The installed iPad app has exactly one URL baked into it. Which lesson that URL
opens is decided by what the HTTPS name proxies to -- and starting a board used
to claim that name unconditionally. `tutor restart` restarts every board on the
machine, one after another, so a deploy handed the address to whichever course
came last in the list. Somebody halfway through a Galois proof was dropped into
a completely different course by a push, with no way to say which one they meant.

The rule this file holds: a name already pointing at a board that is up and
answering is that board's. A start does not take it. What takes it is the name
pointing at nothing, or an explicit `board vpn serve` -- a person saying which
course they mean.
"""

import importlib.machinery
import importlib.util
import os
import shutil
import socket
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

errors = []


def ok(m):
    print("ok   " + m)


def fail(m):
    errors.append(m)
    print("FAIL " + m)


sys.path.insert(0, ROOT)
spec = importlib.util.spec_from_loader(
    "boardcli", importlib.machinery.SourceFileLoader("boardcli", os.path.join(ROOT, "bin", "board")))
board = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(board)
except Exception as exc:                                   # noqa: BLE001
    print("FAIL bin/board did not import: %s" % exc)
    sys.exit(1)
ok("bin/board imports without running")

STATUS = ("Available within your tailnet:\n\n"
          "https://board.tail0c6c62.ts.net/\n"
          "|-- proxy http://127.0.0.1:8787\n")

if board.served_port(STATUS) == 8787:
    ok("the port the name points at can be read back")
else:
    fail("served_port read %r out of a real serve status" % board.served_port(STATUS))

if board.served_port("nothing here") is None:
    ok("and a status with no proxy in it reads as nobody holding the name")
else:
    fail("served_port invented a port out of an empty status")

# `ts` folds stderr into stdout, and a client/daemon version skew prints a
# warning there -- so a real `status --json` can open with prose, not the JSON
# object. ts_info must still find the object rather than bail on the warning.
def _ts_warned(*a, **k):
    return 0, ("Warning: client version mismatch\n"
               '{"Self":{"DNSName":"board.tail0c6c62.ts.net.",'
               '"TailscaleIPs":["100.0.0.1","fd7a::1"]}}')

board.ts = _ts_warned
v4, name = board.ts_info()
if name == "board.tail0c6c62.ts.net" and v4 == "100.0.0.1":
    ok("ts_info reads the JSON behind a folded warning line")
else:
    fail("ts_info got %r / %r out of a status carrying a warning" % (v4, name))

# A real listener, so port_answers is tested against a socket and not a mock.
srv = socket.socket()
srv.bind(("127.0.0.1", 0))
srv.listen(1)
live_port = srv.getsockname()[1]

if board.port_answers(live_port):
    ok("a port with something listening on it answers")
else:
    fail("port_answers said no to a socket that is listening")

srv.close()
if board.port_answers(live_port):
    fail("port_answers said yes to a closed port")
else:
    ok("and a closed one does not")

# ---- the rule itself -------------------------------------------------------
#
# Drive ts_repoint with the tailnet stubbed out, and watch whether it issues the
# command that moves the address.

calls = []


def install(status, held_alive, held_recorded=True):
    """Stand in for the tailscale daemon: what the name points at, whether the
    board it points at is still answering, and whether any live record names it.

    THE THIRD ARGUMENT IS NOT A DETAIL. A board an ended generation left behind
    answers exactly like a live one, and its repository's one record was
    overwritten by the board that replaced it -- so on the answering test alone
    it held the address against everything that came after it. Answering is not
    owning; see `recorded_ports` in `bin/board`.
    """
    calls[:] = []
    board.ts_daemon_running = lambda *a, **k: True
    board.ts_info = lambda *a, **k: ("100.0.0.1", "board.tail0c6c62.ts.net")
    board.port_answers = lambda p: held_alive
    board.recorded_ports = lambda: ({8787} if held_recorded else set())
    # serve_target branches on machine shape, which reads the real config. A test
    # must not depend on whatever that file happens to say, so pin it: these
    # cases are about a machine that points the name at its own board.
    board.machine.machine_shape = lambda: "standalone"

    def ts(*args, **kwargs):
        if args[:2] == ("serve", "status"):
            return 0, status
        calls.append(args)
        return 0, "serving"
    board.ts = ts


# The name points at a board on THIS machine, whatever kind of machine it is.
# `tailscale serve` only proxies to a local backend -- handed a remote tailnet
# address it answers every request with a 502 -- so there is nowhere else for it
# to point.
for shape in ("standalone", "compute node"):
    board.machine.machine_shape = lambda shape=shape: shape
    if board.serve_target(8787) == "http://127.0.0.1:8787":
        ok("on a %s the name points at the board's own port" % shape)
    else:
        fail("serve_target on a %s did not point at the board" % shape)


held = ("https://board.tail0c6c62.ts.net/\n|-- proxy http://127.0.0.1:8787\n")

install(held, held_alive=True)
board.ts_repoint(8812)
if calls:
    fail("starting another course took the address from a board that is still "
         "answering — this is the deploy that moved somebody mid-proof")
else:
    ok("a board that is up keeps the address when another course starts")

install(held, held_alive=False)
board.ts_repoint(8812)
if calls:
    ok("but a name pointing at a board that has gone is picked up")
else:
    fail("the address was left pointing at a dead board, which is a blank screen")

install(held, held_alive=True)
board.ts_repoint(8812, force=True)
if calls:
    ok("and `board vpn serve` still takes it, because that is a person asking")
else:
    fail("nothing can move the address deliberately any more")

install(held, held_alive=True)
board.ts_repoint(8787)
if calls:
    fail("the board already holding the address re-pointed it at itself")
else:
    ok("and re-pointing at where it already points does nothing at all")

# AND THE ONE THAT COST AN EVENING. A board left behind by an ended generation
# answers perfectly and is named by no record: its repository holds one
# `.board.json` and the board that replaced it overwrote it. So it is invisible
# to everything that works from records, and it held the one address the iPad is
# installed against for an hour and three quarters while the live board served
# another port -- with the tutor up, the chain three generations deep, and every
# status command green.
install(held, held_alive=True, held_recorded=False)
board.ts_repoint(8812)
if calls:
    ok("a board left behind by an ended generation does not hold the address, "
       "however healthily it answers")
else:
    fail("a leftover board keeps the address for as long as its process lives, "
         "which is the whole of being left hanging with nothing looking wrong")

# A board has to be REACHABLE from the other machine, or none of the above can
# happen at all.
#
# Boards bound 127.0.0.1 and nothing else, deliberately -- there is no
# authentication here. The consequence went unseen for a week: asking another
# machine where a course is served means probing its ports, and every one of
# those probes was refused by a loopback socket. So a course could only ever be
# found on the machine doing the asking.
src_serve = open(os.path.join(ROOT, "tutorboard", "server", "app.py"),
                 encoding="utf-8").read()
(ok if "for addr in tailscale.tailnet_addresses():" in src_serve else fail)(
    "a board listens on this machine's tailnet address as well as loopback")
(ok if "for a in tailnet]" in src_serve else fail)(
    "and says so in its record, so the far side knows where to knock")
(ok if "tailscale.publish_board(port)" in src_serve else fail)(
    "and where binding is impossible -- userspace tailscaled, which is every "
    "machine without administrator rights -- tailscaled forwards for it instead")
src_board = open(os.path.join(ROOT, "bin", "board"), encoding="utf-8").read()
(ok if "tailscale.unpublish_board(" in src_board else fail)(
    "and a stopped board takes its forwarding rule with it, rather than leaving "
    "one that points at a port nothing answers on")
(ok if 'if host == "0.0.0.0"' in src_serve else fail)(
    "but not on the LAN unless somebody asked for that")


# ---- and the client stays current, which nothing else here does -----------
#
# An unprivileged Tailscale is a tarball somebody unpacked into a home
# directory. No package manager knows it exists, `tailscale update` refuses a
# static build, and there is no administrator to notice -- so it sits at the
# version of the afternoon it was installed while the hosted control plane it
# talks to moves. `vendor/colibri` has the same problem and gets the same two
# moments: the login hook, and the daily timer that stands in for a login on a
# machine left up for a week.
#
# Everything below runs against a FAKE install and a FAKE index. The real one
# is what this machine is on the tailnet with, and a suite that replaces those
# binaries takes the address down under whoever is holding the iPad.
import io as _io
import json as _json
import tarfile
import tempfile
import time as _time
import urllib.request

from tutorboard.net import tailscale as ts                   # noqa: E402

(ok if ts._is_version("1.102.4") else fail)("a version is digits and dots")
(ok if not any(ts._is_version(v) for v in
               ("", "latest", "1", "../../etc/passwd", "1.2.3; rm -rf ~",
                "1." + "9" * 40))
 else fail)("and anything that could be a path or a command is not one, "
            "because it goes into a URL and into a filename")

sand = tempfile.mkdtemp(prefix="tutor-ts-update-")
ts.TS_OPT = os.path.join(sand, "opt")
ts.UPDATE_LOCK = os.path.join(sand, "update.lock")
ts.UPDATE_STAMP = os.path.join(sand, "update.checked")
os.makedirs(ts.TS_OPT)

asked = []
real_urlopen = urllib.request.urlopen


def tarball(version, prints):
    """A tarball shaped like the one pkgs.tailscale.com serves."""
    buf = _io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name in ("tailscale", "tailscaled"):
            body = ("#!/bin/sh\necho %s\n" % prints).encode()
            info = tarfile.TarInfo("tailscale_%s_amd64/%s" % (version, name))
            info.size = len(body)
            info.mode = 0o755
            tar.addfile(info, _io.BytesIO(body))
    return buf.getvalue()


SERVED = {"version": "9.9.9", "prints": "9.9.9"}


def fake_urlopen(url, timeout=None):
    asked.append(url)
    if url == ts.PKGS_INDEX:
        return _io.BytesIO(_json.dumps(
            {"TarballsVersion": SERVED["version"]}).encode())
    if url.endswith(".tgz"):
        return _io.BytesIO(tarball(SERVED["version"], SERVED["prints"]))
    raise OSError("nothing serves %s" % url)


urllib.request.urlopen = fake_urlopen


def install(version):
    for name in ("tailscale", "tailscaled"):
        path = os.path.join(ts.TS_OPT, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("#!/bin/sh\necho %s\n" % version)
        os.chmod(path, 0o755)


def wipe_stamp():
    if os.path.exists(ts.UPDATE_STAMP):
        os.remove(ts.UPDATE_STAMP)


try:
    del asked[:]
    (ok if ts.update_userspace(quiet=True) is None else fail)(
        "with no install of ours in this home, there is nothing to update")
    (ok if not asked else fail)(
        "and the index is not asked about a machine whose tailscale belongs "
        "to root, because there is no sudo here to use the answer")

    install("1.0.0")
    (ok if ts.installed_version() == "1.0.0" else fail)(
        "the installed version is read off the binary that will actually run")

    del asked[:]
    (ok if ts.update_userspace(quiet=True) is True else fail)(
        "a newer version is fetched, proved and moved into place")
    (ok if ts.installed_version() == "9.9.9" else fail)(
        "and the CLI on the path is the new one")

    # The property that makes this safe to run under a live daemon: the file is
    # REPLACED rather than written through, so the running tailscaled keeps the
    # inode it opened and goes on serving the tailnet name at the old version.
    live = open(os.path.join(ts.TS_OPT, "tailscaled"), "rb")
    before = os.fstat(live.fileno()).st_ino
    SERVED["version"] = SERVED["prints"] = "9.9.10"
    wipe_stamp()
    ts.update_userspace(quiet=True)
    after = os.stat(os.path.join(ts.TS_OPT, "tailscaled")).st_ino
    (ok if before != after and b"9.9.9" in live.read() else fail)(
        "an update swaps the inode rather than rewriting the file, so a live "
        "tailscaled keeps the binary it is running and the tailnet name does "
        "not go down to update it")
    live.close()

    # The stamp. A login is not a rare event -- four terminals on a node in a
    # morning is four logins -- and each one asking the internet is three of
    # them wasted.
    del asked[:]
    (ok if ts.update_userspace(quiet=True) is True and not asked else fail)(
        "a second login the same day asks nothing at all")
    del asked[:]
    SERVED["version"] = SERVED["prints"] = "9.9.11"
    (ok if ts.update_userspace(quiet=True, force=True) is True
        and ts.installed_version() == "9.9.11" else fail)(
        "while `tutor pull` forces it, because that IS the daily job")

    # A binary that does not run is not an update. An archive for the wrong
    # architecture unpacks perfectly and leaves a machine with no Tailscale.
    wipe_stamp()
    SERVED["version"] = "9.9.12"
    SERVED["prints"] = "not-a-version"
    (ok if ts.update_userspace(quiet=True) is False
        and ts.installed_version() == "9.9.11" else fail)(
        "a download that will not run here is refused and the working one is "
        "left exactly where it was")

    # One shared home, seven compute nodes, and every login runs this.
    wipe_stamp()
    SERVED["version"] = SERVED["prints"] = "9.9.13"
    with open(ts.UPDATE_LOCK, "w", encoding="utf-8") as fh:
        fh.write("")
    del asked[:]
    (ok if ts.update_userspace(quiet=True) is True
        and ts.installed_version() == "9.9.11" else fail)(
        "with another node already downloading into the same home directory, "
        "this one stands aside rather than fetching 76 MB over the top of it")
    os.utime(ts.UPDATE_LOCK, (_time.time() - ts.LOCK_STALE - 60,) * 2)
    wipe_stamp()
    (ok if ts.update_userspace(quiet=True) is True
        and ts.installed_version() == "9.9.13" else fail)(
        "and a lock left behind by a node that was killed mid-download goes "
        "stale, because a lock nothing can clear is a machine that never "
        "updates again")

    # No index, no news. A node whose egress is down has worse problems and a
    # login is not where it should hear about them.
    wipe_stamp()
    urllib.request.urlopen = lambda url, timeout=None: (_ for _ in ()).throw(
        OSError("no route"))
    (ok if ts.update_userspace(quiet=True) is False
        and ts.installed_version() == "9.9.13" else fail)(
        "an unreachable index changes nothing and leaves the install alone")
finally:
    urllib.request.urlopen = real_urlopen
    shutil.rmtree(sand, ignore_errors=True)

# And the two moments it happens in, which are `vendor/colibri`'s two moments.
src_tutor = open(os.path.join(ROOT, "bin", "tutor"), encoding="utf-8").read()
(ok if "tailscale.update_userspace(quiet=quiet)" in src_tutor else fail)(
    "a login pulls the tailscale client forward, which is the one moment a "
    "compute node gets")
(ok if "tailscale.update_userspace(quiet=quiet, force=True)" in src_tutor else fail)(
    "and so does `tutor pull`, which is what the daily timer runs on a "
    "machine that is left up and never has a login")

print("\n%d FAILURES" % len(errors) if errors else "\nthe address stays with the course")
sys.exit(1 if errors else 0)
