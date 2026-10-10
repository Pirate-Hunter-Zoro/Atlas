"""The server's own routes: health, the relay panel, the meeting deck, the
provider setting, Colibri tasks and `/seen`.

WHERE EACH IS SERVED (`handler.UNPREFIXED` is the table that serves them):

    atlas     unprefixed only, over every subject, by a sessionless Repo over
              the Atlas root; 404 under `/s/<id>/`:
              GET  /relay.json
              POST /meeting  /default-agent  /colibri
    session   under `/s/<id>/`: POST /seen (somebody is looking at this
              session's subject)
    both      GET /health: the session's, under `/s/<id>/`; unprefixed, the
              handler answers for the server

`/meeting` asks the Meetings subject's tutor (`library.ask_meeting`); the
deck is read, inked and corrected in that subject's library.
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
from ... import subjects
from ... import colibri
from ... import relay
from ... import briefs
from ... import stamp
from ...lesson import state


def get(h, repo, path):
    if path == "/relay.json":
        # The cluster's health from relay/status.json and this tree, never
        # from Slurm (D27).
        return h.send_json(relay.panel(repo.root))

    if path == "/health":
        # `dir` and `id` name the session's subject; `limited` the machine's
        # allowance; `tutor` the session's agent state; `host` the machine.
        agent = state.load_agent(repo) or {}
        out = {"ok": True, "root": repo.root,
               "dir": os.path.basename(repo.root),
               # Qualified, so same-named subjects are told apart.
               "id": subjects.identify(repo.root),
               "host": tailscale.tailnet_self() or "",
               "tutor": agent.get("state") or None,
               "limited": limits.limited_until()}
        # `code=1` is opt-in, because the stamp is a git call and the hub
        # polls plain `/health`.
        want = urllib.parse.parse_qs(urllib.parse.urlparse(h.path or "").query)
        if "code" in want:
            out["code"] = {"running": stamp.LOADED, "tree": stamp.tree(),
                           "tutor": agent.get("code")}
        return h.send_json(out)
    return NOT_MINE


def post(h, repo, path):
    # Only the page can say somebody is looking.
    if path == "/seen":
        # The session's own `seen`: the home screen's Continue row counts the
        # cards written after it as new.
        if getattr(repo, "stored", False):
            repo.set_state(seen=time.time())
        h.hub.worker.dirty.set()
        return h.send_json({"ok": True})

    if path == "/meeting":
        # The meeting deck: `{since, items}` (no items: every subject that
        # moved), via `library.ask_meeting`.
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
        # The one provider setting: writes only `provider`, which the next
        # turn re-reads. Refused: unknown, unrunnable here, or in-fence. A
        # spent allowance is allowed; the fallback covers it.
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
        # Atomic: every turn reads this file.
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
        # A Colibri task, filed as a relay request (`colibri.ask`); the Mac
        # starts no server.
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

    return NOT_MINE
