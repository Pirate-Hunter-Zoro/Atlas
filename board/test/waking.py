"""A tutor coming up says so, and nothing handed in is ever answered by silence.

Three reports, one evening, from an iPad in the middle of a Galois proof:

  "The tutor was sluggish to start up... But the tutor was just marked as dead
   or not available or not listening in the app. If the tutor is 'waking' up, I
   should be told that. It seemed to tell me the tutor was dead which put me in
   'send again' mode leading to massive confusion."

  "The tutor also appears to be very non responsive. Now it's just hanging. I
   need you to make the tutor way more robust. I don't ever want to be left
   hanging."

Both are the same defect wearing two faces: the board had words for exactly two
states -- attached and dead -- and a start takes seconds while a failed turn
takes none, so everything in between was reported as one of those two, wrongly.

What this asserts is the vocabulary and the plumbing behind it, on the server
side, where the truth is. `test/hanging.js` asserts that the board says it.
"""

import json
import os
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tutorboard import processes                                # noqa: E402
from tutorboard.lesson import notes, slate, state               # noqa: E402

fails = []


def check(label, cond):
    print(("ok   " if cond else "FAIL ") + label)
    if not cond:
        fails.append(label)


class Repo(object):
    """Just enough of a repository for the readers under test."""

    def __init__(self, root):
        self.root = root
        self.live = os.path.join(root, "live")
        self.slate = os.path.join(self.live, "slate")
        self.inbox = os.path.join(self.live, "inbox")
        self.messages_path = os.path.join(self.inbox, "messages.jsonl")
        # A failure stops being news when something NEWER lands on the board, so
        # the reader under test has to be able to see the cards and the answers.
        self.cards = os.path.join(self.live, "cards")
        self.turns_path = os.path.join(self.live, "turns.jsonl")
        for d in (self.live, self.slate, self.inbox, self.cards):
            os.makedirs(d, exist_ok=True)

    def agent(self, **kw):
        with open(os.path.join(self.live, "agent.json"), "w", encoding="utf-8") as fh:
            json.dump(kw, fh)


HERE = processes  # readability below

# --------------------------------------------------------------- waking up
print("-- a tutor on its way up is not a tutor that died --")

box = tempfile.mkdtemp(prefix="waking-")
repo = Repo(box)
host = __import__("tutorboard.machine", fromlist=["x"]).node_name()

# What the launcher writes BEFORE it forks: no pid, because there is no process
# yet. This is the whole of the gap the board used to fill with "tutor stopped".
repo.agent(host=host, agent="claude", pid=None, state="waking",
           waking_at=time.time())
got = state.load_agent(repo)
check("a start with no pid yet is reported, not judged",
      got is not None and got.get("state") == "waking")
check("and it counts as attached, so nothing says the board is unread",
      processes.agent_is_attached({"host": host, "state": "waking",
                                   "waking_at": time.time()}, host))

# Once the daemon has rewritten the record with its own pid, a start that DIED
# is knowable at once rather than having to wait out the grace -- a board that
# goes on promising a tutor for five minutes is its own kind of lie.
check("and once there is a pid, a start that died is noticed immediately",
      not processes.agent_is_attached(
          {"host": host, "state": "waking", "waking_at": time.time(),
           "pid": 999999}, host))
check("while the daemon that is really there is believed",
      processes.agent_is_attached(
          {"host": host, "state": "waking", "waking_at": time.time(),
           "pid": os.getpid()}, host))

# It expires. A start that fell over must not go on claiming to be in progress.
repo.agent(host=host, agent="claude", pid=None, state="waking",
           waking_at=time.time() - processes.WAKING_GRACE - 5)
got = state.load_agent(repo)
check("a start that never landed stops claiming to be in progress",
      got is not None and got.get("state") == "stale")

# And a record from another node is still not ours, waking or otherwise: the
# home directory is shared and a pid from a finished allocation is a stranger's.
repo.agent(host="some-other-node", agent="claude", pid=None, state="waking",
           waking_at=time.time())
