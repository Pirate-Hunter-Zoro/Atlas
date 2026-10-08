"""Keeping this Mac's boards and tutors up, and on the tree's code.

`cmd_restart` bounces boards and tutors onto current code; `watch_once` is one
pass of the watchdog, repairing only what a person already asked for;
`ship_beat` puts this node's processes on the tree's stamp; `cmd_down` takes
the machine out of serving.
"""

import contextlib
import io
import json
import os
import signal
import sys
import time

from tutorboard import machine, missions, paths, processes, stamp, supervise
from tutorboard.agents import recipes
from tutorboard.net import tailscale
from tutorboard.runner import daemon
from tutorboard.course import repo as course_repo

# HOW LONG A RESTART WAITS FOR A BOUNCED DAEMON TO RECORD ITS OWN PID.
#
# `agent_start` writes `waking` with no pid and then forks; the pid arrives once
# the daemon has brought the link, the board and the sitting up, which is
# seconds. Bounded, because a restart is run by somebody watching a terminal and
# a command that waits for ever is a command nobody runs after a ship.
RESTART_WAIT = 20


# How long a detached waiter will sit on a wrap-up turn before giving up on it.
# The turn is a model call writing HANDOFF.md, and `agent_stop` allows it to take
# minutes; twenty is far past anything measured and is a bound rather than an
# expectation. What it must not be is ninety seconds, which is the number the
# foreground gives up at -- see `finish_restart`.
FINISH_WAIT = 1200


def finish_restart(cfg, args):
    """Wait out a wrap-up turn this machine already signalled, then start the
    replacement. Spawned detached by `cmd_restart`; nobody types this.

    A RESTART MUST NOT WALK AWAY FROM A RESTART IT STARTED. The foreground waits
    ninety seconds for the daemon's record to clear, and a handoff turn is a
    model call that routinely outruns that -- 97 seconds, measured. The branch
    that gave up wrote nothing further and returned, leaving `restarting: True`
    on the record with NOTHING pending: the board reads that flag and says
    "claude is restarting", truthfully, for as long as it takes somebody else to
    notice.

    Somebody else was `tutor watch`, at `REATTACH_GRACE` — 180 seconds. That is
    the right backstop and it is not a plan. It only exists where a watch loop is
    running, so a hand `tutor restart --tutors` on a machine with no watch
    loop left the tutor down with the flag on
    and no clock anywhere. And where it does exist, the person holding the iPad
    still watches a lesson say "restarting" for three minutes. Reported in those
    words: "Suddenly it says 'claude is restarting' - and I don't foresee that
    finishing... what the hell happened?"

    So the operation finishes itself, as soon as the turn it is waiting for
    actually ends rather than at a fixed grace. The watchdog stays exactly as it
    is: two things that may both start a tutor is not a race, because
    `agent_start` answers "already listening" and changes nothing.
    """
    plain = [a for a in args if not a.startswith("-")]
    found = daemon.courses(cfg)
    course = daemon.pick(found, plain[0]) if plain else None
    if not course:
        return 1
    # The record is the least reliable of the three by the time this runs -- the
    # whole job is to wait for it to disappear -- so configuration is the
    # fallback, which is the same answer `cmd_restart` resolves and the one that
    # should be running here anyway.
    name = (daemon.flag(args, "--agent")
            or (daemon.agent_live(course["root"]) or {}).get("agent")
            or recipes.resolve_agent(cfg, course))
    for _ in range(FINISH_WAIT):
        if not daemon.agent_live(course["root"]):
            code, msg = daemon.agent_start(cfg, course, name)
            return 0 if code == 0 else 1
        time.sleep(1.0)
    # Still wrapping up after twenty minutes. Leave the flag: it is true, and
    # the watchdog is the right owner of a case this far outside the measured
    # range. Saying so where a person will find it is the whole of what is left.
    print("finish-restart: %s was still wrapping up after %d s; leaving the "
          "restart flag for the watchdog" % (course["dir"], FINISH_WAIT))
    return 1


