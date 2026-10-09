"""What this machine can teach, and which course the one address opens.

Nothing here reaches the filesystem from a request: a course named in a
request is matched against what this server already discovered.

WHERE EACH IS SERVED (`handler.UNPREFIXED` is the table that serves them):

    atlas     unprefixed only, over every subject, by a sessionless Repo over
              the Atlas root; 404 under `/s/<id>/`:
              GET  /courses.json  /atlas.json  /news  /missions  /mission
              GET  /meeting/deck.json  /meeting/view  /meeting/pdf
              POST /meeting  /default-agent
              POST /colibri  /writeup/scopes  /elsewhere  /switch
    session   under `/s/<id>/`: POST /seen (somebody is looking at this
              session's subject)
    both      GET /health: the session's, under `/s/<id>/`; unprefixed, the
              handler answers for the server

`/meeting` and `/elsewhere` ask another subject's tutor, and each goes
through `registry.runner_route`. Ink on the deck is the Meetings subject's,
and so is feedback on it (`/library/feedback?subject=projects/Meetings`).
"""

import json
import os
import time
import urllib.parse

from . import NOT_MINE
from .. import registry
from ...net import tailscale
from ... import assistants
from ... import keys
from ... import limits
from ... import choice
from .. import spawn
from ... import subjects
from ... import colibri
from ... import machines
from ... import briefs
from ... import missions
from ... import news
from ... import progress
from ... import scopes
from ... import stamp
from ...course import config
from ...course import paper
from ...lesson import state
from ...course import repo as course_repo