check("a start on another machine is not this board's tutor",
      not processes.agent_is_attached(
          {"host": "some-other-node", "state": "waking",
           "waking_at": time.time()}, host))

# ------------------------------------------------- a turn that fell over
print()
print("-- a failed turn reaches the person whose work it was --")

repo.agent(host=host, agent="claude", pid=os.getpid(), state="listening",
           last_error="timed out", failed_at=time.time())
got = state.load_agent(repo)
check("a turn that failed is handed to the board, not only to the log",
      got and got.get("failure") and got["failure"]["error"] == "timed out")

repo.agent(host=host, agent="claude", pid=os.getpid(), state="listening",
           last_error="timed out",
           failed_at=time.time() - state.FAILURE_FRESH - 10)
got = state.load_agent(repo)
check("and a failure from yesterday is history rather than news",
      got and not got.get("failure"))

# A FAILURE ENDS WHEN SOMETHING NEWER HAPPENS, NOT WHEN A CLOCK SAYS SO.
#
# This expired at fifteen minutes, and fifteen minutes is nothing to a turn that
# was asked to write code: one timed out after twenty, having left an opening
# sentence on the board saying "running the four typists on the pilot session's
# real audio". Five minutes later the board stopped mentioning the failure at
# all -- so what was there was a present-tense card about work that had stopped,
# a tutor listening, and nothing anywhere saying so.
failed_at = time.time() - 3000
repo.agent(host=host, agent="claude", pid=os.getpid(), state="listening",
           last_error="timed out", failed_at=failed_at)
old_card = os.path.join(repo.cards, "0001-opening.md")
with open(old_card, "w", encoding="utf-8") as fh:
    fh.write("---\nkind: lesson\n---\nAbout to run the four typists.\n")
os.utime(old_card, (failed_at - 600, failed_at - 600))
got = state.load_agent(repo)
check("a failure with nothing newer than it is still the news, an hour on",
      got and got.get("failure") and got["failure"]["error"] == "timed out")

# ...and the thing that actually ends it is a card, because a card newer than
# the failure IS the turn that succeeded.
with open(os.path.join(repo.cards, "0002-report.md"), "w", encoding="utf-8") as fh:
    fh.write("---\nkind: lesson\n---\nDone: four typists run.\n")
got = state.load_agent(repo)
check("and a card written since clears it, because that is the success",
      got and not got.get("failure"))
for name in ("0001-opening.md", "0002-report.md"):
    try:
        os.remove(os.path.join(repo.cards, name))
    except OSError:
        pass

repo.agent(host=host, agent="claude", pid=os.getpid(), state="listening",
           last_error=None, failed_at=0)
got = state.load_agent(repo)
check("a turn that then succeeded clears it",
      got and not got.get("failure"))

# ------------------------------------------- work nobody has picked up
print()
print("-- and the board can always say whether anything took it --")

check("an empty inbox is nothing waiting", notes.waiting(repo) is None)

with open(repo.messages_path, "w", encoding="utf-8") as fh:
    fh.write(json.dumps({"t": time.time() - 90, "text": "[slate] t0001 rev 1",
                         "read": True}) + "\n")
check("and so is an inbox the tutor has read", notes.waiting(repo) is None)

sent_at = time.time() - 120
with open(repo.messages_path, "a", encoding="utf-8") as fh:
    fh.write(json.dumps({"t": sent_at, "text": "[slate] t0002 rev 1",
                         "read": False}) + "\n")
    fh.write(json.dumps({"t": time.time() - 30, "text": "[slate] t0003 rev 1",
                         "read": False}) + "\n")
w = notes.waiting(repo)
check("two things handed in and nothing taken is reported as two",
      w and w["count"] == 2)
check("timed from the OLDEST, which is the one somebody has been waiting on",
      w and abs(w["since"] - sent_at) < 1)