def cmd_restart(cfg, args, only=None):
    """Restart every long-lived process on this machine, on the current code.

    A board is a long-lived process that read `serve.py` when it started, so a
    change to this tool reaches a course only when its board comes back. That is
    invisible from the outside: the pages are served from disk and look new while
    the endpoints behind them are still the old ones, which is exactly the sort of
    difference somebody spends an evening not finding.

    Only boards that are actually answering on this node are touched -- a record
    on a shared filesystem may belong to another machine, and stopping a stranger's
    process is worse than leaving a stale one. That node's own watch restarts it
    (`ship_beat`). `--tutors` adds the daemons.

    `--stale` touches only a process whose recorded code stamp differs from the
    tree's, so a commit that changed no loaded code bounces nothing. `--wait`
    then waits for every other node's watch to report its boards and tutors on
    the new stamp, and says per process where it landed (`await_elsewhere`).
    `--since EPOCH` is when the ship began: another node's watch may restart a
    board before this command starts, and that is still this ship's restart.
    `only` is the watch beat's own entry: those boards and no others, under the
    lock the beat already holds.
    """
    host = recipes.this_host()
    stale = "--stale" in args
    wait_elsewhere = "--wait" in args
    tree = stamp.tree()
    if stale and tree is None:
        print("can't read the tree's stamp; restarting everything")
        stale = False
    started = time.time()
    try:
        started = min(started, float(daemon.flag(args, "--since") or started))
    except ValueError:
        pass
    # ONE RESTART OF THIS NODE'S BOARDS AT A TIME. A lesson save, a ship and
    # the watch's ship beat can all reach for the same board together; the
    # beat already holds this lock when it calls in with `only`.
    lock = (stamp.restart_lock(wait=True) if only is None
            else contextlib.nullcontext(True))
    with lock:
        # WHO HOLDS THE ADDRESS, BEFORE ANYTHING IS STOPPED.
        #
        # There is one HTTPS name and it points at one board. A start claims it only
        # when it is pointing at nothing -- but this loop stops each board in turn,
        # so while one is down the name it holds IS pointing at nothing, and the
        # next course to come up takes it. The alphabet decided which. Somebody
        # mid-proof in Galois Theory looked up at a board labelled PSYCH-ASR, on a
        # device with one URL baked into it, with no way to say which course they
        # meant. A deploy must not move somebody's address.
        #
        # The name points at ONE port, machine-wide, so it is asked once; which
        # course that is is then read off the board each one is actually running on,
        # because a port is a pure function of the workspace's directory basename
        # and the record in `live/.board.json` is the fact rather than a derivation
        # of it.
        all_courses = daemon.courses(cfg)
        held_port = None
        for c in all_courses:
            code, out = daemon.board(c["root"], "vpn", "holder")
            if code == 0 and out.strip().isdigit():
                held_port = int(out.strip())
            break
        held_before = None
        if held_port:
            for c in all_courses:
                try:
                    with open(course_repo.session_path(c["root"], ".board.json"),
                              "r", encoding="utf-8") as fh:
                        if json.load(fh).get("port") == held_port:
                            held_before = (c["dir"], c["root"], held_port)
                            break
                except (OSError, ValueError):
                    continue

        touched, skipped, elsewhere, current = [], [], [], []
        for c in all_courses:
            live = course_repo.session_dir(c["root"])
            try:
                with open(os.path.join(live, ".board.json"), "r", encoding="utf-8") as fh:
                    info = json.load(fh)
            except (OSError, ValueError):
                continue
            if only is not None and c["dir"] not in only:
                continue
            if info.get("node") and info["node"] != host:
                # Not this node's to stop. Its own watch restarts it, and `--wait`
                # is what says whether it did.
                elsewhere.append((c, info))
                continue
            if not processes.board_is_running(info.get("pid"), c["root"]):
                continue
            if stale and info.get("code") == tree:
                current.append(c["dir"])
                continue
            daemon.board(c["root"], "stop")
            code, out = daemon.board(c["root"], "start")
            if code == 0:
                touched.append(c["dir"])
            else:
                skipped.append("%s (%s)" % (c["dir"], last_line(out)))

        # And give it back. The board that had the name has just come up on the new
        # code; whatever the loop pointed the name at in the meantime, it goes back
        # to where it was. `vpn serve` is the forced claim, which is the right verb:
        # this is not a guess about which course is wanted, it is a restoration of
        # the one that was.
        if held_before:
            name, root, port = held_before
            code, out = daemon.board(root, "vpn", "holder")
            now = out.strip() if code == 0 else ""
            if now != str(port):
                daemon.board(root, "vpn", "serve")
                print("the address is back on %s" % name)

    label = tree or "the current code"
    if touched:
        print("restarted on %s: %s" % (label, ", ".join(touched)))
    if current:
        print("already on %s: %s" % (tree, ", ".join(current)))
    if not touched and not current:
        print("no boards were running on %s" % host)
    for s2 in skipped:
        print("  left alone: %s" % s2)
    if not wait_elsewhere:
        # "Its watch restarts it" only when that node's watch has written a
        # beat lately: a watch started before the ship beat existed never will.
        for c, info in elsewhere:
            ship = ship_record(info["node"]) or {}
            beating = time.time() - (ship.get("at") or 0) <= 3 * supervise.POLL
            print("  %s on %s: %s" % (
                c["dir"], info["node"],
                "already on %s" % tree if tree and info.get("code") == tree
                else "that node's watch restarts it on its next beat" if beating
                else "not restarted -- no watch there runs the ship beat; it "
                     "lands when that node's board next starts"))

    if "--tutors" not in args:
        return (await_elsewhere(cfg, elsewhere, tree, started)
                if wait_elsewhere else 0)

    # The daemons hold old code for exactly the same reason the boards do: this
    # file is read once, when the process starts. A tutor in the middle of a turn
    # is left alone -- bouncing it loses the card it is writing, and the student
    # is the one who pays for that.
    import signal as _sig
    bounced, coming, held, deferred = [], [], [], []
    # A tutor mid-turn is left alone here. With `--stale`, this node's own
    # watch bounces it after the turn if one runs the ship beat, so say that
    # rather than "left alone" for something that is then restarted.
    ship_here = ship_record(host)
    watched_here = bool(ship_here and time.time() - (ship_here.get("at") or 0)
                        <= 3 * supervise.POLL)
    for c in daemon.courses(cfg):
        st = daemon.agent_live(c["root"])
        if not st or st.get("mode") == "interactive":
            continue
        if stale and st.get("code") == tree:
            continue
        if st.get("state") == "working":
            if stale and watched_here:
                deferred.append("%s: mid-turn; this node's watch restarts it "
                                "after the turn" % c["dir"])
            else:
                held.append("%s (mid-turn%s)" % (
                    c["dir"], "; no watch here will restart it" if stale else ""))
            continue
        # What configuration says NOW, not what happened to be running. A restart
        # used to bring back whatever the record named, which meant changing
        # `default_agent` never reached a course whose tutor was restarted rather
        # than stopped -- the config said one thing and the board ran another, for
        # ever. This is the safe moment to act on it: the daemon is being stopped
        # anyway, and the SIGTERM below makes it write HANDOFF.md, which is
        # precisely the continuity a different tutor picks up from.
        was_name = st.get("agent")
        name = recipes.resolve_agent(cfg, c) or was_name
        # Say, on disk, that this is a RESTART and not a death. The board reads
        # this record to decide what to tell the person holding the iPad, and a
        # daemon being bounced looks from there exactly like one that died: the
        # chip goes to "no tutor attached" and the empty-board banner appears,
        # in the middle of a lesson, because a fix was shipped. Reported as
        # "No tutor attached. NOW the tutor just got attached, but this is
        # spotty". It is one word in the record and it turns a dead end into
        # "reattaching".
        daemon.agent_state(c["root"] + "/live", restarting=True, stopped_at=time.time())
        was = st.get("pid")
        if not was:
            # A record with no pid in it. It happens: a daemon killed with its
            # state directory underneath it leaves half a file, and `os.kill`
            # with None does not raise OSError -- it raises TypeError, which is
            # not caught here and took the whole restart down with it, every
            # course after this one included.
            held.append("%s (no pid in its record)" % c["dir"])
            continue
        try:
            os.kill(was, _sig.SIGTERM)
        except OSError:
            pass
        # The wrap-up turn a SIGTERM starts writes HANDOFF.md, and the next tutor
        # reads it -- so waiting for the record to clear is waiting for the
        # continuity to be written, not merely for a process to die. It is one
        # turn, and a turn can take minutes, so this does not wait for ever.
        gone = False
        for _ in range(90):
            if not daemon.agent_live(c["root"]):
                gone = True
                break
            time.sleep(1.0)
        if not gone:
            # `agent_start` answers "already listening" here and answers it with
            # a success code, which is how this came to report a restart it had
            # not performed. Say what actually happened.
            #
            # AND WHAT HAPPENS NEXT, because this is the one branch that leaves a
            # restart half-done. A handoff turn is a model call and routinely
            # outruns the ninety seconds above; the `restarting` flag written
            # before the signal stays on the record, and that is what the
            # watchdog picks the tutor back up from once `REATTACH_GRACE` is out.
            # Telling somebody to run it again was the only instruction while
            # the daemon's own exit erased the flag -- and nobody ever does.
            # AND THIS BRANCH NOW FINISHES ITSELF. See `finish_restart`: a
            # detached waiter sits on the wrap-up turn and starts the
            # replacement the moment it ends, so recovery does not depend on a
            # watch loop existing, and does not wait out a fixed grace where it
            # does. The watchdog stays as the backstop it was.
            clause = daemon.handed_off(cfg, c, name)
            held.append("%s (still writing its handoff; %s)"
                        % (c["dir"], clause))
            continue
        code, msg = daemon.agent_start(cfg, c, name)
        if code != 0:
            held.append("%s (%s)" % (c["dir"], msg.strip() or "did not come back"))
            continue
        # A RECORD WITH NO PID IN IT IS NOT A RESTART THAT DID NOT HAPPEN.
        #
        # This read the record once, immediately after the start -- and a start
        # writes `waking` with no pid BEFORE it forks, so the read found a
        # pidless record every time and reported every successful restart as one
        # it had left alone. That is the defect above it wearing the opposite
        # coat: it used to claim restarts it had not performed, and then denied
        # the ones it had. Read off a real ship, with both daemons in fact coming
        # back on the new code: "left alone: claude starting in Galois-Theory".
        #
        # So wait for the daemon's OWN record -- a pid, and a different one --
        # and then say which of the three things happened.
        back = None
        for _ in range(RESTART_WAIT):
            now = daemon.agent_live(c["root"]) or {}
            if now.get("pid") and now["pid"] != was:
                back = now
                break
            time.sleep(1.0)
        if back:
            bounced.append(c["dir"] if name == was_name
                           else "%s (%s -> %s)" % (c["dir"], was_name, name))
        elif daemon.agent_live(c["root"]):
            # Launched, still on its way, and the one that was there is already
            # gone: not a failure, and not a restart anybody can confirm yet.
            # Saying "left alone" here is the lie -- nothing was left alone.
            coming.append("%s (%s)" % (c["dir"], name))
        else:
            held.append("%s (%s)" % (c["dir"], msg.strip() or "did not come back"))

    if bounced:
        print("tutors restarted: %s" % ", ".join(bounced))
    elif not held and not coming and not deferred:
        print("no tutors were attached on %s" % host)
    for h in coming:
        print("  coming back: %s -- the old one is gone; it records its pid "
              "when it starts listening" % h)
    for h in held:
        print("  left alone: %s" % h)
    for h in deferred:
        print("  %s" % h)
    return await_elsewhere(cfg, elsewhere, tree, started) if wait_elsewhere else 0

