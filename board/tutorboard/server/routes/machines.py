"""What this machine can teach, and which course the one address opens.

Nothing here reaches the filesystem from a request: a course named in a
request is matched against what this server already discovered.
"""

import json
import os
import time

from . import NOT_MINE
from ...net import tailscale
from ... import limits
from ... import choice
from .. import spawn
from ... import atlas
from ... import colibri
from ... import machines
from ... import meeting
from ... import missions
from ... import news
from ...course import config
from ...course.repo import Repo
from ...lesson import state
from ...lesson import turns


def get(h, repo, path):
    if path == "/courses.json":
        info = {}
        try:
            with open(os.path.join(repo.live, ".board.json"), "r", encoding="utf-8") as fh:
                info = json.load(fh)
        except (OSError, ValueError):
            pass
        urls = [u for u in info.get("urls", []) if "127.0.0.1" not in u]
        return h.send_json({
            "courses": machines.workspaces(repo),
            "where": (urls[0] if urls else "") ,
            "node": info.get("node"),
        })

    if path == "/atlas.json":
        # Everything the front door draws, in one request. The hub's
        # `/courses.json` stays exactly as it was -- the board's own switcher
        # reads it, and a payload two surfaces share is a payload that grows a
        # field for one of them and breaks the other.
        return h.send_json(machines.atlas_payload(repo))

    if path.startswith("/meeting/"):
        # A note this board wrote, served back. The NAME is matched against what
        # is actually in `meetings/`, never joined onto a path: the same rule as
        # every other name that arrives from a browser.
        base = atlas.root() or repo.root
        want = path[len("/meeting/"):].strip("/")
        out_dir = os.path.join(base, meeting.OUT_DIR)
        try:
            names = os.listdir(out_dir)
        except OSError:
            names = []
        for n in names:
            if n == want + ".pdf":
                return h.send_file(os.path.join(out_dir, n))
        return h.send_json({"ok": False, "error": "no such notes"}, status=404)

    if path == "/news":
        # The same list the board payload carries, for a surface that is not on
        # the stream -- the front door polls, it does not subscribe.
        return h.send_json({"news": news.waiting(repo)})

    if path == "/missions":
        # WHAT IS STILL RUNNING SOMEWHERE NOBODY IS LOOKING, and how the ones
        # that stopped ended. `/news` above is the past tense of the same
        # sentence and this is the present one; they are separate routes because
        # a card that landed and a job still going are different things to do
        # about it. Read off disk in every workspace on the machine, so a board
        # that has only just started answers as well as the one that dispatched.
        return h.send_json({"missions": missions.waiting(repo)})

    if path == "/health":
        # `dir` so a caller can confirm it reached the course it meant --
        # ports are derived from names and derivation is not proof, and the
        # hub checks this before it reloads into a lesson. `chosen` so a
        # decision can be read off a board rather than raced for. `limited`
        # so an allowance can be too: a board answering perfectly well whose
        # tutor has been told it is out of quota is still up, and is still
        # the wrong place to send a lesson. Only the machine serving can know
        # that -- the limit is written by its own tutor into its own state
        # directory -- so it is published here for the same reason the choice
        # is. `tutor` because a board with nobody behind it is a lesson that
        # cannot answer, and the hub says so rather than drawing it as ready.
        # `host` so a CLIENT can tell which machine it reached.
        agent = state.load_agent(repo) or {}
        return h.send_json({"ok": True, "root": repo.root,
                               "dir": os.path.basename(repo.root),
                               # The qualified name too, so a caller can tell
                               # `courses/Probability` from a future
                               # `practice/Probability` without guessing.
                               "id": atlas.identify(repo.root),
                               "host": tailscale.tailnet_self() or "",
                               "chosen": machines.chosen_target(),
                               "tutor": agent.get("state") or None,
                               "limited": limits.limited_until()})
    return NOT_MINE


