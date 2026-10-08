#!/usr/bin/env python3
"""One server, one port, one HTTPS name, and nothing automatic may move it.

The iPad has ONE address baked into it. `tailscale serve` publishes it to
127.0.0.1 on config.json's `port` (default 8778) once, and one `serve.py`
listens there for every session, at `/s/<id>/`. Part 0 checks that server:
the port it takes, the arguments it accepts, that it opens exactly one
listener, and that nothing in it touches the tailnet name.

Parts 1 to 4 check the per-workspace boards that still exist until T49
deletes them. There the name could move a person mid-sentence into another
course, and four separate faults each did it: a bare `board vpn serve` on
every launch, `served_port` reading the first TCP forward instead of the
name's proxy line, `tutor restart` letting a board claim a name pointing at
nothing, and a guard reading "answering" as "somebody's lesson" while an
ended generation's board held the address. Each is checked by what the code
does.
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
# 1. The parse. This is the real shape: a tree of TCP forwards, one per board,
#    and the https names last with their proxy targets.
# ---------------------------------------------------------------------------
STATUS = """\
|-- tcp://compute-node.tail0c6c62.ts.net:8937 (tailnet only)
|-- tcp://100.105.212.85:8937
|--> tcp://127.0.0.1:8937
|-- tcp://compute-node.tail0c6c62.ts.net:9171 (tailnet only)
|--> tcp://127.0.0.1:9171

https://board.tail0c6c62.ts.net (tailnet only)
|-- / proxy http://127.0.0.1:8787