# The point of it being on disk: a reload cannot lose it, and neither can the
# tutor being restarted underneath it. Nothing in the browser is consulted.
check("and it is read off disk, so a reload still knows",
      notes.waiting(Repo(box)) is not None)

# -------------------------------------------- a page is its number
print()
print("-- a slate page is named by its number, never by its position --")

# The exact shape of the Galois directory: page 1 was never saved, and neither
# were 6, 8 or 10. Read as a dense array, index 4 is `page-07` -- and the next
# stroke on it was written to `page-05`.
for n in (2, 3, 4, 5, 7, 9, 11, 12):
    with open(os.path.join(repo.slate, "page-%02d.json" % n), "w",
              encoding="utf-8") as fh:
        json.dump({"page": n, "w": 1130, "h": 1514,
                   "strokes": [{"c": "#eee", "w": 3, "pts": [[n, n], [n * 2, n * 2]]}]},
                  fh)
pages = slate.read_slate_pages(repo)
check("every page carries the number it is saved under",
      [p["page"] for p in pages] == [2, 3, 4, 5, 7, 9, 11, 12])
check("and a gap is a gap rather than a page sliding down into it",
      pages[4]["page"] == 7)

# A field inside the file that disagrees with the filename loses: the field was
# written by whichever client saved it, and a client that had already slid is a
# client whose field is wrong too. The filename is what the next save addresses.
with open(os.path.join(repo.slate, "page-04.json"), "w", encoding="utf-8") as fh:
    json.dump({"page": 99, "w": 1130, "h": 1514, "strokes": []}, fh)
pages = slate.read_slate_pages(repo)
check("the filename wins over a number written inside the file",
      [p["page"] for p in pages] == [2, 3, 4, 5, 7, 9, 11, 12])

# Three figures. `%02d` means `page-100` sorts BEFORE `page-99` by name, so a
# sitting that ran past a hundred pages came back with its last hundred first.
for n in (99, 100, 101):
    with open(os.path.join(repo.slate, "page-%02d.json" % n), "w",
              encoding="utf-8") as fh:
        json.dump({"page": n, "w": 1130, "h": 1514, "strokes": []}, fh)
pages = slate.read_slate_pages(repo)
check("and past a hundred pages the order is still the order",
      [p["page"] for p in pages][-3:] == [99, 100, 101])

# ------------------------------------------------- the launcher's own order
print()
print("-- and the launcher says so before it does anything slow --")

src = open(os.path.join(ROOT, "bin", "tutor"), encoding="utf-8").read()
i = src.index("def agent_start(")
start = src[i:src.index("def agent_stop(", i)]
check("`agent_start` marks the course waking", "mark_waking(" in start)
check("and it does so before it forks anything",
      start.index("mark_waking(") < start.index("subprocess.Popen"))
check("and the catch-up no longer happens inside the request that asked",
      "sync(root, quiet=True)" not in start)

j = src.index("def headless(")
head = src[j:j + 4000]
check("the daemon marks itself waking too, for a start nobody routed",
      "mark_waking(" in head)
check("before the link, the board and the sitting, which are the slow part",
      head.index("mark_waking(") < head.index('board(root, "start")'))
check("and the catch-up moved here, where nobody is holding a request open",
      "sync(root, quiet=True)" in head)

# The other half of never hanging: work handed in with nothing reading the board
# starts a tutor. It used to go into the inbox and stay there for ever, because
# `board wait` only ever returns to a daemon that is already running.
for mod in ("writing", "lesson"):
    routes = open(os.path.join(ROOT, "tutorboard", "server", "routes",
                               mod + ".py"), encoding="utf-8").read()
    check("handing work in through %s.py wakes a tutor" % mod,
          "spawn.wake_tutor(repo)" in routes)

# --------------------------------- a transcript never commits its own loss
print()
print("-- and a beat never commits the disappearance of somebody's working --")