def _deck_ink(repo, base):
    """`(ink, ink_repo)` for the meeting deck. Its ink is the Meetings
    subject's (`/annotate/save?subject=projects/Meetings`, the repo
    `/library/feedback` reads); ink saved at the Atlas root before it was
    loads in place under it."""
    root = briefs.meetings_root(base)
    meet = registry.sessionless(root, base) if root else repo
    ink = briefs.ink_keys(repo)
    if meet is not repo:
        ink.update(briefs.ink_keys(meet))
    return ink, meet


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
        #
        # `holders=1` IS THE ONE FIELD THAT IS ASKED FOR RATHER THAN SENT.
        # Which assistant is attached in each workspace is an `agent.json` per
        # workspace off a shared filer -- 37 ms against 0.4 ms for the whole
        # cached payload -- and the front door polls this route every 20
        # seconds while drawing none of it. The dispatch panel draws it and
        # asks for it; see `machines._mark_holder`.
        want = urllib.parse.parse_qs(urllib.parse.urlparse(h.path or "").query)
        return h.send_json(machines.atlas_payload(
            repo, holders=want.get("holders", [""])[0] == "1"))

    # THE DECK, AND THERE IS EXACTLY ONE OF IT: the artifact
    # projects/Meetings/docs/meeting/ (`briefs.py`). No name arrives from the
    # browser, so no name from a request can reach the filesystem here.
    if path == "/meeting/deck.json":
        # Being written, ready, or did not land: `briefs.judge`, which reads
        # `artifacts.status` and checks a built deck once against its sources.
        base = subjects.root() or repo.root
        rec = briefs.deck(base)
        if not rec:
            return h.send_json({"ok": False,
                                "detail": "No deck has been made yet."})
        return h.send_json({
            "ok": True, "state": rec["state"], "why": rec["why"],
            "since": rec["since"], "period": rec["period"], "at": rec["at"],
            "built": bool(rec["has_pdf"]), "host": rec["host"],
            "workspaces": rec["workspaces"], "names": rec["names"],
            "pages": rec["pages"], "unsupported": rec["unsupported"],
            "marked": sorted(_deck_ink(repo, base)[0]),
        })

    if path == "/meeting/view":
        # The library reader's rasteriser, cache and page addresses. Only a
        # READY deck is drawn.
        base = subjects.root() or repo.root
        rec = briefs.deck(base)
        if not rec or not rec.get("has_pdf"):
            deck_state = (rec or {}).get("state") or ""
            return h.send_json({
                "ok": False, "why": "none" if not rec else deck_state,
                "detail": ("There is no deck to read. Make one from the front "
                           "door." if not rec else
                           "The deck is being written in Meetings. This page "
                           "draws it when it is there."
                           if deck_state == "being written" else
                           (rec.get("why") or "The deck did not land."))})
        out = paper.pages_of(repo, rec["pdf"], briefs.STEM + ".pdf", "meeting")
        if out.get("ok"):
            # The marks come WITH the pages: this page opens no session.
            out["ink"], meet = _deck_ink(repo, base)
            out["build"], out["rebuilt"] = briefs.drawn_on(meet, rec["pdf"], out)
            out["deck"] = briefs.deck_id(base)
            out["pages_of"] = rec["pages"]
            out["workspaces"] = rec["workspaces"]
            out["names"] = rec["names"]
            out["since"] = rec["since"]
            out["period"] = rec["period"]
            prov = briefs.provenance(base)
            out["unsupported"] = {
                "numbers": prov.get("numbers") or [],
                "figures": prov.get("figures") or [],
                "internal": prov.get("internal") or []}
        return h.send_json(out)

    if path == "/meeting/pdf":
        rec = briefs.deck(subjects.root() or repo.root)
        if not rec or not rec.get("has_pdf"):
            return h.send_json({"ok": False, "error": "no deck"}, status=404)
        return h.send_file(rec["pdf"])

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

    if path == "/mission":
        # ONE MISSION, TAPPED. Asked for in these words: *"if I click on that
        # box that says 'A Mission is still going' I can see what has been going
        # on and been accomplished thus far."*
        #
        # `/missions` above is the list and it is pushed four times a second, so
        # nothing expensive may ride on it. This is a TAP: two `git` calls and a
        # directory walk, once, for the one mission somebody is looking at.
        #
        # NEITHER NAME REACHES THE FILESYSTEM. The workspace is matched against
        # what this server already discovered and the root comes off the match
        # -- the rule `/switch` and `/elsewhere` follow -- and the mission id is
        # matched against `missions.ID_RE`, which is a turn id and nothing else.
        want = urllib.parse.parse_qs(urllib.parse.urlparse(h.path or "").query)
        ws = (want.get("ws", [""])[0] or "").strip()
        mid = (want.get("id", [""])[0] or "").strip()
        match = None
        for c in machines.workspaces(repo):
            if ws in (c["repo"], c["id"]):
                match = c
                break
        if not match or not missions.ID_RE.match(mid):
            return h.send_json({"ok": False, "detail": "unknown mission"},
                               status=404)
        rec = next((m for m in missions.of(match["root"])
                    if str(m.get("id")) == mid), None)
        if not rec:
            return h.send_json({"ok": False, "detail": "unknown mission"},
                               status=404)
        out = progress.of(match["root"], rec,
                          working=missions.mid_turn(match["root"]))
        out["ok"] = True
        out["ws"] = match["id"]
        out["repo"] = match["repo"]
        out["course"] = news.course_name(match["root"]) or match["repo"]
        return h.send_json(out)

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
        out = {"ok": True, "root": repo.root,
               "dir": os.path.basename(repo.root),
               # The qualified name too, so a caller can tell
               # `courses/Probability` from a future
               # `projects/Probability` without guessing.
               "id": subjects.identify(repo.root),
               "host": tailscale.tailnet_self() or "",
               "chosen": machines.chosen_target(),
               "tutor": agent.get("state") or None,
               "limited": limits.limited_until()}
        # `code=1` IS ASKED FOR, NOT SENT: the hub and the board poll plain
        # `/health`, and the tree's stamp is a git call. The trace panel asks,
        # so a process older than the tree is visible from the glass.
        want = urllib.parse.parse_qs(urllib.parse.urlparse(h.path or "").query)
        if "code" in want:
            out["code"] = {"running": stamp.LOADED, "tree": stamp.tree(),
                           "tutor": agent.get("code")}
        return h.send_json(out)
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
        # The session's own `seen`: the home screen counts the cards written
        # after it as new.
        if getattr(repo, "stored", False):
            repo.set_state(seen=time.time())
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
        h.hub.worker.dirty.set()
        return h.send_json({"ok": True})

    if path == "/meeting":
        # THE MEETING DECK: `{since, items}`, `items` the subjects it covers
        # (none is every subject that moved). The brief is written and a
        # `[writeup]` turn asked in a session bound to projects/Meetings
        # (`library.ask_meeting`); the page then watches `/meeting/deck.json`.
        try:
            payload = json.loads(h.read_body().decode("utf-8") or "{}")
        except Exception:                                    # noqa: BLE001
            return h.send_json({"ok": False, "detail": "bad json"}, status=400)
        if not isinstance(payload, dict):
            payload = {}
        base = subjects.root() or repo.root
        when, said = briefs.resolve_since(payload.get("since") or "", base)
        if when is None:
            return h.send_json({"ok": False, "detail": said}, status=400)
        items = payload.get("items")
        items = [str(w) for w in items if isinstance(w, str) and w.strip()][:200] \
            if isinstance(items, list) else []
        from . import library as library_route         # local: a cycle
        try:
            return library_route.meeting_deck(h, repo, base, when, said,
                                              want=items or None)
        except Exception as exc:                             # noqa: BLE001
            return h.send_json({"ok": False,
                                "detail": str(exc)[-300:]}, status=500)

    if path == "/default-agent":
        # THE ONE PROVIDER SETTING, SET FROM THE FRONT DOOR: `provider` in this
        # machine's config, and nothing else in that file. Every turn re-reads
        # the config (`loop.for_this_turn`), so the next turn of every session
        # takes it with nothing restarted. Refused: an unknown name, one this
        # machine cannot run (binary or key missing), and an in-fence model,
        # because only it reads phi and it never takes a turn here. An
        # allowance that has run out is not refused: the fallback covers it.
        from ...agents import recipes
        try:
            payload = json.loads(h.read_body().decode("utf-8") or "{}")
        except (ValueError, UnicodeDecodeError):
            return h.send_json({"ok": False, "detail": "bad request"}, status=400)
        want = str((payload or {}).get("agent") or "").strip()
        cfg = recipes.load_config()
        spec = (cfg.get("agents") or {}).get(want)
        why = None
        if not isinstance(spec, dict):
            why = "'%s' is not an assistant on this machine" % want
        else:
            why = recipes.in_fence(cfg, want)
            gone = recipes.missing_command(spec.get("cmd"))
            need = keys.unkeyed(spec)
            why = why or (gone and "`%s` is not installed here" % gone) or (
                need and "%s is not in %s" % (need, keys.store()))
        if why:
            return h.send_json({"ok": False, "detail": why}, status=400)
        try:
            with open(recipes.CONFIG, "r", encoding="utf-8") as fh:
                on_disk = json.load(fh) or {}
        except (OSError, ValueError):
            on_disk = {}
        on_disk["provider"] = want
        on_disk.pop("default_agent", None)
        # Atomically: every turn reads this file, and a half-written one
        # takes the tutor out.
        os.makedirs(os.path.dirname(recipes.CONFIG), exist_ok=True)
        tmp = recipes.CONFIG + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(on_disk, fh, indent=2)
                fh.write("\n")
            os.replace(tmp, recipes.CONFIG)
        except OSError as exc:
            return h.send_json({"ok": False, "detail": str(exc)}, status=500)
        assistants.forget()
        h.hub.worker.dirty.set()
        table = assistants.listing()
        return h.send_json({"ok": True, "default": want,
                            "machine": (table or {}).get("machine"),
                            "why": (table or {}).get("why"),
                            "assistants": table})

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
        h.hub.worker.dirty.set()
        return h.send_json({"ok": True, "started": started, "detail": said,
                            "colibri": colibri.status(fresh=True)})

    if path == "/writeup/scopes":
        # WHAT A DOCUMENT IN ANOTHER WORKSPACE COULD BE ABOUT.
        #
        # Asked for in these words: *"the ability to write a paper or a slide
        # deck should just be an option on the homescreen, and from there I want
        # to be able to specify which projects/course, and which
        # sections/results."* The front door is the one surface with no sitting
        # behind it, so the second half of that sentence cannot be answered from
        # a board -- it is answered from what discovery found in the workspace
        # being named, which is `tutorboard/scopes.py`.
        #
        # IT IS IN THIS FILE BECAUSE IT READS A WORKSPACE THAT IS NOT THIS ONE,
        # and that is exactly what this file is for. The resolution is
        # `/elsewhere`'s and `/switch`'s, unchanged: matched against what the
        # walk found, with the ROOT taken off the match rather than rebuilt out
        # of the name, because the same name can sit under two families.
        try:
            payload = json.loads(h.read_body().decode("utf-8") or "{}")
        except Exception:                                    # noqa: BLE001
            return h.send_json({"ok": False, "error": "bad json"}, status=400)
        want = payload.get("repo") or ""
        match = None
        for c in machines.workspaces(repo):
            if want in (c["repo"], c["id"]):
                match = c
                break
        if not match:
            return h.send_json({"ok": False, "error": "unknown workspace"},
                               status=404)
        # THE `about` SENTENCE IS NOT SENT. It is the instruction the assistant
        # is given, and a browser that holds it is a browser that can edit it --
        # at which point the key is decoration and the front door is a text box
        # wearing buttons. What comes back is a key, and `POST /writeup`
        # resolves it against this same list.
        offered, more = scopes.offered(match["root"])
        return h.send_json({
            "ok": True, "repo": match["repo"], "id": match["id"],
            "name": match["course"] or match["repo"],
            # AND WHAT IS NOT ON THE LIST. A picker that stops at a cap and says
            # nothing reads as *this is all there is*, and the one thing that
            # cannot be asked for is then the one nobody knows to ask about.
            "more": more,
            "scopes": [{"key": s["key"], "label": s["label"], "what": s["what"]}
                       for s in offered]})

    if path == "/elsewhere":
        # PUT AN ASSISTANT TO WORK IN A WORKSPACE YOU ARE NOT LOOKING AT.
        #
        # Asked for almost word for word: *"I want to be able to go into a
        # different section of a project, or a different project completely, and
        # put other agents to work on other things while the first one is
        # working."* `machines.workspaces` is the list, `runner_route` queues
        # the turn in that subject's session, and `news.elsewhere` is how you
        # are told it landed.
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
        # NOTHING IS STARTED OR STOPPED OVER THERE. The task is queued on the
        # runner in the session `runner_route` picks, and the subject's provider
        # writes it; a named assistant is kept on the mission record only.
        stopped = ""
        said = ""

        # The task goes in as a turn of theirs, because that is what it is: they
        # asked for it, and a transcript over there that opens with the answer
        # reads as an assistant that decided to do this on its own. It goes
        # through `runner_route`, which picks the session on that subject.
        record = {
            "kind": "text", "answers": None,
            "t": time.time(),
            "iso": time.strftime("%Y-%m-%d %H:%M:%S"),
            "from": "student", "text": task, "signal": None, "read": False,
        }

        # AND THE MISSION IS A RECORD, IN THE WORKSPACE IT IS ABOUT.
        #
        # Asked for in these words: *"just because I close the iPad doesn't mean
        # that should end. Next time I open the iPad and access the board, that
        # mission should still be going or notify me somewhere if it's done."*
        # The daemon already survived the lid; nothing said it had. Written
        # after the start was allowed and the task is on disk, because a record
        # of a mission that was refused is a row about work nobody is doing --
        # and BEFORE the inbox line, because that line is what wakes the daemon
        # and `board brief` reads this record to know the turn is a doing one.
        #
        # `ship` is carried here and honoured when the mission ENDS -- see
        # `missions.py` -- because the record is written once and read by that
        # turn later. `done` only: a mission that failed may well have left
        # changes in the tree, and pushing those is the opposite of what the
        # switch means to whoever set it going.
        ceiling = 0.0
        if agent == "colibri":
            # THE ONE ASSISTANT WITH A CEILING. A colibrì turn runs inside the
            # serve job's allocation, so the mission cannot outlive that job's
            # walltime -- and until this nothing anywhere said what it was.
            left = (colibri.status() or {}).get("left")
            if left:
                ceiling = time.time() + float(left)
        # A dispatch starts no assistant, so it brings none for the mission's
        # end to release.
        brought = ""
        made = {}

        def mission(target, tid):
            made["rec"] = missions.dispatch(
                match["root"], task=task, turn=tid, agent=agent,
                ship=bool(payload.get("ship")), frm=subjects.identify(repo.root),
                ceiling=ceiling, brought=brought)

        # AND NOW THE TURN AND THE INBOX LINE, WHICH IS THE WAKING, after the
        # mission record: everything the woken turn reads about itself is on
        # disk before it lands. The line is their words and nothing else: what
        # kind of turn this is comes out of `board brief`.
        try:
            got = registry.runner_route(match["id"], record, turn=True,
                                        base=registry.base_of(repo),
                                        ask=task[:60], before=mission)
        except (LookupError, OSError) as exc:
            return h.send_json({"ok": False, "repo": match["repo"], "agent": agent,
                                "error": "nothing could be asked: %s" % exc},
                               status=500)
        tid, rec = got["id"], made["rec"]
        missions.forget()
        h.hub.worker.dirty.set()
        # WHAT IT DID, IN ONE SENTENCE, ON THE GLASS. A swap that happens
        # silently in a workspace nobody is looking at is worse than one that is
        # announced: the assistant that was there is gone and the only person
        # who could have known is the one who tapped.
        if stopped:
            said = ("'%s' was stopped in %s and '%s' has it now."
                    % (stopped, match["repo"], agent))
        return h.send_json({"ok": True, "repo": match["repo"],
                            "agent": agent, "turn": tid, "detail": said,
                            "stopped": stopped, "session": got["session"],
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
        vcode, vout = spawn.board_cli(target, ["vpn", "serve"])
        # The assistant follows the course -- unless all that was asked for is
        # its MAP. A map needs a board serving, not a tutor: the tap on a box
        # that opens a sitting wakes one (`_begin` in `routes/lesson.py`), and
        # an assistant started for somebody who only looked is a process, a
        # login and an allowance spent on nothing.
        acode, aout = 0, ""
        if payload.get("agent", True) is not False:
            acode, aout = spawn.tutor_cli(["agent", "start", match["repo"]])
        # WHERE THE OPENED BOARD ANSWERS, for a page that is not on the address.
        # A page loaded off a board's own port -- `http://<name>:8937/` -- sees
        # that board whatever the address points at, so re-pointing the address
        # is invisible to it and its poll of its own `/health` never lands.
        # Given the port and the name, it can go there instead.
        port = None
        try:
            with open(course_repo.session_path(target, ".board.json"), "r",
                      encoding="utf-8") as fh:
                port = int(json.load(fh).get("port"))
        except (OSError, ValueError, TypeError):
            pass
        return h.send_json({"ok": True, "repo": match["repo"],
                               "address": vcode == 0,
                               "address_error": None if vcode == 0
                               else vout.strip()[-300:],
                               "host": tailscale.tailnet_self() or "",
                               "port": port,
                               "detail": out.strip(),
                               "agent": (aout.strip() or None) if acode == 0 else None,
                               "agent_error": None if acode == 0 else aout.strip()[-300:]})

    return NOT_MINE