# How long `--wait` waits for another node's watch: three beats and a margin.
# One beat to notice, one to restart, one for a beat that was mid-pass.
SHIP_WAIT = 3 * supervise.POLL + 10


def ship_record(host):
    """What `ship_beat` last wrote on `host`, or None."""
    try:
        with open(os.path.join(paths.STATE_DIR, "ship-%s.json" % host),
                  "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def await_elsewhere(cfg, elsewhere, tree, since):
    """Wait for other nodes' watches to put their boards and tutors on `tree`.

    A board on another node is not this machine's to stop, and the checkout is
    shared, so that node already has the new files: its own watch restarts the
    board on its next beat (`ship_beat`) and writes the new stamp into the
    record. This reads the records rather than asking over ssh, so it works from
    any machine and catches a commit that never went through `ship.sh`. One line
    per board and per tutor, and one that did not move says why.

    `since` is when the ship began. A process on `tree` that started at or after
    it was restarted by this ship; one that started before was already on it.
    """
    host = recipes.this_host()
    remote_tutors = []
    for c in daemon.courses(cfg):
        st = daemon.agent_record(c["root"]) or {}
        node = st.get("host")
        if (not node or node == host or st.get("state") == "stopped"
                or st.get("mode") == "interactive"):
            continue
        remote_tutors.append((c, node))
    if not tree:
        for c, info in elsewhere:
            print("  %s on %s: can't tell -- the tree's stamp could not be read"
                  % (c["dir"], info.get("node")))
        return 0
    held = machine.slurm_nodes()
    fresh = 3 * supervise.POLL
    remote_tutors = [(c, n) for c, n in remote_tutors
                     if held is None or n in held]

    def on_tree(rec):
        return ("restarted on %s" % tree if (rec.get("started") or 0) >= since
                else "already on %s" % tree)

    def watch_of(node):
        ship = ship_record(node)
        if not ship or time.time() - (ship.get("at") or 0) > fresh:
            return None
        return ship

    no_watch = ("not restarted -- no watch there runs the ship beat; it lands "
                "when that node's board next starts")

    def verdict(c, info):
        node = info.get("node")
        rec = daemon.board_record(c["root"])
        if not rec:
            return "not restarted -- its board was stopped while this waited"
        if rec.get("code") == tree:
            return on_tree(rec)
        if held is not None and node not in held:
            return ("not restarted -- that node is no longer yours; the record "
                    "is a leftover")
        ship = watch_of(node)
        if not ship:
            return no_watch
        if ship.get("tree") == tree:
            why = ship.get("blocked") or ship.get("broken")
            said = (ship.get("boards") or {}).get(c["dir"]) or ""
            if why:
                return "not restarted -- %s" % why
            if said and not said.startswith("restarted"):
                return "not restarted -- %s" % said
        return None

    def tutor_verdict(c, node):
        st = daemon.agent_record(c["root"]) or {}
        ship = watch_of(node)
        said = ((ship or {}).get("tutors") or {}).get(c["dir"]) or ""
        if ship and ship.get("tree") != tree:
            said = ""
        state = st.get("state")
        if st.get("code") == tree and state in ("listening", "working"):
            return on_tree(st)
        if state in ("waking",) or st.get("restarting"):
            return None                          # on its way back, on `tree`
        if state == "stopped" or not st:
            if said.startswith("restarting"):
                return None                      # between the old and the new
            return "not restarted -- its tutor was stopped while this waited"
        if not ship:
            return no_watch
        why = ship.get("blocked") or ship.get("broken")
        if ship.get("tree") == tree and why:
            return "not restarted -- %s" % why
        if state == "working":
            return "mid-turn; its watch restarts it after the turn"
        if said == "mid-turn" and any(x.get("state") == "running"
                                      for x in missions.of(c["root"])):
            return "on a mission; its watch restarts it after the mission"
        if said and not said.startswith("restarting"):
            return "not restarted -- %s" % said
        return None

    left = [("board", c, info) for c, info in elsewhere]
    left += [("tutor", c, node) for c, node in remote_tutors]
    out = {}
    end = time.time() + SHIP_WAIT
    while left:
        for item in list(left):
            kind, c, where = item
            got = verdict(c, where) if kind == "board" else tutor_verdict(c, where)
            if got:
                out[(kind, c["dir"])] = got
                left.remove(item)
        if not left or time.time() >= end:
            break
        time.sleep(2.0)
    for c, info in elsewhere:
        got = out.get(("board", c["dir"]))
        if not got:
            rec = daemon.board_record(c["root"]) or {}
            got = "not restarted -- still on %s after %d s" % (
                rec.get("code") or "code from before stamps", SHIP_WAIT)
        print("  %s on %s: %s" % (c["dir"], info.get("node"), got))
    for c, node in remote_tutors:
        got = out.get(("tutor", c["dir"]))
        if not got:
            st = daemon.agent_record(c["root"]) or {}
            if st.get("state") == "waking":
                got = "coming back on %s -- still waking after %d s" % (
                    tree, SHIP_WAIT)
            elif st.get("restarting") or st.get("state") == "stopped":
                got = ("writing its handoff; back on %s when it ends" % tree)
            else:
                got = "not restarted -- still on %s after %d s" % (
                    st.get("code") or "code from before stamps", SHIP_WAIT)
        print("  %s's tutor on %s: %s" % (c["dir"], node, got))
    return 0

# ---------------------------------------------------------------------------
# Watching what is up
# ---------------------------------------------------------------------------
def last_line(out):
    """The last thing a command said, for a one-line report. Never an empty one."""
    said = [l.strip() for l in (out or "").splitlines() if l.strip()]
    return said[-1] if said else "no reason given"


def ship_beat(cfg, host, memo, say):
    """Put this node's boards and tutors on the tree's code. Returns what it said.

    THE SHIP LANDS WHEREVER THE LESSON IS SERVED. The checkout is shared, so a
    ship puts the new files in front of every node at once and no node ever
    sees a pull move HEAD. What is stale is the processes, and each one records
    the stamp it loaded (`tutorboard/stamp.py`). A board here whose stamp is
    not the tree's is restarted through `cmd_restart(only=...)`, which keeps its
    address-holder restoration; another node's board is that node's beat's.

    A TUTOR MID-TURN IS NOT BOUNCED THIS BEAT. It is bounced on the first beat
    it is listening with no mission running, without blocking: `restarting` on
    the record, a SIGTERM that starts its handoff, and `handed_off` to bring it
    back as the agent the record names, because a deploy must not swap the
    assistant in the middle of a lesson.

    Guarded three ways. A busy or detached checkout waits for the next beat. A
    tree that does not import bounces nothing, checked once per stamp. And a
    board or tutor already tried on this stamp is not tried again until the
    tree moves. `ship-<host>.json` says what the beat did, and is what `tutor
    restart --wait` reads from another machine.
    """
    m = memo.setdefault("#ship", {"said": [], "checked": {}, "boards": {},
                        "tutors": {}, "results": {}})
    tree = stamp.tree()
    if tree is None:
        return []
    did, extra = [], {}
    # WHAT EACH PROCESS'S LAST TRY ON THIS STAMP CAME TO, kept across beats.
    # A board that failed is not retried on the same stamp, so the beat that
    # said why is the only one that ever will; every later record carries it
    # until the tree moves.
    results = m["results"]
    for key in [k for k, v in results.items() if v[0] != tree]:
        del results[key]
    boards, tutors = {}, {}

    def result(kind, name, said):
        results[(kind, name)] = (tree, said)

    def tell(line, once=None):
        if once is not None:
            if once in m["said"]:
                return
            m["said"] = (m["said"] + [once])[-50:]
        did.append(line)
        say(line)

    def landed():
        for (kind, name), (_t, said) in results.items():
            (boards if kind == "board" else tutors).setdefault(name, said)
        rec = dict(host=host, pid=os.getpid(), at=time.time(), tree=tree,
                   boards=boards, tutors=tutors, **extra)
        try:
            os.makedirs(paths.STATE_DIR, exist_ok=True)
            path = os.path.join(paths.STATE_DIR, "ship-%s.json" % host)
            tmp = "%s.%d.tmp" % (path, os.getpid())
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(rec, fh, indent=2)
            os.replace(tmp, path)
        except OSError:
            pass
        return did

    why = stamp.blocked(daemon.TOOL)
    if why:
        extra["blocked"] = why
        tell("the tree at %s waits: %s" % (tree, why), once=("blocked", tree, why))
        return landed()

    with stamp.restart_lock(wait=False) as mine:
        if not mine:
            extra["busy"] = "another restart on this node holds the lock"
            return landed()
        stale_boards, stale_tutors = [], []
        for c in daemon.courses(cfg):
            root, name = c["root"], c["dir"]
            rec = daemon.board_record(root) or {}
            if (rec.get("node") == host
                    and processes.board_is_running(rec.get("pid"), root)
                    and rec.get("code") != tree
                    and m["boards"].get(name) != tree):
                stale_boards.append(c)
            st = daemon.agent_live(root)
            if (st and st.get("mode") != "interactive"
                    and not st.get("restarting")
                    and st.get("code") != tree
                    and m["tutors"].get(name) != tree):
                stale_tutors.append((c, st))
        if not stale_boards and not stale_tutors:
            return landed()

        # A REAL IMPORT FAILURE IS REMEMBERED FOR THE STAMP; A CHECK THAT COULD
        # NOT RUN IS NOT. `ok` is None for a timeout or an OSError -- a slow
        # filer, not a broken tree -- and caching that would keep a good ship
        # off this node for the rest of the generation.
        got = m["checked"].get(tree) or stamp.imports(daemon.TOOL)
        ok, line = got
        if ok is not None:
            m["checked"][tree] = got
        if ok is None:
            extra["unchecked"] = "the import check did not finish (%s)" % line
            tell("the tree at %s could not be checked this beat (%s); trying "
                 "again next beat" % (tree, line), once=("unchecked", tree))
            return landed()
        if not ok:
            extra["broken"] = "the tree does not import (%s)" % line
            tell("the tree at %s does not import (%s); everything stays on its "
                 "code" % (tree, line), once=("broken", tree))
            return landed()

        if stale_boards:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                cmd_restart(cfg, [], only={c["dir"] for c in stale_boards})
            said = buf.getvalue().splitlines()
            for c in stale_boards:
                m["boards"][c["dir"]] = tree
                rec = daemon.board_record(c["root"]) or {}
                if rec.get("code") == tree and processes.board_is_running(
                        rec.get("pid"), c["root"]):
                    result("board", c["dir"], "restarted on %s" % tree)
                    tell("%s: board restarted on %s" % (c["dir"], tree))
                else:
                    mine_said = [l for l in said if c["dir"] in l]
                    reason = last_line("\n".join(mine_said) or buf.getvalue())
                    result("board", c["dir"],
                           "would not restart on %s (%s)" % (tree, reason))
                    tell("%s: board would not restart on %s (%s)"
                         % (c["dir"], tree, reason))

        import signal as _sig
        for c, st in stale_tutors:
            name, live = c["dir"], course_repo.session_dir(c["root"])
            # READ AGAIN, NOW. The board restarts above can take seconds each,
            # and a tutor listening when the beat began may be mid-turn by the
            # time its turn in this loop comes. The snapshot says who was stale;
            # only a fresh record says who may be signalled.
            now = daemon.agent_live(c["root"])
            if (not now or now.get("restarting") or now.get("code") == tree
                    or now.get("mode") == "interactive"):
                continue
            running = [x for x in missions.of(c["root"])
                       if x.get("state") == "running"]
            if (now.get("state") != "listening" or running
                    or now.get("pid") != st.get("pid")):
                result("tutor", name, "mid-turn")
                tell("%s: tutor mid-turn; restarted on a later beat" % name,
                     once=("deferred", name, tree))
                continue
            m["tutors"][name] = tree
            pid = now.get("pid")
            if not pid:
                result("tutor", name, "no pid in its record")
                tell("%s: tutor left on its code -- no pid in its record" % name)
                continue
            daemon.agent_state(live, restarting=True, stopped_at=time.time())
            try:
                os.kill(pid, _sig.SIGTERM)
            except OSError:
                pass
            clause = daemon.handed_off(cfg, c, now.get("agent") or recipes.resolve_agent(cfg, c))
            result("tutor", name, "restarting on %s" % tree)
            tell("%s: tutor restarting on %s (%s)" % (name, tree, clause))
    return landed()


def watch_once(cfg, host, memo, say):
    """One pass over every workspace, repairing what is down. Returns what it did.

    `memo` is the loop's memory, keyed by workspace: how many health probes have
    missed in a row, how many repairs have been tried, and when the next one is
    allowed. A board that is a second late writing a slate PNG is not a board to
    bounce, and a tutor that cannot start -- no allowance, no command on the path
    -- must not be started every twenty seconds for seven days.

    What it will NOT do is the load-bearing half:

    - nothing without a record. `board stop` and `tutor headless --stop` remove
      theirs, and a workspace nobody has ever opened never had one. Both mean a
      person has not asked for this, and a watchdog that starts nine boards
      because it found nine directories is a worse failure than the one it fixes.
    - nothing whose record names another machine. The pid in it cannot be
      read from here, so the only honest answer is to leave it.
    - nothing a restart is already doing. `tutor restart --tutors` writes
      `restarting` before it signals, exactly so a bounce can be told from a
      death, and this waits that grace out before deciding a bounce has failed.
    """
    did = []
    for c in daemon.courses(cfg):
        root, name = c["root"], c["dir"]
        mem = memo.setdefault(name, {"misses": 0, "board_tries": 0, "board_at": 0.0,
                              "tutor_tries": 0, "tutor_at": 0.0})
        now = time.time()

        # --- the board ------------------------------------------------------
        rec = daemon.board_record(root) or {}
        pid_ok = processes.board_is_running(rec.get("pid"), root)
        answers = supervise.answering(rec.get("port")) if (rec and pid_ok) else False
        mem["misses"] = 0 if answers else mem["misses"] + 1
        verdict = supervise.board_verdict(rec, host, pid_ok, answers, mem["misses"])
        if verdict in ("revive", "hung") and now >= mem["board_at"]:
            if verdict == "hung":
                # Wedged rather than gone: the pid has to be taken out before a
                # start, or the port is still held and the new one lands
                # somewhere the iPad is not looking.
                daemon.board(root, "stop")
            # `board start` points the HTTPS name at the board it starts when
            # the name is pointing at nothing, so the address comes back with it.
            code, out = daemon.board(root, "start")
            mem["misses"] = 0
            # A clean start clears the count only for a board that was DEAD. A
            # hung one that starts cleanly has proved nothing until it answers,
            # and the `ok` branch below is what clears it then: a board whose
            # `/health` always fails is otherwise bounced every 55 seconds for
            # as long as the chain runs, with no backoff at all.
            mem["board_tries"] = (0 if code == 0 and verdict != "hung"
                                  else mem["board_tries"] + 1)
            mem["board_at"] = now + supervise.next_try(mem["board_tries"])
            note = "%s: board %s" % (name, {"revive": "was dead",
                                            "hung": "was wedged"}[verdict])
            did.append(note if code == 0 else
                       "%s -- and would not start (%s)" % (note, last_line(out)))
            say(did[-1])
        elif verdict == "ok":
            mem["board_tries"] = 0

        # --- the tutor ------------------------------------------------------
        st = daemon.agent_record(root) or {}
        tverdict = supervise.tutor_verdict(
            st, host, processes.pid_alive(st.get("pid")))
        if tverdict == "revive" and now >= mem["tutor_at"]:
            # Whatever configuration says now, not what the dead record named:
            # the same rule `cmd_restart` follows, and for the same reason.
            agent_name = recipes.resolve_agent(cfg, c) or st.get("agent")
            # The handover flag has been acted on; leaving it set would make
            # every later stop of this tutor look like a machine going away.
            if st.get("handover"):
                daemon.agent_state(course_repo.session_dir(root), handover=None)
            code, msg = daemon.agent_start(cfg, c, agent_name)
            mem["tutor_tries"] = 0 if code == 0 else mem["tutor_tries"] + 1
            mem["tutor_at"] = now + supervise.next_try(mem["tutor_tries"])
            did.append("%s: tutor was dead -- %s" % (name, (msg or "").strip()))
            say(did[-1])
        elif tverdict == "ok":
            mem["tutor_tries"] = 0

    # --- THE SHIP, EVERY PASS ---------------------------------------------
    # Before the address, so a board it restarts is checked in the same beat.
    try:
        did += ship_beat(cfg, host, memo, say)
    except Exception as exc:                                 # noqa: BLE001
        did.append("the ship beat failed and the pass is carrying on: %r" % (exc,))
        say(did[-1])

    # --- THE ADDRESS, EVERY PASS ------------------------------------------
    # A board can be perfect and unreachable, and that is the whole of what the
    # iPad experiences: one HTTPS name, which needs a `tailscaled` on THIS node
    # and a `tailscale serve` pointing at a port that answers. Both can fail with
    # nothing dying -- a link that lost a race while a generation was starting,
    # a name still pointing at the port of a board that has moved -- and until
    # now nothing ever looked again. `link` was called after a board START, so a
    # link that failed there was never retried: measured on compute306, where
    # every process was healthy, both boards answered on loopback, and the glass
    # stayed white.
    addr = memo.setdefault("#address", {"at": 0.0, "tries": 0,
                                        "waiting": False})
    now = time.time()
    if now >= addr["at"]:
        here = [c for c in daemon.courses(cfg)
                if processes.board_is_running(
                    (daemon.board_record(c["root"]) or {}).get("pid"), c["root"])
                and (daemon.board_record(c["root"]) or {}).get("node") == host]
        stalled = None
        if here:
            # WHICH COURSE THE ADDRESS IS FOR IS A DECISION. `address_course`
            # reads the person's, and reads nothing else; with no choice
            # standing on this node it is None and what follows is the boards
            # here in the order they were found, which is the alphabet wearing a
            # disguise. A guess may keep the address alive and may not move it:
            # everything below that says "and only when the choice is known"
            # says it for that reason.
            want = daemon.address_course(cfg, here)
            guess = want is None
            if guess:
                want = here[0]
            mine = (daemon.board_record(want["root"]) or {}).get("port")
            why = forced = None
            if not tailscale.daemon_running():
                why = "there is no tailnet link on this node"
            else:
                code, out = daemon.board(want["root"], "vpn", "holder")
                port = (out or "").strip()
                if not (code == 0 and port.isdigit()
                        and supervise.answering(int(port))):
                    why = "the address is not pointing at a board that answers"
                elif not guess and mine and int(port) != int(mine):
                    # POINTING AT SOMETHING THAT ANSWERS IS NOT THE TEST. A
                    # board the person did not ask for answers just as well, and
                    # the pass that only asks "does anything answer" calls that
                    # healthy and leaves them in it for ever: one bad moment --
                    # the chosen board a few seconds down, mid-restart -- hands
                    # the name to the next course along and nothing ever asks
                    # again. The name has to be on the chosen board's own port.
                    #
                    # WHICH IS ALSO WHERE ANSWERING IS NOT OWNING LANDS. A board
                    # an ended generation left behind answers exactly like a
                    # live one and is named by no record, so "does anything
                    # answer" calls the name resting on it healthy for as long
                    # as that process lives -- and a leftover's port is not the
                    # chosen board's port either, so this is the test that takes
                    # the name off it. No separate one: a leftover is still an
                    # address that draws, and with nobody having chosen there is
                    # nothing here entitled to move it onto something else.
                    #
                    # ONLY A CHOICE REACHES THIS BRANCH, and `guess` is what
                    # keeps it that way: this is the one place that overrides
                    # the guard against a wandering address, and the alphabet
                    # is not entitled to it. A record with no port says nothing
                    # either way and is left alone -- a truncated record read as
                    # drift is a claim every pass, for ever.
                    #
                    # AND A NAME IS WORTH MOVING ONLY ONTO A BOARD THAT CAN DRAW
                    # SOMETHING. `here` is a pid and a node, which a wedged
                    # board passes: alive, holding its port, answering nothing.
                    # Claiming for that is a white screen in exchange for a
                    # working wrong lesson. The wedged board is the half above's
                    # to fix -- it stops the pid, starts it again and links it --
                    # and the name comes back on the pass after that one.
                    if supervise.answering(int(mine)):
                        why = "the address is pointing at a course nobody chose"
                        forced = True
                    else:
                        stalled = True
            # HOLDING STILL IS ALSO A THING TO SAY, once. The name is on a
            # course nobody chose and the chosen course's board cannot be given
            # it yet, which is a state a reader of the log has to be able to
            # see; a line every twenty seconds is not seeing it. The flag marks
            # the entry, and is cleared wherever the state is not so the next
            # time is reported too. `tries` is untouched by it: the recheck is
            # the next pass, not a backoff away, because this clears the moment
            # the board half finishes.
            if stalled and not addr["waiting"]:
                did.append("the address is pointing at a course nobody chose, "
                           "and %s's own board is not answering yet, so the "
                           "name is left where it is" % want["dir"])
                say(did[-1])
            if why:
                if forced:
                    # A name on another course's LIVE board is not free, and
                    # `link` will not take it: `--if-free` is there so that a
                    # board coming up cannot drag the iPad out of the lesson
                    # somebody is reading. A standing choice may, and is the one
                    # thing that may, so it uses the forced claim -- the same
                    # command a person types to say which course they mean,
                    # typed here on their behalf because they already said it.
                    #
                    # A CLAIM THAT FAILED MUST NOT READ LIKE ONE THAT WORKED.
                    # `tailscaled` runs on a node that is not logged in, so the
                    # gate above passes and the serve is still refused. The exit
                    # code is the only thing that knows.
                    code, out = daemon.board(want["root"], "vpn", "serve")
                    if code == 0:
                        did.append("%s, so the address was pointed back at %s"
                                   % (why, want["dir"]))
                    else:
                        did.append("%s -- and the claim for %s would not go "
                                   "through (%s)"
                                   % (why, want["dir"], last_line(out)))
                else:
                    # `--if-free`: a guess may keep the address alive and may
                    # not move it off a board somebody is reading.
                    daemon.board(want["root"], "vpn", "serve", "--if-free")
                    did.append("%s, so the address was offered to %s"
                               % (why, want["dir"]))
                addr["tries"] += 1
                addr["at"] = now + supervise.next_try(addr["tries"])
                say(did[-1])
            else:
                addr["tries"] = 0
        # A pass with no board up here is not the state ending, but it is not
        # the state either, and the flag has to come off in both: an empty
        # `here` is what a generation handover looks like, which is exactly when
        # the address gets stuck, and a flag left set there silences the line on
        # the way back in.
        addr["waiting"] = bool(stalled)
    return did


def cmd_watch(cfg, args):
    """Keep the boards and tutors on this machine up. Runs until it is stopped.

        tutor watch                 the loop
        tutor watch --once          one pass, then stop
        tutor watch --interval 30   how often to look (seconds)

    The Mac's `tutor-board.tutor-watch` LaunchAgent runs it, which is what
    brings every board back after a reboot there.

    It repairs only what a person has already asked for -- see `watch_once` --
    and it says what it repaired into whatever log it was started with, as well
    as into `watch.json`.
    """
    interval = float(daemon.flag(args, "--interval") or supervise.POLL)
    once = "--once" in args
    host = recipes.this_host()
    memo, repairs, checks = {}, [], 0
    started = time.time()

    stopping = {"now": False}

    def bye(*_):
        stopping["now"] = True
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            signal.signal(sig, bye)
        except (OSError, ValueError):
            pass

    def say(line):
        print("[%s] %s" % (time.strftime("%H:%M:%S"), line))

    while True:
        checks += 1
        try:
            did = watch_once(cfg, host, memo, say)
        except Exception as exc:                             # noqa: BLE001
            # A WATCHDOG MAY NOT DIE OF THE THING IT IS WATCHING. One unreadable
            # record, one workspace half-way through being created, one NFS
            # hiccup -- any of them would take the loop down and leave nothing
            # watching anything, which is worse than the fault it tripped over.
            did = []
            say("the watch pass failed and the loop is carrying on: %r" % (exc,))
        repairs = (repairs + did)[-20:]
        supervise.note_watch(host=host, pid=os.getpid(), started=started,
                             last=time.time(), checks=checks, repairs=repairs,
                             job=os.environ.get("SLURM_JOB_ID") or "")
        if once or stopping["now"]:
            break
        if supervise.stopped():
            say("%s exists; the watch loop is standing down" % supervise.STOP)
            break
        if watch_stale(memo, say):
            watch_reexec()             # normally never returns
        end = time.time() + interval
        while time.time() < end and not stopping["now"]:
            time.sleep(0.5)
        if stopping["now"]:
            break
    return 0


def watch_stale(memo, say):
    """Is the watch loop itself running code the tree has moved past?

    `ship_beat` puts this node's boards and tutors on the tree's stamp, and
    nothing put the loop doing it there. A loop that runs for weeks -- the Mac's
    LaunchAgent, which only a reboot restarts -- would go on repairing with the
    code it read at boot, fixes on disk and nowhere in the process making the
    decisions. So the loop compares its own stamp (`stamp.LOADED`, taken before
    `bin/tutor` imported anything) with the tree's, under `ship_beat`'s guards:
    a busy or detached checkout waits, and a tree that does not import keeps the
    loop on what it has, with the import check shared with the beat's memo.
    """
    loaded, tree = stamp.LOADED, stamp.tree()
    if not loaded or not tree or loaded == tree or stamp.blocked(daemon.TOOL):
        return False
    m = memo.setdefault("#ship", {"said": [], "checked": {}, "boards": {},
                                  "tutors": {}, "results": {}})
    got = m["checked"].get(tree) or stamp.imports(daemon.TOOL)
    if got[0] is not None:
        m["checked"][tree] = got
    if not got[0]:
        return False
    say("the watch loop is on %s and the tree is at %s; it restarts itself on "
        "the tree's code" % (loaded, tree))
    return True


def watch_reexec():
    """Replace the watch loop with itself on the tree's code, same pid.

    The same pid on purpose: the LaunchAgent's KeepAlive and `watch.json`
    both follow the process, and an exec keeps both pointing at it. Flushed
    first, for `tool_reexec`'s reason: the log is a file, and the line saying
    why would be lost in the exec.
    """
    sys.stdout.flush()
    sys.stderr.flush()
    try:
        os.execve(sys.executable,
                  [sys.executable, daemon.TUTOR] + sys.argv[1:],
                  dict(os.environ))
    except OSError:
        pass


def cmd_down(cfg, args):
    """Take this machine out of serving. The other half of `tutor resume`.

        tutor down              every board and tutor here, and the tailnet link
        tutor down galois       one workspace, and nothing else

    It is what a machine handing the board over says. Two boards serving one
    `live/` directory off a shared home is worse than a board on the wrong
    machine: both write cards, both answer the same inbox line, and the student
    pays for two turns of the same lesson.

    The tutor is stopped with a wait, because that stop IS the handoff turn and
    the point of taking it over is to carry the lesson, not to drop it.
    """
    named = [a for a in args if not a.startswith("-")]
    host = recipes.this_host()
    found = daemon.courses(cfg)
    if named:
        want = [daemon.pick(found, named[0])]
    else:
        want = [c for c in found
                if (daemon.board_record(c["root"]) or {}).get("node") == host
                or (daemon.agent_record(c["root"]) or {}).get("host") == host]
    if not want or want == [None]:
        print("nothing here to stop")
        return 0
    for c in want:
        st = daemon.agent_record(c["root"]) or {}
        if st.get("host") == host and st.get("state") not in (None, "stopped"):
            # The record says it is a handover rather than somebody leaving, so
            # whoever takes it over knows to pick it back up. `agent_state` merges,
            # so the daemon's own exit record does not erase this.
            daemon.agent_state(course_repo.session_dir(c["root"]),
                               handover=time.strftime("%Y-%m-%d %H:%M:%S"))
            code, msg = daemon.agent_stop(c, wait=True)
            print("  %s" % (msg or "").strip())
        # ONLY A BOARD THIS MACHINE ACTUALLY HAS. `board stop` against a record
        # naming another node does not stop anything -- it cannot -- and it
        # DELETES THE RECORD, which is worse than doing nothing: the process goes
        # on serving with nothing on disk naming it, so the hub cannot find it,
        # the watch loop sees no record and leaves it alone, and the next tutor
        # start puts a SECOND board on a fallback port against the same `live/`.
        # That is not hypothetical; it is what this line did the first time it
        # ran, to PSYCH-ASR, ten seconds after the board had moved.
        on = (daemon.board_record(c["root"]) or {}).get("node")
        if on and on != host:
            print("  %s: its board is on %s, not here; left alone"
                  % (c["dir"], on))
            continue
        code, out = daemon.board(c["root"], "stop")
        print("  %s: %s" % (c["dir"], last_line(out)))
    if not named:
        # The link is a property of the MACHINE, not of a workspace, and it is
        # the thing that must not be held by a node that has stopped serving:
        # the state directory is shared, so a claim left behind makes the next
        # node refuse to bring the link up at all.
        code, out = daemon.board(want[0]["root"], "vpn", "down")
        print("  %s" % last_line(out))
    return 0