# Two clones run `sync_transcript` on a beat over the same course, and `git add
# -A live` commits a SNAPSHOT of whichever working tree it is standing in.
# Neither machine has the other's newest pages, so each snapshot DELETES the
# other's, and the next fast-forward pull checks it out and removes the files
# from disk. Measured on Galois Theory: `live/slate/` pages 50 to 53, written
# between 10:13 and 10:25, present in one line of history and physically absent
# from the working tree by 11:09.
import subprocess                                              # noqa: E402

TUTOR = os.path.join(ROOT, "bin", "tutor")
git_ok = subprocess.run(["git", "--version"], stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL).returncode == 0

if not git_ok:
    print("skip  git is not available")
else:
    work = tempfile.mkdtemp(prefix="transcript-")

    def g(*args):
        return subprocess.run(["git"] + list(args), cwd=work,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              timeout=60)

    g("init", "-q", "-b", "main")
    g("config", "user.email", "t@t")
    g("config", "user.name", "t")
    for d in ("live/slate", "live/answers", "live/cards", "live/archive"):
        os.makedirs(os.path.join(work, d), exist_ok=True)
    for n in (1, 2, 3):
        open(os.path.join(work, "live/slate/page-%02d.json" % n), "w").write("{}")
    open(os.path.join(work, "live/answers/t0001-r1.json"), "w").write("{}")
    open(os.path.join(work, "live/cards/0001-first.md"), "w").write("card")
    g("add", "-A")
    g("commit", "-q", "-m", "a lesson")

    # What the other machine's snapshot does: two pages and an answer vanish
    # from the working tree, having never been deleted by anything here.
    for rel in ("live/slate/page-02.json", "live/slate/page-03.json",
                "live/answers/t0001-r1.json"):
        os.remove(os.path.join(work, rel))
    # And one that IS accounted for: filed away by `board archive`, which
    # renames it under `live/archive/`.
    os.makedirs(os.path.join(work, "live/archive/2026-09-03"), exist_ok=True)
    os.rename(os.path.join(work, "live/cards/0001-first.md"),
              os.path.join(work, "live/archive/2026-09-03/0001-first.md"))

    # The real function, lifted out of `bin/tutor` -- which has no `.py` on the
    # end of it and cannot be imported. Just the transcript block: importing the
    # whole launcher would run its argument parsing.
    ns = {"os": os, "subprocess": subprocess}
    tutor_src = open(TUTOR, encoding="utf-8").read()
    i = tutor_src.index("TRANSCRIPT_DIRS = (")
    j = tutor_src.index("def sync_transcript(")
    exec(compile(tutor_src[i:j], "<tutor>", "exec"), ns)

    def gg(*args, **kw):
        return subprocess.run(["git"] + list(args), cwd=work,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              timeout=kw.get("timeout", 60))

    said = []
    gg("add", "-A", "live")
    put = ns["keep_transcript_files"](work, gg, said.append)

    check("a slate page that vanished with nothing to account for is put back",
          os.path.isfile(os.path.join(work, "live/slate/page-02.json"))
          and os.path.isfile(os.path.join(work, "live/slate/page-03.json")))
    check("and so is a frozen answer, which is the copy that cannot be redrawn",
          os.path.isfile(os.path.join(work, "live/answers/t0001-r1.json")))
    check("on disk as well as in the index, so the board can read it again",
          gg("diff", "--cached", "--name-only", "--diff-filter=D", "--",
             "live/slate").stdout.decode().strip() == "")
    check("a card that `board archive` filed away is a deletion that IS "
          "accounted for, and stays deleted",
          not os.path.isfile(os.path.join(work, "live/cards/0001-first.md")))
    check("and the beat says what it put back rather than doing it silently",
          any("put back" in s for s in said))
    check("with nothing missing, it does nothing at all",
          ns["keep_transcript_files"](work, gg, said.append) == [])

    # AND THE PULL, WHICH IS THE HALF THAT ACTUALLY DELETES. A fast-forward
    # checks the other machine's snapshot out and removes files from disk, and
    # by then HEAD no longer holds them -- so the commit-side guard has nothing
    # to restore from. This is the only moment that knows.
    gg("commit", "-q", "-m", "put back")
    ours = gg("rev-parse", "HEAD").stdout.decode().strip()

    # The other machine's snapshot: it never saw page 3, and it filed a card.
    gg("checkout", "-q", "-b", "theirs")
    os.remove(os.path.join(work, "live/slate/page-03.json"))
    os.remove(os.path.join(work, "live/answers/t0001-r1.json"))
    os.makedirs(os.path.join(work, "live/archive/2026-09-04"), exist_ok=True)
    open(os.path.join(work, "live/archive/2026-09-04/0002-second.md"), "w").write("x")
    open(os.path.join(work, "live/slate/page-04.json"), "w").write("{}")
    gg("add", "-A")
    gg("commit", "-q", "-m", "their snapshot")
    theirs = gg("rev-parse", "HEAD").stdout.decode().strip()
    # What a fast-forward onto it looks like from here.
    gg("checkout", "-q", theirs)

    # And a deletion paired with an addition of the SAME BYTES must still read
    # as a deletion. Slate pages are routinely byte-identical -- a page cut as a
    # copy of another, an attempt handed in twice -- and git reports that pair as
    # a rename, which is not a deletion, so the files this exists to protect are
    # exactly the ones that would hide behind rename detection.
    said2 = []
    put2 = ns["keep_pulled_files"](work, gg, said2.append, ours)

    check("a pull that removed a slate page puts it back on disk",
          os.path.isfile(os.path.join(work, "live/slate/page-03.json")))
    check("and the frozen answer it removed with it",
          os.path.isfile(os.path.join(work, "live/answers/t0001-r1.json")))
    check("while what the pull BROUGHT is kept, because that is the point of it",
          os.path.isfile(os.path.join(work, "live/slate/page-04.json")))
    check("and the beat says what it saved",
          any("would have removed" in s for s in said2))
    check("a pull that took nothing away does nothing",
          ns["keep_pulled_files"](work, gg, said2.append, theirs) == [])