def post(h, repo, path):
    # SOMEBODY IS LOOKING AT THIS WORKSPACE, NOW.
    #
    # The one fact the notifications are built out of, and the only one that
    # cannot be derived: a board is a long-lived process that goes on running in
    # an empty room, so "a request arrived" and "a person is reading this" are
    # different things. The page says it -- on its first payload, when a card
    # lands in front of it, and when the tab comes back to the front -- and it is
    # throttled there rather than here.
    #
    # It marks THIS workspace and no other: a name from a browser never reaches
    # the filesystem, and there is exactly one root this server may write into.
    if path == "/seen":
        news.mark_seen(repo.root)
        # AND A MISSION THAT ENDED IN THIS WORKSPACE HAS NOW BEEN LOOKED AT.
        # Looking means coming here, which is exactly what has happened: the row
        # in the strip is the way back and this is the far end of it. Only the
        # ones that ENDED -- a running mission stays on the list after a look,
        # because it is still running and that is the fact being reported.
        missions.looked(repo.root)
        # The next payload has to be able to say the badge has gone; without
        # this it says the old answer for up to `news.TTL`, and a notification
        # that survives being read is one nobody trusts again.
        news.forget()
        missions.forget()
        h.server.hub.worker.dirty.set()
        return h.send_json({"ok": True})

    if path == "/notes":
        # MEETING NOTES, FROM THE FRONT DOOR, because that is what is open when
        # somebody remembers they have one in ten minutes. The work is the same
        # `meeting.build` the command line runs -- one builder, so the note the
        # button makes and the note the terminal makes are the same document.
        try:
            payload = json.loads(h.read_body().decode("utf-8"))
        except Exception:                                    # noqa: BLE001
            return h.send_json({"ok": False, "detail": "bad json"}, status=400)
        base = atlas.root() or repo.root
        when, said = meeting.resolve_since(payload.get("since") or "", base)
        if when is None:
            return h.send_json({"ok": False, "detail": said}, status=400)
        try:
            rec = meeting.build(base, when, said, here=repo.root)
        except Exception as exc:                             # noqa: BLE001
            return h.send_json({"ok": False,
                                "detail": str(exc)[-300:]}, status=500)
        # The markdown is not sent: it is the document, it is megabytes on a
        # long period, and the page shows a name and a link rather than prose.
        rec.pop("markdown", None)
        return h.send_json(rec)

    if path == "/colibri":
        # START THE LOCAL MODEL'S SERVER, AND SAY SO AT ONCE.
        #
        # `coli-code` exits with "No colibri server is running. Start one:
        # coli-up", which is the right message in a terminal and a dead end on an
        # iPad. It cannot be done inside this request either -- an allocation, a
        # 429 GB load and a warm-up generation is seven or eight minutes on a
        # good day and can pend indefinitely -- so this returns the state and
        # lets the payload carry the rest. See `spawn.wake_colibri`.
        started, said = spawn.wake_colibri()
        h.server.hub.worker.dirty.set()
        return h.send_json({"ok": True, "started": started, "detail": said,
                            "colibri": colibri.status(fresh=True)})

    if path == "/elsewhere":
        # PUT AN ASSISTANT TO WORK IN A WORKSPACE YOU ARE NOT LOOKING AT.
        #
        # Asked for almost word for word: *"I want to be able to go into a
        # different section of a project, or a different project completely, and
        # put other agents to work on other things while the first one is
        # working."* Three of the four pieces already existed --
        # `machines.workspaces` is the list, `tutor agent start` is the start,
        # and `news.elsewhere` is how you are told it landed -- so this is the
        # seam between them.
        #
        # THE ASSISTANT IS NAMED ON THE COMMAND LINE AND NOT WRITTEN INTO THAT
        # SITTING. Layer 1 of `resolve_agent` is "this once", which is exactly
        # what this is; writing it into the other workspace's `state.json` would
        # be changing a sitting nobody is watching, and an agent change does not
        # carry the conversation the old one was holding. If something is already
        # listening there the start is a no-op and says so, and the task goes to
        # whoever is there -- which is the honest answer and is in the reply.
        try:
            payload = json.loads(h.read_body().decode("utf-8") or "{}")
        except Exception:                                    # noqa: BLE001
            return h.send_json({"ok": False, "error": "bad json"}, status=400)
        task = (payload.get("task") or "").strip()
        if not task:
            return h.send_json({"ok": False, "error": "say what to do"},
                               status=400)
        agent = config.clean_agent(payload.get("agent"))
        want = payload.get("repo") or ""
        # Only a workspace this server already discovered, and the ROOT comes off
        # the match rather than being rebuilt out of the name -- the same rule
        # `/switch` follows, and for the same reason: the same name can sit under
        # two families.
        match = None
        for c in machines.workspaces(repo):
            if want in (c["repo"], c["id"]):
                match = c
                break
        if not match:
            return h.send_json({"ok": False, "error": "unknown workspace"},
                               status=404)

        # THE START IS ASKED FIRST, AND THE TASK IS WRITTEN ONLY IF IT IS
        # ALLOWED. The other way round leaves a refused job sitting in another
        # workspace's transcript with nothing that will ever read it -- and there
        # are two refusals here that fire routinely: one colibri sitting at a
        # time machine-wide, and cards that must not be committed. `/say` writes
        # before it wakes, correctly, because there the work already exists and
        # must not be lost; here the request is what creates it.
        #
        # Nothing is missed by writing second. `agent_start` forks and returns,
        # so the daemon is not up yet -- and when it is, `board wait` blocks
        # until something lands rather than reading the inbox once.
        args = ["agent", "start", match["repo"]]
        if agent:
            args += ["--agent", agent]
        code, out = spawn.tutor_cli(args, timeout=60)
        said = out.strip()[-300:]
        if code != 0:
            # A refusal is an answer and has to reach the glass. Both of them
            # name what to do about it -- which workspace is holding the one
            # slot, or the one line that stops a card being tracked.
            return h.send_json({"ok": False, "repo": match["repo"],
                                "agent": agent, "error": said}, status=409)

        # The task goes in as a turn of theirs, because that is what it is: they
        # asked for it, and a transcript over there that opens with the answer
        # reads as an assistant that decided to do this on its own. One
        # implementation of "a student said something" -- the same
        # `turns.write_turn` and the same inbox line `/say` writes -- against a
        # Repo for the root that came back from the walk.
        target = Repo(match["root"])
        tid = turns.next_turn_id(target)
        record = {
            "id": tid, "rev": turns.turn_revision(target, tid), "kind": "text",
            "answers": None,
            "t": time.time(),
            "iso": time.strftime("%Y-%m-%d %H:%M:%S"),
            "from": "student", "text": task, "signal": None, "read": False,
        }
        turns.write_turn(target, record)
        with open(target.messages_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")

        # AND THE MISSION IS A RECORD, IN THE WORKSPACE IT IS ABOUT.
        #
        # Asked for in these words: *"just because I close the iPad doesn't mean
        # that should end. Next time I open the iPad and access the board, that
        # mission should still be going or notify me somewhere if it's done."*
        # The daemon already survived the lid; nothing said it had. Written LAST,
        # after the start was allowed and the task is on disk, because a record
        # of a mission that was refused is a row about work nobody is doing.
        #
        # `ship` is carried and not yet honoured -- see HANDOFF item 2, which is
        # where a mission gets told to push its own diff and where the check that
        # lets it is built. The field is here because the record is written once
        # and read by that turn later.
        ceiling = 0.0
        if agent == "colibri":
            # THE ONE ASSISTANT WITH A CEILING. A colibrì turn runs inside the
            # serve job's allocation, so the mission cannot outlive that job's
            # walltime -- and until this nothing anywhere said what it was.
            left = (colibri.status() or {}).get("left")
            if left:
                ceiling = time.time() + float(left)
        rec = missions.dispatch(match["root"], task=task, turn=tid,
                                agent=agent, ship=bool(payload.get("ship")),
                                frm=atlas.identify(repo.root), ceiling=ceiling)
        missions.forget()
        h.server.hub.worker.dirty.set()
        return h.send_json({"ok": True, "repo": match["repo"],
                            "agent": agent, "turn": tid, "detail": said,
                            "mission": rec["id"], "ship": rec["ship"],
                            "ceiling": rec["ceiling"]})

    if path == "/switch":
        try:
            payload = json.loads(h.read_body().decode("utf-8"))
        except Exception:
            return h.send_json({"ok": False, "error": "bad json"}, status=400)
        want = payload.get("repo") or ""

        # Only a workspace this server already discovered. No path from a
        # request ever reaches the filesystem: the name is matched against what
        # the walk found, and the ROOT comes off the match rather than being
        # rebuilt out of the name. Rebuilding it was safe while every course was
        # a sibling and `dirname(root)` was the whole tree; it is not safe now,
        # because the same name can sit under two families.
        #
        # Either spelling is accepted -- `Probability` or `courses/Probability`
        # -- because the hub has always sent the bare directory and an address
        # (§9) spells the qualified one.
        match = None
        for c in machines.workspaces(repo):
            if want in (c["repo"], c["id"]):
                match = c
                break
        if not match:
            return h.send_json({"ok": False, "error": "unknown course"}, status=404)
        target = match["root"]

        # A tap in the hub is a person saying which course they mean. The
        # record is written first and unconditionally, because it is the one
        # thing that survives this board being restarted, and it is what every
        # later question about "which course" is answered from.
        choice.remember_chosen(match["repo"], target,
                                 host=tailscale.tailnet_self() or "",
                                 family=match["family"])

        # THE ADDRESS IS MOVED HERE, IN THIS REQUEST, BY THE MACHINE SERVING.
        #
        # A course has its own port, so the one name the iPad is installed
        # against has to be re-pointed at the board being opened or the tap
        # lands nowhere: the hub asks the address which course it is serving
        # before it reloads, the answer is still the old one, and after a
        # minute of that the page can only say so. From the iPad that is a
        # switch that cannot be made, reported as "whenever I want to switch
        # courses... I can hit it, but it never seems to work."
        #
        # `board vpn serve` is deliberate about this where `ts_repoint` is
        # careful: a start does not steal a name that a live board is holding,
        # because `tutor restart` walks every course on the machine and would
        # otherwise leave the address wherever the alphabet finished. A tap in
        # the hub is the opposite case -- it is a person naming the course they
        # want -- so it takes the name, and it is the only thing here that does.
        code, out = spawn.board_cli(target, ["start"])
        if code != 0:
            return h.send_json({"ok": False, "error": out.strip()[-300:]},
                                  status=500)
        vcode, _ = spawn.board_cli(target, ["vpn", "serve"])
        # The assistant follows the course.
        acode, aout = spawn.tutor_cli(["agent", "start", match["repo"]])
        return h.send_json({"ok": True, "repo": match["repo"],
                               "address": vcode == 0,
                               "detail": out.strip(),
                               "agent": aout.strip() if acode == 0 else None,
                               "agent_error": None if acode == 0 else aout.strip()[-300:]})

    return NOT_MINE
