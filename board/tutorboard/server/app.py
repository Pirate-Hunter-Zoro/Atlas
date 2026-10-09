"""Starting the board: parse the arguments and open the one listener.

    serve.py [--port N] [--atlas DIR] [--lan]

One process serves every session at `/s/<id>/`, on config.json's `port`
(default 8778) on loopback; `tailscale serve` publishes it, and nothing here
re-points it. A session's Repo and Hub are made on first use and dropped when
idle (`registry.py`). The runner (`runner/service.py`) takes every turn in this
process: started here after `recover`, and on SIGTERM it kills the turns in
flight, whose messages stay owed for the next start.
"""

import os
import shutil
import signal
import socketserver
import sys
import threading
from http.server import ThreadingHTTPServer

from .. import jobs, paths, subjects
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


def main(argv):
    if slurm_here():
        sys.stderr.write("serve.py: this is a Slurm host, and the board never runs "
                         "on the cluster; the cluster's entry is board/bin/relay\n")
        return 2
    atlas, port, host = parse(argv)
    httpd = make_server(atlas, port, host)
    runner = service.install(service.Runner(atlas, port=httpd.server_port))
    queued = runner.recover()
    runner.start()

    def stop(*_):
        runner.shutdown()
        raise SystemExit(0)
    signal.signal(signal.SIGTERM, stop)
    threading.Thread(target=httpd.registry.sweep_loop, daemon=True).start()
    # The mission sweep walks this machine's real workspaces, so a server on
    # a test tree (`--atlas`) leaves it off.
    if os.path.realpath(atlas) == os.path.realpath(subjects.root()):
        threading.Thread(target=spawn.sweep_missions, daemon=True).start()
    sys.stderr.write("board listening on http://%s:%d/ for %s; %d turn(s) at "
                     "once%s\n" % (host, httpd.server_port, atlas, runner.concurrency,
                                  "; recovered %s" % ", ".join(queued) if queued else ""))
    sys.stderr.flush()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        runner.shutdown()
