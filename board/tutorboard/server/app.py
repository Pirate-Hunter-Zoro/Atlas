"""Starting the board: parse the arguments and open the one listener.

    serve.py [--port N] [--atlas DIR] [--lan]

One process serves every session at `/s/<id>/`, on config.json's `port`
(default 8778) on loopback; `tailscale serve` publishes it, and nothing here
re-points it. A session's Repo and Hub are made on first use and dropped when
idle (`registry.py`). The runner (`runner/service.py`) takes every turn in this
process: started here after `recover`, and on SIGTERM it kills the turns in
flight, whose messages stay owed for the next start.

Two more threads, each switched on by the LaunchAgent's environment
(`scripts/launchd/tutor-board.plist`), so a server started by hand or by a
test runs neither:

  * `TUTORBOARD_CLUSTER=1`: the cluster thread (`cluster.Ear`), which pulls
    when origin's main moves, hears every subject's reports, and hears each
    `code/<id>` ref: a coding session's step at the cluster wakes its session.
  * `TUTORBOARD_FRESH=1`: the freshness thread. Once committed board code
    differs from what this process loaded (`stamp.moved`) and no turn runs
    or waits, the server stops listening and exits 0; launchd (KeepAlive)
    starts it again on the new code.

The boot line names the code stamp this process loaded.
"""

import os
import shutil
import signal
import socketserver
import sys
import threading
import time
from http.server import ThreadingHTTPServer

from .. import cluster, jobs, paths, sessions, stamp, subjects
from ..runner import service
from .handler import Handler
from . import spawn
from .registry import Registry


class BoardServer(ThreadingHTTPServer):
    """`ThreadingHTTPServer` without the reverse lookup in `server_bind`.

    `HTTPServer.server_bind` asks `socket.getfqdn` for the name of the address
    it bound, and nothing here reads the answer. On the Mac that lookup goes out
    through the tailnet's resolver and an exit node, and was measured taking
    over thirty seconds for the tailnet address -- longer than `board start`
    waits for the record, so a board started by `tutor watch` was called dead,
    killed as a leftover on the next pass, and started again.
    """

    def server_bind(self):
        socketserver.TCPServer.server_bind(self)
        host, port = self.server_address[:2]
        self.server_name = str(host)
        self.server_port = port


def parse(argv):
    """`(atlas, port, host)` from serve.py's arguments. `--port` and `--atlas`
    are for tests; the board itself runs with none."""
    atlas = subjects.root()
    port = paths.port()
    # Loopback by default. There is no authentication of any kind here, so
    # listening on every interface has to be a decision somebody made on purpose.
    # `tailscale serve` reaches the board through 127.0.0.1.
    host = "127.0.0.1"
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("--atlas", "-a"):
            i += 1
            atlas = argv[i]
        elif a in ("--port", "-p"):
            i += 1
            port = int(argv[i])
        elif a == "--lan":
            host = "0.0.0.0"
        elif a == "--local":
            host = "127.0.0.1"
        elif a in ("--root", "-r"):
            raise SystemExit("serve.py serves every session under /s/<id>/; "
                             "--root is gone (use --atlas for a test tree)")
        else:
            raise SystemExit("serve.py: unknown argument %r" % a)
        i += 1
    return os.path.abspath(atlas), port, host


def make_server(atlas, port, host="127.0.0.1", start=True):
    """The one listener, with its session registry. `start` False builds
    hubs that run no threads, for a test that drives them itself."""
    httpd = BoardServer((host, port), Handler)
    httpd.daemon_threads = True
    httpd.registry = Registry(atlas, start=start)
    return httpd


def slurm_here():
    """Is this a Slurm host? `jobs.has_slurm()` (so `TUTOR_SLURM=1` says yes),
    or `sbatch` on PATH whatever `TUTOR_SLURM` says: no board server runs on
    the cluster, and an override meant for tests does not make one."""
    return jobs.has_slurm() or shutil.which("sbatch") is not None


# How often the freshness thread asks git whether the committed code moved.
FRESH_EVERY = 5.0


def watch_fresh(httpd, runner, every=FRESH_EVERY, say=None):
    """The freshness thread: once `stamp.moved()` says why and the runner
    stops with nothing running or queued, stop the listener so `main`
    returns 0. Returns the reason."""
    say = say or (lambda msg: (sys.stderr.write(msg + "\n"), sys.stderr.flush()))
    while True:
        time.sleep(every)
        try:
            why = stamp.moved()
        except Exception:                                    # noqa: BLE001
            why = None
        if not why or not runner.quiesce():
            continue
        say("board: %s and no turn runs; exiting 0 for launchd to start the "
            "new code" % why)
        httpd.fresh = why
        httpd.shutdown()
        return why


def main(argv):
    if slurm_here():
        sys.stderr.write("serve.py: this is a Slurm host, and the board never runs "
                         "on the cluster; the cluster's entry is board/bin/relay\n")
        return 2
    atlas, port, host = parse(argv)
    httpd = make_server(atlas, port, host)
    httpd.fresh = None
    runner = service.install(service.Runner(atlas, port=httpd.server_port))
    queued = runner.recover()
    runner.start()

    def stop(*_):
        runner.shutdown()
        raise SystemExit(0)
    signal.signal(signal.SIGTERM, stop)
    threading.Thread(target=httpd.registry.sweep_loop, daemon=True).start()
    # The trash keeps a delete 30 days; older entries go at startup.
    try:
        pruned = sessions.prune_trash()
    except OSError:
        pruned = []
    # The mission sweep walks this machine's real workspaces, so a server on
    # a test tree (`--atlas`) leaves it off.
    if os.path.realpath(atlas) == os.path.realpath(subjects.root()):
        threading.Thread(target=spawn.sweep_missions, daemon=True).start()
    threads = []
    if os.environ.get("TUTORBOARD_CLUSTER") == "1":
        cluster.Ear(atlas).start()
        threads.append("cluster")
    if os.environ.get("TUTORBOARD_FRESH") == "1":
        threading.Thread(target=watch_fresh, args=(httpd, runner),
                         name="fresh", daemon=True).start()
        threads.append("fresh")
    sys.stderr.write("board listening on http://%s:%d/ for %s; code %s; pid %d; "
                     "%d turn(s) at once%s%s\n" % (
                         host, httpd.server_port, atlas, stamp.LOADED or "unknown",
                         os.getpid(), runner.concurrency,
                         "; threads: %s" % ", ".join(threads) if threads else "",
                         "; recovered %s" % ", ".join(queued) if queued else ""))
    if pruned:
        sys.stderr.write("board: pruned %d trash entr%s older than %d days\n" % (
            len(pruned), "y" if len(pruned) == 1 else "ies", sessions.TRASH_DAYS))
    sys.stderr.flush()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        runner.shutdown()
        return 0
    runner.shutdown()
    return 0