# ---------------------------------------------------------------------------
# AN ABANDONED BOUNCE IS NOT A PERSON SAYING NO
# ---------------------------------------------------------------------------
#
# The third face of the same defect, and the one that cost fifteen hours rather
# than a minute. From the iPad: "I'm in Galois Theory and it says the tutor is
# down, though the app is working."
#
# `restarting` is the field that says somebody asked for this daemon BACK. Only
# the asker can write it -- `tutor restart --tutors`, before it signals -- and
# the daemon receiving a SIGTERM cannot tell a bounce from a person leaving. So
# the daemon's exit record must not touch it. It used to write `restarting:
# False`, which turned every restart nobody finished into a record identical to
# `tutor agent stop`, and `tutor_verdict` reads that as "a person said no" and
# never revives it. Measured: a handoff turn took 97 seconds, `cmd_restart`
# gives it 90, so it returned without starting anything -- and three generations
# of the serving chain then revived that course's board and refused its tutor.
#
# `supervise.tutor_verdict` is read here, not changed: this asserts the contract
# between the record the daemon leaves and the watchdog that reads it.
from tutorboard import supervise                                # noqa: E402

HOST = "compute304"
NOW = 1000000.0
GRACE = 180

# What the daemon's own exit leaves, after a bounce asked for it. The asker
# wrote `restarting` and a `stopped_at`; the exit merges `state: stopped` over
# the top and says nothing about why.
bounced = {"host": HOST, "pid": 4321, "state": "stopped", "restarting": True,
           "stopped_at": NOW - 5}
check("a bounce that has just signalled reads as reattaching, not as a death",
      supervise.tutor_verdict(bounced, HOST, False, now=NOW) == "reattaching")

