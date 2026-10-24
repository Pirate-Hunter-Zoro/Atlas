#!/usr/bin/env python3
"""One server, one port, one HTTPS name, and nothing automatic may move it.

The iPad has ONE address baked into it. `tailscale serve` publishes it to
127.0.0.1 on config.json's `port` (default 8778) once, and one `serve.py`
listens there for every session, at `/s/<id>/`. Part 0 checks that server:
the port it takes, the arguments it accepts, that it opens exactly one
listener, and that nothing in it touches the tailnet name.

Part 1 checks that the per-workspace machinery is gone: no `board start`,
`stop` or address-moving `vpn serve`, and no old launcher.
"""

import importlib.machinery
import importlib.util
import os
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


# Never the real one: a test that writes this has renamed the live machine on
# the tailnet before now, which silently moved the address the iPad app is
# installed against.
os.environ["BOARD_STATE_DIR"] = tempfile.mkdtemp(prefix="tutor-serving-")


def load(rel, name):
    """Import one of the CLIs, which are scripts with no `.py` to import by."""
    path = os.path.join(ROOT, rel)
    loader = importlib.machinery.SourceFileLoader(name, path)
    spec = importlib.util.spec_from_loader(name, loader)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# 0. The one server.
# ---------------------------------------------------------------------------
import json                                                   # noqa: E402
import re                                                     # noqa: E402
import shutil                                                 # noqa: E402
import subprocess                                             # noqa: E402
import time                                                   # noqa: E402
import urllib.request                                         # noqa: E402

cfg_home = tempfile.mkdtemp(prefix="tutor-serving-cfg-")
os.environ["XDG_CONFIG_HOME"] = cfg_home
sys.path.insert(0, ROOT)
from tutorboard import paths as tb_paths                      # noqa: E402
from tutorboard.server import app as tb_app                   # noqa: E402

check("the config lives where XDG_CONFIG_HOME says, in a test",
      tb_paths.CONFIG.startswith(cfg_home))
check("with no config the board takes 8778",
      tb_paths.port() == 8778 and tb_app.parse([])[1] == 8778)
os.makedirs(tb_paths.CONFIG_DIR, exist_ok=True)
with open(tb_paths.CONFIG, "w", encoding="utf-8") as fh:
    json.dump({"port": 8790}, fh)
check("config.json's port is the board's port", tb_app.parse([])[1] == 8790)
atlas_tmp = tempfile.mkdtemp(prefix="tutor-serving-atlas-")
check("--port and --atlas override it, for tests",
      tb_app.parse(["--port", "8779", "--atlas", atlas_tmp])[:2]
      == (os.path.abspath(atlas_tmp), 8779))
check("and it listens on loopback unless told otherwise",
      tb_app.parse([])[2] == "127.0.0.1")


def refused(argv):
    try:
        tb_app.parse(argv)
    except SystemExit:
        return True
    return False


check("--root is refused: one server serves every session",
      refused(["--root", atlas_tmp]))
check("and so is an argument it does not know", refused(["--bogus"]))

app_src = open(os.path.join(ROOT, "tutorboard", "server", "app.py"),
               encoding="utf-8").read()
check("nothing in the server touches the tailnet name",
      "import tailscale" not in app_src and "tailscale." not in app_src)
check("and it writes no per-workspace record", ".board.json" not in app_src)

env = dict(os.environ, BOARD_STATE_DIR=tempfile.mkdtemp(prefix="tutor-serving-st-"))
proc = subprocess.Popen([sys.executable, os.path.join(ROOT, "serve.py"), "--port", "0",
                         "--atlas", atlas_tmp], stderr=subprocess.PIPE, env=env)
try:
    line = proc.stderr.readline().decode("utf-8", "replace")
    found = re.search(r"http://127\.0\.0\.1:(\d+)/", line)
    port = int(found.group(1)) if found else 0
    health = {}
    deadline = time.time() + 20
    while port and time.time() < deadline:
        try:
            with urllib.request.urlopen("http://127.0.0.1:%d/health" % port,
                                        timeout=5) as r:
                health = json.loads(r.read().decode("utf-8"))
            break
        except OSError:
            time.sleep(0.1)
    check("serve.py starts and answers /health for its tree",
          health.get("atlas") == os.path.realpath(atlas_tmp)
          or health.get("atlas") == os.path.abspath(atlas_tmp))
    if shutil.which("lsof"):
        out = subprocess.run(["lsof", "-nP", "-a", "-p", str(proc.pid), "-iTCP",
                              "-sTCP:LISTEN"], stdout=subprocess.PIPE,
                             stderr=subprocess.DEVNULL).stdout.decode("utf-8", "replace")
        listening = [ln for ln in out.splitlines()[1:] if "LISTEN" in ln]
        check("serve.py opens exactly one listener (%d)" % len(listening),
              len(listening) == 1 and (":%d " % port) in listening[0] + " ")
    else:
        print("SKIP lsof is missing; the listener count was not checked")
finally:
    proc.terminate()
    proc.wait(10)
    shutil.rmtree(cfg_home, ignore_errors=True)
    shutil.rmtree(atlas_tmp, ignore_errors=True)

brd = load("bin/board", "board_cli_serving")

# ---------------------------------------------------------------------------
# 1. Nothing per-workspace is left to move the name.
# ---------------------------------------------------------------------------
gone = ("free_port", "default_port", "served_ports", "recorded_ports",
        "boards_serving", "drop_strays", "ts_" + "repoint", "cmd_start", "cmd_stop")
check("bin/board has no per-workspace server machinery: " +
      ", ".join(n for n in gone if hasattr(brd, n)),
      not any(hasattr(brd, n) for n in gone))
check("and no `board start` or `board stop`",
      "start" not in brd.COMMANDS and "stop" not in brd.COMMANDS)
calls = []
brd.ts = lambda *a, **kw: (calls.append(a) or (0, ""))
import contextlib                                             # noqa: E402
import io                                                     # noqa: E402
with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
    refused_serve = brd.cmd_vpn(None, ["serve"])
    brd.cmd_vpn(None, ["status"])
check("`board vpn` only reports: serve is refused, and status sets nothing",
      refused_serve != 0 and calls
      and not any("--bg" in a or a[:1] in (("up",), ("down",)) for a in calls))
check("the old launcher is gone", not os.path.exists(os.path.join(ROOT, "bin", "tutor")))
for mod in ("ports", "choice", "supervise", "processes", "machines"):
    check("tutorboard/%s.py is gone" % mod,
          not os.path.exists(os.path.join(ROOT, "tutorboard", mod + ".py")))

print()
if fails:
    print("%d FAILURES" % len(fails))
    sys.exit(1)
print("one server, one address, and nothing automatic moves it")