https://compute-node.tail0c6c62.ts.net (tailnet only)
|-- / proxy http://127.0.0.1:9098
"""

by_name = brd.served_by_name(STATUS)
check("a name's target is read off its proxy line, not off a TCP forward",
      by_name.get("compute-node.tail0c6c62.ts.net") == 9098)
check("and every name is read, because two of them can point different ways",
      by_name.get("board.tail0c6c62.ts.net") == 8787)
check("a TCP forward is never mistaken for the address",
      8937 not in by_name.values() and 9171 not in by_name.values())
check("and the ports an https name serves are exactly the proxied ones",
      sorted(brd.served_ports(STATUS)) == [8787, 9098])
check("an empty status says nobody holds it, rather than guessing",
      brd.served_ports("") == [] and brd.served_by_name("") == {})

# ---------------------------------------------------------------------------
# 2. The guard. A name held by a board that is UP is that board's, and a start
#    does not take it. A name pointing at nothing is free.
# ---------------------------------------------------------------------------
calls = []


def fake_ts(*args, **kw):
    calls.append(args)
    if args[:2] == ("serve", "status"):
        return 0, STATUS
    return 0, ""


brd.ts = fake_ts
brd.ts_daemon_running = lambda: True
brd.ts_info = lambda: ("100.0.0.1", "compute-node.tail0c6c62.ts.net")

# 9098 answers AND a live record names it -- it is somebody's lesson -- so 9171
# coming up must not take it. Both halves are stubbed because both are the test:
# answering alone is what let a leftover hold the address.
brd.port_answers = lambda p: p == 9098
brd.recorded_ports = lambda: {9098}
calls[:] = []
brd.ts_repoint(9171)
check("a board coming up does not take a name that points at a live board",
      not any(a[:1] == ("serve",) and "--bg" in a for a in calls))

# Nothing answers on the port the name points at: the course whose board that
# was has gone, and leaving the address pointing at a corpse helps nobody.
brd.port_answers = lambda p: False
brd.recorded_ports = lambda: set()
calls[:] = []
brd.ts_repoint(9171)
check("but it does take one that points at nothing at all",
      any("--bg" in a for a in calls))

# AND THE ONE THAT COST AN EVENING: a board that answers and that NO RECORD
# NAMES. Its repository's record was overwritten by the board that replaced it,
# so it is invisible to everything that reads records -- and on the answering
# test alone it outranked the live board for as long as its process survived.
# Answering is not owning.
brd.port_answers = lambda p: p == 9098
brd.recorded_ports = lambda: {9171}
calls[:] = []
brd.ts_repoint(9171)
check("a board left behind by an ended generation does not hold the address, "
      "however healthily it answers",
      any("--bg" in a for a in calls))

# AND "CANNOT TELL" IS NOT "NOBODY HAS ONE". Where the repository layout cannot
# be read at all, `recorded_ports` answers None and the guard falls back to the
# rule it replaced -- believe answering, leave the name alone. An empty set here
# would read as "no record names anything", which takes the address from whoever
# is holding it, in exactly the case where least is known.
brd.port_answers = lambda p: p == 9098
brd.recorded_ports = lambda: None
calls[:] = []
brd.ts_repoint(9171)
check("and where nothing can be read, it leaves the address where it is",
      not any("--bg" in a for a in calls))

# And forced, when a person says which course they mean.
brd.port_answers = lambda p: p == 9098
brd.recorded_ports = lambda: {9098}
calls[:] = []
brd.ts_repoint(9171, force=True)
check("and a forced claim takes it whatever is holding it",
      any("--bg" in a for a in calls))


# ---------------------------------------------------------------------------
# 3. What each caller is entitled to. `--if-free` asks; a bare serve forces; and
#    anything that runs WITHOUT a person present must ask.
# ---------------------------------------------------------------------------
board_src = open(os.path.join(ROOT, "bin", "board"), encoding="utf-8").read()
# The launcher and the daemon machinery it was split into.
_runner = os.path.join(ROOT, "tutorboard", "runner")
tutor_src = "".join(open(p, encoding="utf-8").read() for p in (
    [os.path.join(ROOT, "bin", "tutor")]
    + [os.path.join(_runner, f) for f in sorted(os.listdir(_runner))
       if f.endswith(".py")]))

check("`vpn serve --if-free` exists, and routes through the guard",
      '"--if-free" in args' in board_src and board_src.count('"--if-free" in args') >= 2)

watch = tutor_src[tutor_src.index("def watch_once("):]
watch = watch[:watch.index("\ndef ", 1)]
check("the watchdog's own claim, where nobody chose, asks first",
      '"vpn", "serve", "--if-free")' in watch)
check("and the launcher has no claim of its own any more",
      "def link(" not in tutor_src)

# AND THE LEFTOVER IS NOT MERELY OUTRANKED, IT IS STOPPED. The moment a
# repository's next board starts is the moment the previous one became a
# leftover, and `.board.json` holds one pid -- so a second live board for one
# repository is unreachable by every command that works from the record, while
# still holding a port, a socket and, on the answering test, the address.
start = board_src[board_src.index("def cmd_start("):]
start = start[:start.index("\ndef ", 1)]
check("a new board clears what its own repository left behind, before it starts",
      start.find("drop_strays(live)") != -1
      and start.find("drop_strays(live)") < start.find("subprocess.Popen"))
check("and it only ever stops this repository's own, on this node",
      "paths.same_dir(at, root)" in board_src)
check("answering is not owning, and the guard says which it means",
      "recorded_ports()" in board_src
      and "p in mine" in board_src)

# ---------------------------------------------------------------------------
# 4. A deploy restarts every board, so it must remember who had the name BEFORE
#    it starts stopping things -- while the answer is still true.
# ---------------------------------------------------------------------------
restart = tutor_src[tutor_src.index("def cmd_restart("):]
restart = restart[:restart.index("\ndef ", 1)]
asked = restart.find('"vpn", "holder"')
stopped = restart.find('board(c["root"], "stop")')
check("a restart reads the holder before it stops anything",
      asked != -1 and stopped != -1 and asked < stopped)
check("and hands the name back afterwards",
      restart.find('"vpn", "serve"') > stopped)

print()
if fails:
    print("%d FAILURES" % len(fails))
    sys.exit(1)
print("one server, one address, and nothing automatic moves it")
