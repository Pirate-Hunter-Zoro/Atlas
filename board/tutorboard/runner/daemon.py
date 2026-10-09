"""A session's agent record, and what is left of the per-workspace daemon.

`agent.json` in the session directory is the record (`agent_state` merges into
it); the runner (`runner/service.py`) writes it around every turn. No daemon
is started any more: turns run inside the board server, so `agent_start`
refuses and says so. `courses` is the walk over the workspaces on disk, and
`board` runs the board CLI in one of them.
"""

import json
import os
import re
import signal
import subprocess
import sys
import time

from tutorboard import atlas, choice, paths, processes
from tutorboard.agents import recipes
from tutorboard.course import repo as course_repo

TOOL = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
BOARD = os.path.join(TOOL, "bin", "board")
TUTOR = os.path.join(TOOL, "bin", "tutor")


def flag(args, name):
    """The value after `name` in `args`, or None."""
    for n, a in enumerate(args):
        if a == name and n + 1 < len(args):
            return args[n + 1]
    return None

def courses(cfg):
    """Whatever is on disk. No registry, so nothing to keep in step.

    `atlas.workspaces()` is the walk: a workspace per directory under a
    subject family (`subjects.DIRS`). Nothing anywhere lists the workspaces.

    `TUTORBOARD_COURSES` still beats everything, and it is not a nicety. It is
    how a test says "this tree, not this machine's", and until 7 September only
    the shell scripts had heard of it: `catch-up.sh` walked the directory it was
    pointed at, then handed the machine to `tutor restart --tutors`, which asked
    the configuration and found the real home. Running the test suite therefore
    bounced the board somebody was being taught on, and -- because a `HOME` the
    test HAD moved gave a different config and so a different derived port --
    left a second board for the same course answering on a port nobody knew
    about. One variable, one meaning, everywhere. It now means "the repository
    root" rather than "the directory the courses are siblings in", which is the
    same sentence about the new shape; `atlas.root()` reads it.
    """
    # `TUTORBOARD_COURSES` beats the configuration; `courses_dir` is what a
    # person set, and it is honoured when they set something real. A value left
    # over from the flat layout is dropped by `load_config` before it gets here
    # -- see the note there, which is where that belongs, because a stale value
    # should be wrong ONCE at load rather than at every use.
    base = os.environ.get("TUTORBOARD_COURSES") or cfg.get("courses_dir") \
        or atlas.root()
    out = []
    for w in atlas.workspaces(base):
        info = recipes.read_course(w["root"])
        info["root"] = w["root"]
        info["dir"] = w["dir"]
        info["id"] = w["id"]
        info["family"] = w["family"]
        out.append(info)
    return out


def pick(cands, query):
    """Match on the directory name or the declared course name, loosely."""
    if not query:
        return None
    q = re.sub(r"[^a-z0-9]", "", query.lower())
    exact = [c for c in cands if re.sub(r"[^a-z0-9]", "", c["dir"].lower()) == q]
    if exact:
        return exact[0]
    hits = [c for c in cands
            if q in re.sub(r"[^a-z0-9]", "", c["dir"].lower())
            or q in re.sub(r"[^a-z0-9]", "", (c.get("name") or "").lower())]
    if len(hits) == 1:
        return hits[0]
    if len(hits) > 1:
        print("'%s' matches more than one course:" % query, file=sys.stderr)
        for c in hits:
            print("  %s" % c["dir"], file=sys.stderr)
        sys.exit(1)
    print("no course matching '%s'. Try: tutor --list" % query, file=sys.stderr)
    sys.exit(1)