abandoned = dict(bounced, stopped_at=NOW - (GRACE + 60))
check("and a bounce nobody finished is REVIVED once the grace is out, which is "
      "the whole reason the flag is written before the signal",
      supervise.tutor_verdict(abandoned, HOST, False, now=NOW) == "revive")

# And the other half of the contract, which must not have moved: a person who
# says stop is obeyed, for ever. Reviving that is the watchdog arguing with its
# owner.
asked = {"host": HOST, "pid": 4321, "state": "stopped", "restarting": False,
         "stopped_at": NOW - (GRACE + 60)}
check("while a person's own stop is still obeyed and never revived",
      supervise.tutor_verdict(asked, HOST, False, now=NOW) == "stopped")

# AND THE DAEMON'S EXIT LEAVES THE FLAG ALONE. The two halves above can only
# stay true if nothing on the way out overwrites the asker's note, and that line
# lives in `bin/tutor`, which has no `.py` on the end and cannot be imported.
# Read as source, because a drift here is silent and costs a whole evening.
src = open(TUTOR, encoding="utf-8").read()
exit_line = [l for l in src.splitlines()
             if 'agent_state(live, state="stopped"' in l]
check("the daemon writes exactly one exit record", len(exit_line) == 1)
check("and it does not claim to know whether a restart was asked for",
      bool(exit_line) and "restarting" not in exit_line[0])

# AND A RESTART DOES NOT WALK AWAY FROM A RESTART IT STARTED.
#
# The foreground waits ninety seconds for the wrap-up turn to write HANDOFF.md
# and the record to clear. A handoff turn is a model call and routinely outruns
# that — 97 seconds, measured, in the sitting this whole flag was written for.
# The branch that gave up returned with `restarting: True` on the record and
# NOTHING pending, so the board said "claude is restarting" until somebody else
# noticed. Somebody else was the watchdog above, at the grace — which is the
# right backstop and is not a plan: it only exists where a watch loop runs, so a
# hand restart in an `salloc` left the tutor down with no clock anywhere, and
# where it does run the person watching still waits out the grace.
#
# Reported: "Suddenly it says 'claude is restarting' - and I don't foresee that
# finishing... what the hell happened?"
gave_up = src[src.index("        if not gone:"):]
gave_up = gave_up[:gave_up.index("\n        code, msg = agent_start(")]
check("the branch that gives up waiting arranges the finish itself",
      "handed_off(" in gave_up)
check("and it is a DETACHED process, because the restart is a CLI that exits "
      "and a thread goes with it",
      "def handed_off(" in src and "start_new_session=True" in src
      or ("def handed_off(" in src and "os.setsid" in src))
finish = src[src.index("def finish_restart("):]
finish = finish[:finish.index("\ndef ", 1)]
check("the waiter starts the replacement the moment the turn ends, rather than "
      "at a fixed grace",
      "if not agent_live(" in finish and "agent_start(" in finish)
check("and it waits far past anything measured before handing back to the "
      "watchdog, rather than giving up at the number that caused this",
      "FINISH_WAIT" in finish and int(
          src.split("FINISH_WAIT = ")[1].split("\n")[0]) >= 600)
# The watchdog is left exactly as it is, so for a while BOTH may decide to start
# this tutor. That is not a race, and the reason is one property of `agent_start`
# rather than any coordination between them: it refuses when one is already
# there. If that ever stops being true, two daemons answer one inbox.
starter = src[src.index("def agent_start("):]
starter = starter[:starter.index("\ndef ", 1)]
check("and a second start is refused rather than spawning a second daemon, "
      "which is the whole of why the waiter and the watchdog cannot collide",
      "already listening in" in starter and "already waking up in" in starter)

print()
print(("%d FAILURES" % len(fails)) if fails
      else "a tutor says when it is waking, and silence is never the answer")
sys.exit(1 if fails else 0)
