"""The server's own routes: health, the sync health, the meeting deck, the
provider setting, `/seen` and a page's error report.

WHERE EACH IS SERVED (`handler.UNPREFIXED` is the table that serves them):

    atlas     unprefixed only, over every subject, by a sessionless Repo over
              the Atlas root; 404 under `/s/<id>/`:
              GET  /sync.json
              POST /meeting  /default-agent
    session   under `/s/<id>/`: POST /seen (somebody is looking at this
              session's subject)
    both      GET /health: the session's, under `/s/<id>/`; unprefixed, the
              handler answers for the server
              POST /client-error: one line in the server's log, the same
              under `/s/<id>/` and unprefixed

`/meeting` asks the Meetings subject's tutor (`library.ask_meeting`); the
deck is read, inked and corrected in that subject's library.
"""

import json
import os
import threading
import time
import urllib.parse

from . import NOT_MINE
from ...net import tailscale
from ... import assistants
from ... import keys
from ... import limits
from ... import subjects
from ... import sync
from ... import briefs
from ... import stamp
from ...lesson import state


def get(h, repo, path):
    if path == "/sync.json":
        # The Mac's sync health and the machine's brew and tools lines.
        return h.send_json(sync.health(repo.root))

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


# A page's error report: each field cut to this, the body refused over
# CLIENT_BODY, and at most CLIENT_PER_MINUTE lines a minute from this process,
# so a page failing in a loop cannot fill the log.
CLIENT_FIELD = 300
CLIENT_BODY = 8 * 1024
CLIENT_PER_MINUTE = 20
CLIENT_FIELDS = ("page", "what", "src", "msg", "stack", "ua")
_client = {"window": 0.0, "count": 0, "dropped": 0}
_client_lock = threading.Lock()


def _client_field(payload, name):
    """One field of a report, on one line and cut to CLIENT_FIELD; "-" for none.
    Every character that does not print (a control, an escape, a bidi
    override) is a space first, so a report cannot repaint the log's
    terminal."""
    said = payload.get(name)
    if said is None:
        return "-"
    said = "".join(c if c.isprintable() else " " for c in str(said))
    return " ".join(said.split())[:CLIENT_FIELD] or "-"


def client_error(h, now=None):
    """POST /client-error {page, what, src, msg, stack, ua}: what a page could
    not load or run, which no request line shows when a proxy dropped the
    request, written as one `client:` line through `h.note`. `{ok: true}` for
    any JSON object; past the rate the line is counted, not written."""
    try:
        length = int(h.headers.get("Content-Length") or 0)
    except (TypeError, ValueError):
        length = 0
    if length > CLIENT_BODY:
        # The body is unread; this connection carries nothing more.
        h.close_connection = True
        return h.send_json({"ok": False, "error": "a report is at most %d bytes"
                            % CLIENT_BODY}, status=413)
    try:
        payload = json.loads(h.read_body().decode("utf-8") or "{}")
    except (ValueError, UnicodeDecodeError):
        payload = None
    if not isinstance(payload, dict):
        return h.send_json({"ok": False, "error": "bad json"}, status=400)
    got = dict((k, _client_field(payload, k)) for k in CLIENT_FIELDS)
    line = "client: %(page)s %(what)s %(src)s %(msg)s" % got
    for extra in ("stack", "ua"):
        if got[extra] != "-":
            line += " | %s %s" % (extra, got[extra])
    now = time.time() if now is None else now
    with _client_lock:
        dropped = 0
        if now - _client["window"] >= 60:
            dropped = _client["dropped"]
            _client.update(window=now, count=0, dropped=0)
        _client["count"] += 1
        logged = _client["count"] <= CLIENT_PER_MINUTE
        if not logged:
            _client["dropped"] += 1
    if dropped:
        h.note("client: %d more report%s in the minute before this one went "
               "unlogged" % (dropped, "" if dropped == 1 else "s"))
    if logged:
        h.note(line)
    return h.send_json({"ok": True})


def post(h, repo, path):
    if path == "/client-error":
        return client_error(h)

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
            gone = recipes.missing_command(spec.get("cmd"))
            need = keys.unkeyed(spec)
            why = (gone and "`%s` is not installed here" % gone) or (
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

    return NOT_MINE