def board(root, *args):
    p = subprocess.run([sys.executable, BOARD] + list(args), cwd=root,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return p.returncode, p.stdout.decode("utf-8", "replace")

def agent_state(live, **kw):
    path = os.path.join(live, "agent.json")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            st = json.load(fh)
    except (OSError, ValueError):
        st = {}
    st.update(kw)
    st["last_seen"] = time.time()
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(st, fh, indent=2)
    os.replace(tmp, path)
    return st


def agent_record_at(live):
    """`<live>/agent.json` as a dict, or None."""
    try:
        with open(os.path.join(live, "agent.json"), "r", encoding="utf-8") as fh:
            got = json.load(fh)
    except (OSError, ValueError):
        return None
    return got if isinstance(got, dict) else None


def owed_message(live):
    """A message a turn took and never answered, or None: the other half of
    `loop.owe`. The runner answers it before anything new in the inbox, since
    the lines it came from are already marked read."""
    try:
        with open(os.path.join(live, "agent.json"), "r", encoding="utf-8") as fh:
            got = (json.load(fh) or {}).get("owed")
    except (OSError, ValueError):
        return None
    return got if isinstance(got, str) and got.strip() else None


def record_is_ours(live, pid=None):
    """Does `agent.json` still name this process as the daemon on it?

    `agent_state` is a read-modify-write on one file that several processes
    write -- this daemon, the launcher, `tutor restart`, the hub -- and merging
    is what makes that safe for a field somebody is adding. It is not safe for
    the LAST write a daemon makes, which is `state: "stopped"`: a bounce hands
    the workspace over, the successor comes up and records its own pid, and the
    process that was replaced then stamps `stopped` on the record of the one
    that replaced it. `supervise.tutor_verdict` reads `stopped` as "a person
    said no" and never revives it, so the cost is a board that serves perfectly
    with nothing reading it until somebody notices by hand.

    Only the exit write is guarded, and the test is deliberately generous: an
    unreadable record, and a record whose pid a start has not filled in yet, are
    both answered yes. The successor writes its real pid within seconds of
    forking, which is the window this closes -- the narrow one where two daemons
    are alive and only one of them owns the file.
    """
    pid = os.getpid() if pid is None else pid
    try:
        with open(os.path.join(live, "agent.json"), "r", encoding="utf-8") as fh:
            got = (json.load(fh) or {}).get("pid")
    except (OSError, ValueError):
        return True
    return not got or got == pid


def mark_waking(live, agent_name, pid=None):
    """Record that a tutor is on its way up, before anything slow is attempted.

    Written by both halves of a start -- the launcher that decides, and the
    daemon that then spends several seconds bringing a link, a board and a
    sitting up before it can listen. Either is enough on its own, which matters
    because a person can start a daemon directly and never go through the other.

    IT CLEARS THE TWO FLAGS THAT SAY A DAEMON IS OWED. `restarting` says a
    bounce is unfinished and `handover` says the machine went, and both are
    answered by a daemon arriving -- this one. `agent_state` merges, so a flag
    nothing clears survives every later write, and a record still carrying
    `handover` while it listens makes the NEXT stop of it read as a machine
    going away: `supervise.tutor_verdict` returns `revive` and the watchdog
    starts the workspace's configured assistant over whoever was deliberately
    put there. A start is the only thing that has earned the right to clear
    either, and it is the one place every path up goes through.

    IT LEAVES `last_error` AND `failed_at` ALONE WHERE THE FAILURE BELONGS TO THE
    AGENT COMING UP, and that is the whole of what the board has to show for a
    turn that wrote no card. A daemon is most often restarted BECAUSE the last
    turn fell over, so clearing the reason here erases it at the one moment
    somebody is looking for it: the iPad then reads `listening`, no error, no
    card, which is the tutor claiming to be fine about work it never did. What
    retires a failure is something NEWER -- a turn that GOES THROUGH clears it on
    its success, and `lesson.state._failure` drops it the moment a card is
    written past it. A start is not newer than anything.

    AND IT CLEARS THE CLOCKS THE DAEMON BEFORE THIS ONE LEFT BEHIND. `agent_state`
    merges, so `stopped_at`, `turn_started` and `turn_signal` from a process that
    is gone sit in the same record as this one's `started` and are read as
    though they were this one's -- the board draws how long a turn has been
    running off `turn_started`, and a record carrying 17:40:07 beside a daemon
    that came up at 20:16 draws a turn that has been going for two and a half
    hours. A start is the one moment that has earned the right to clear them,
    because it is the one moment they are certainly about somebody else.

    AND A FAILURE IS DROPPED WHEN THE AGENT CHANGES, because the strip names the
    agent on the record and would otherwise paint the new one with the old one's
    fault: "claude's last turn failed -- cannot reach api.deepseek.com", about a
    host claude never opens. `failed_agent` is stamped beside the error for
    exactly this comparison. A provider swap is the common case here -- it is
    what a climb-down IS -- so the error is kept only where it is still about
    whoever is about to teach.

    AND IT CLEARS THE CODE STAMP. The daemon coming up writes its own when it
    listens; a waking record that kept the last one's would read as current to
    `ship_beat` for a process that has not loaded anything yet.
    """
    try:
        return agent_state(live, agent=agent_name, pid=pid, state="waking",
                           waking_at=time.time(), restarting=False,
                           handover=None, host=recipes.this_host(), code=None,
                           stopped_at=0, turn_started=0, turn_signal="",
                           turn_repairs=[],
                           **not_this_agents_failure(live, agent_name))
    except OSError:
        return None


def not_this_agents_failure(live, agent_name):
    """The fields that drop a failure belonging to somebody else, or `{}`.

    Written wherever the agent ON the record changes -- a start, and a
    climb-down between turns -- because the board reads the agent and the
    failure out of the same record and puts them in one sentence. A failure that
    outlives the provider it happened to is then a sentence about the wrong
    provider, which is a new way to mislead rather than the honest history the
    retention is for.
    """
    try:
        with open(os.path.join(live, "agent.json"), "r", encoding="utf-8") as fh:
            was = json.load(fh) or {}
    except (OSError, ValueError):
        return {}
    if not was.get("last_error"):
        return {}
    whose = was.get("failed_agent") or was.get("agent")
    if whose == agent_name:
        return {}
    return {"last_error": None, "failed_at": 0, "failed_agent": None}

def agent_record(root):
    """What `live/agent.json` says, believed or not."""
    try:
        with open(course_repo.session_path(root, "agent.json"), "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def agent_live(root):
    """The daemon recorded for this course, if it is really there.

    A pid on a shared filesystem proves nothing -- the record may have been
    written by a node whose allocation has since ended -- so the host is checked
    before the pid is believed.
    """
    st = agent_record(root)
    return st if processes.agent_is_attached(st, recipes.this_host()) else None


# NOTHING IS STARTED. Every turn runs inside the board server (`board/serve.py`,
# the `tutor-board` LaunchAgent), queued by the session it is for.
NO_DAEMON = ("there is no tutor daemon to start: turns run inside the board "
             "server (board/serve.py, LaunchAgent tutor-board), one per message")


def agent_start(cfg, course, agent_name, session=None):
    """Refused: see NO_DAEMON. `(1, why)`."""
    return 1, NO_DAEMON


def handed_off(cfg, course, agent_name):
    """Spawn the detached waiter that completes a restart the foreground gave up
    on, and say in one clause what was arranged. See `finish_restart`.

    Detached, not a thread: `cmd_restart` is a CLI that exits, and a thread goes
    with it. Output to the course's own `agent.log`, because that is where the
    next person looking at this tutor will already be.
    """
    live_dir = course_repo.session_dir(course["root"])
    cmd = [sys.executable, TUTOR, "finish-restart",
           course["dir"]]
    if agent_name:
        cmd += ["--agent", agent_name]
    try:
        out = open(os.path.join(live_dir, "agent.log"), "a", buffering=1)
    except OSError:
        out = subprocess.DEVNULL
    kw = {"cwd": course["root"], "stdout": out, "stderr": subprocess.STDOUT,
          "stdin": subprocess.DEVNULL}
    if hasattr(os, "setsid"):
        kw["preexec_fn"] = os.setsid
    try:
        subprocess.Popen(cmd, **kw)
    except OSError as exc:
        return ("nothing is waiting for it -- %s -- so the watchdog is what "
                "brings it back" % exc)
    return "it comes back on its own the moment that turn ends"


def agent_stop(course, wait=False):
    """Ask the daemon to finish. It writes the handoff on its way out.

    SIGTERM rather than a kill, because the whole point of the wrap-up turn is
    that it happens. It can take a minute; nothing here waits for it unless
    asked, since the caller is usually a person switching course.
    """
    st = agent_live(course["root"])
    if not st:
        return 0, "nothing was listening in %s" % course["dir"]
    # A record written by the launcher before the fork has no pid yet. There is
    # nothing to signal; the daemon it is waiting for will find the record gone.
    if not st.get("pid"):
        try:
            os.remove(course_repo.session_path(course["root"], "agent.json"))
        except OSError:
            pass
        return 0, "the start in %s was called off" % course["dir"]
    try:
        os.kill(st["pid"], signal.SIGTERM)
    except (OSError, TypeError, ValueError) as exc:
        return 1, str(exc)
    if wait:
        for _ in range(120):
            if not agent_live(course["root"]):
                break
            time.sleep(1)
    return 0, "%s in %s is wrapping up" % (st.get("agent"), course["dir"])

# What "you were working here" looks like on disk. Several signals, because no
# single one survives everything:
#
#   .board.json  a board is running, or was killed without being stopped --
#                but `board stop` DELETES it, so a cleanly stopped course has
#                none at all;
#   state.json   the session: course, chapter, kind. Written by `board open`
#                and updated through the sitting, and never removed;
#   turns.jsonl  the student's own contributions, appended as they answer;
#   cards        the tutor's, written as it teaches.
#
# Taking the newest of these was the fix for a real mistake: the first version
# looked only at `.board.json`, so stopping the board you were using made that
# course invisible and the next login resumed a DIFFERENT one -- quietly, since
# a login hook runs with --quiet, and the tailnet name moved with it.
LIVE_SIGNS = (".board.json", "state.json", "turns.jsonl", "cards")


def last_used(root):
    """When this course was last worked in, as far as disk can say. 0 if never."""
    best = 0
    for rel in LIVE_SIGNS:
        try:
            best = max(best, os.path.getmtime(course_repo.session_path(root, rel)))
        except OSError:
            continue
    return best


def remember_course(course):
    """Note that a PERSON chose this course, and when.

    Not a registry: courses are still whatever directories are sitting there.
    This records a *decision*, which is a different thing and cannot be derived
    from the filesystem -- because resuming a course touches its files too, so
    "most recently used" is self-reinforcing. A hook that resumed the wrong
    course once would go on resuming it for ever, quietly, taking the tailnet
    name with it every time. Naming one is how you say otherwise.
    """
    choice.remember_chosen(course["dir"], course["root"],
                           family=course.get("family") or "")


def chosen_course(cfg):
    """(when, course) for the last course a person named, if it still exists."""
    rec = choice.chosen_course()
    if not rec:
        return None
    for c in courses(cfg):
        if paths.same_dir(c["root"], rec.get("root")) or c["dir"] == rec.get("dir"):
            return (rec.get("at") or 0, c)
    return None                   # named once, since deleted or renamed


def last_board(cfg):
    """The course to bring back.

    Two signals, and the newer one wins: when a person last named a course, and
    when a course was last worked in. Neither alone is enough -- a name given a
    week ago should not beat an afternoon spent in another course, and file times
    alone cannot tell a course you chose from one a login hook happened to
    start.
    """
    best = chosen_course(cfg)
    for c in courses(cfg):
        when = last_used(c["root"])
        if when and (not best or when > best[0]):
            best = (when, c)
    return best[1] if best else None


def address_course(cfg, here):
    """Which of the boards up here the one HTTPS name is for. None if none is.

    The person's own word and nothing blended into it, which is why this is not
    `last_board`. That answers a different question -- which course to pick back
    up -- and answers it partly from file times, which is right there and wrong
    here: a tutor writes cards and transcript pushes into its own course every
    few minutes, so "most recently used" is a vote the busiest course always
    wins, and the address walks off to it while somebody is reading a different
    one on the iPad. One device, one URL, no way from it to say which course was
    meant; so the only thing that may say is `chosen.json`, which is a decision.

    `here` is the boards answering on this node. None means this node has
    nothing the person asked for -- nobody has ever chosen, or the chosen
    course's board is somewhere else -- and a caller that carries on anyway is
    guessing and must behave like it.
    """
    best = chosen_course(cfg)
    if not best:
        return None
    for c in here:
        if paths.same_dir(c["root"], best[1]["root"]):
            return c
    return None


def board_record(root):
    try:
        with open(course_repo.session_path(root, ".board.json"), "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None
