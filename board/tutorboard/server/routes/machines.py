"""What this machine can teach, and which course the one address opens.

Nothing here reaches the filesystem from a request: a course named in a
request is matched against what this server already discovered.

WHERE EACH IS SERVED (`handler.UNPREFIXED` is the table that serves them):

    atlas     unprefixed only, over every subject, by a sessionless Repo over
              the Atlas root; 404 under `/s/<id>/`:
              GET  /courses.json  /atlas.json  /relay.json
              POST /meeting  /default-agent
              POST /colibri  /switch
    session   under `/s/<id>/`: POST /seen (somebody is looking at this
              session's subject)
    both      GET /health: the session's, under `/s/<id>/`; unprefixed, the
              handler answers for the server

`/meeting` asks the Meetings subject's tutor, through
`library.ask_meeting`. The deck is read in the Meetings subject's
library (`/library?subject=projects/Meetings&doc=meeting`), and its ink and
feedback are that subject's.
"""

import json
import os
import time
import urllib.parse

from . import NOT_MINE
from ...net import tailscale
from ... import assistants
from ... import keys
from ... import limits
from ... import choice
from .. import spawn
from ... import subjects
from ... import colibri
from ... import relay
from ... import machines
from ... import briefs
from ... import stamp
from ...lesson import state
from ...course import repo as course_repo


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

    if path == "/relay.json":
        # THE CLUSTER'S HEALTH, AS THE MAC SEES IT: relay down, not synced,
        # the relay's own status, and Colibri with its panel's tasks
        # (`relay.health`). Everything about the cluster comes from
        # relay/status.json and this tree, never from Slurm (D27).
        return h.send_json(relay.panel(repo.root))

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
    # SOMEBODY IS LOOKING AT THIS SESSION, NOW. Only the page can say so: a
    # request arriving proves a browser is open, not that anybody reads it.
    if path == "/seen":
        # The session's own `seen`: the home screen's Continue row counts the
        # cards written after it as new.
        if getattr(repo, "stored", False):
            repo.set_state(seen=time.time())
        h.hub.worker.dirty.set()
        return h.send_json({"ok": True})

    if path == "/meeting":
        # THE MEETING DECK: `{since, items}`, `items` the subjects it covers
        # (none is every subject that moved). The brief is written and a
        # `[writeup]` turn asked in a session bound to projects/Meetings
        # (`library.ask_meeting`); the front door then watches the Meetings
        # library's record of it (`/library.json?subject=projects/Meetings`).
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
        # FILE A COLIBRI TASK: {brief, label?, session?}. The Mac starts no
        # server; it files a `colibri` relay request in libr-local-llm, the
        # way `board colibri` does (`colibri.ask`), and the relay's next pass
        # queues it and starts a generation where none is up.
        try:
            payload = json.loads(h.read_body().decode("utf-8") or "{}")
        except Exception:                                    # noqa: BLE001
            return h.send_json({"ok": False, "error": "bad json"}, status=400)
        if not isinstance(payload, dict):
            return h.send_json({"ok": False, "error": "bad json"}, status=400)
        if not str(payload.get("brief") or "").strip():
            return h.send_json({"ok": False, "error": "say what the task is"},
                               status=400)
        found = subjects.find(colibri.WORKSPACE, base=repo.root)
        if not found:
            return h.send_json({"ok": False, "error": "no %s here to file in"
                                % colibri.WORKSPACE}, status=404)
        got = colibri.ask(found["root"], payload.get("brief"),
                          label=str(payload.get("label") or "").strip(),
                          session=str(payload.get("session") or "").strip())
        now = colibri.status(repo.root)
        if not got["ok"]:
            return h.send_json({"ok": False, "id": got.get("id"),
                                "error": "; ".join(got["problems"]),
                                "colibri": now}, status=409)
        relay.forget()
        h.hub.worker.dirty.set()
        return h.send_json({"ok": True, "id": got["id"], "detail": got["said"],
                            "estimate": colibri.estimate(now), "colibri": now})

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
