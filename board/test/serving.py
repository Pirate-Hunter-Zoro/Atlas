#!/usr/bin/env python3
"""One HTTPS name, one board, and nothing automatic may take it.

The iPad has ONE address baked into it. There is no way from that device to say
which course was meant, so whichever board the name points at is the course the
person is in -- and moving it moves them, mid-sentence, with no warning and no
way back. It happened: somebody three cards into a proof about field extensions
looked up at a board labelled PSYCH-ASR, and the mathematics they had just
handed in had gone into another workspace's transcript.

Three separate things had to be wrong for that, and each of them reads as
harmless on its own:

  1. `link()` in `bin/tutor` called a bare `board vpn serve` on every launch.
     That command is the FORCED claim -- its whole meaning is "point the address
     at THIS course", which is a sentence only a person is entitled to say. So
     starting a tutor anywhere took the address from whatever was being read.

  2. `served_port` read the first `127.0.0.1:PORT` out of `tailscale serve
     status`. That output lists a TCP forward per board AND the https names at
     the bottom, so the first match is a forward belonging to whichever board
     the daemon felt like printing first. The guard against stealing the name
     was therefore a coin toss.

  3. `tutor restart` stops every board in turn, so the name's holder is briefly
     down -- and a board coming up is allowed to claim a name that points at
     nothing. A deploy handed the address to whichever course the loop reached
     last.

None of the three is visible from the outside, and any one of them alone
reproduces the whole failure. So they are checked here, together, by what the
code does rather than by what it says it does.
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

# 9098 answers -- it is somebody's lesson -- so 9171 coming up must not take it.
brd.port_answers = lambda p: p == 9098
calls[:] = []
brd.ts_repoint(9171)
check("a board coming up does not take a name that points at a live board",
      not any(a[:1] == ("serve",) and "--bg" in a for a in calls))

# Nothing answers on the port the name points at: the course whose board that
# was has gone, and leaving the address pointing at a corpse helps nobody.
brd.port_answers = lambda p: False
calls[:] = []
brd.ts_repoint(9171)
check("but it does take one that points at nothing at all",
      any("--bg" in a for a in calls))

# And forced, when a person says which course they mean.
brd.port_answers = lambda p: p == 9098
calls[:] = []
brd.ts_repoint(9171, force=True)
check("and a forced claim takes it whatever is holding it",
      any("--bg" in a for a in calls))

# ---------------------------------------------------------------------------
# 3. What each caller is entitled to. `--if-free` asks; a bare serve forces; and
#    anything that runs WITHOUT a person present must ask.
# ---------------------------------------------------------------------------
board_src = open(os.path.join(ROOT, "bin", "board"), encoding="utf-8").read()
tutor_src = open(os.path.join(ROOT, "bin", "tutor"), encoding="utf-8").read()

check("`vpn serve --if-free` exists, and routes through the guard",
      '"--if-free" in args' in board_src and board_src.count('"--if-free" in args') >= 2)

link_body = tutor_src[tutor_src.index("def link("):]
link_body = link_body[:link_body.index("\n\n\n")]
check("the launcher's own claim asks first",
      '"vpn", "serve", "--if-free"' in link_body)
check("and never forces it, which is what moved somebody mid-proof",
      '"vpn", "serve")' not in link_body)

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
print("one address, one board, and nothing automatic moves it")
