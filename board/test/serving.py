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

  4. And the guard against 1-3 read "is anything answering on that port" as
     "is that board somebody's lesson". A board an ended generation left behind
     answers exactly like a live one, so it held the address against every board
     that came after it -- for as long as the process lived. Measured: a Galois
     Theory board from a dead generation kept `https://compute-node…/` on 9098
     for an hour and three quarters while the live one served 9195. The tutor
     was up, the board was up, the chain was on generation 3 and reporting
     itself healthy, and the reply the tutor had written was on a board nothing
     pointed at. "If claude is working, and the tutoring server is up, how could
     we ever be left hanging?"

None of the four is visible from the outside, and any one of them alone
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
tutor_src = open(os.path.join(ROOT, "bin", "tutor"), encoding="utf-8").read()

check("`vpn serve --if-free` exists, and routes through the guard",
      '"--if-free" in args' in board_src and board_src.count('"--if-free" in args') >= 2)

link_body = tutor_src[tutor_src.index("def link("):]
link_body = link_body[:link_body.index("\n\n\n")]
check("the launcher's own claim asks first",
      '"vpn", "serve", "--if-free"' in link_body)
check("and never forces it, which is what moved somebody mid-proof",
      '"vpn", "serve")' not in link_body)

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
print("one address, one board, and nothing automatic moves it")
