"""The HTTP handler: headers, bodies, the event stream, and a table of routes.

Routes live in `routes/` by family; this keeps the plumbing they share and
the order they are asked in.
"""

import sys
import gzip
import json
import mimetypes
import os
import re
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler

from .. import cluster, paths, sessions, subjects
from ..course import paper
from .. import stamp as code_stamp
from . import routes
from .routes import (library, lesson, machines, pages, saving, taking,   # noqa: F401
                     writing)

WEB = paths.WEB

# A stream with nothing to say pings this often; a client gone is noticed then.
PING_SECONDS = 15.0

SESSION_PREFIX = re.compile(r"\A/s/([^/]+)(/.*)?\Z")
ICON = re.compile(r"\A/(apple-touch-icon|icon-\d+)\.png\Z")

# Every route served without a `/s/<id>` prefix, and how; anything else
# unprefixed is 404. A trailing `*` is a prefix. `subject`: `?subject=<id>`
# picks the subject (a sessionless Repo); under `/s/<id>/` the session's own.
# `subject?`: no `?subject=` means the Atlas root. `atlas`: cross-subject,
# unprefixed only. Asks of another subject's tutor go through
# `registry.runner_route`.
UNPREFIXED = (
    ("GET", "/", "home"),
    ("GET", "/index.html", "home"),
    ("GET", "/home", "home"),
    ("GET", "/static/*", "pages"),
    ("GET", "/sw.js", "pages"),
    ("GET", "/manifest.webmanifest", "pages"),
    ("GET", "/apple-touch-icon.png", "icon"),
    ("GET", "/icon-*", "icon"),
    ("GET", "/health", "health"),
    ("GET", "/sessions.json", "sessions"),
    ("POST", "/sessions/new", "new"),
    ("GET", "/subjects.json", "subjects"),
    ("POST", "/subjects/new", "subject-new"),
    ("POST", "/subject/delete", "subject-delete"),
    ("POST", "/session/delete", "session-delete"),
    ("GET", "/notices.json", "notices"),
    ("GET", "/assistants.json", "assistants"),
    ("GET", "/library", "page"),
    ("GET", "/library/", "page"),
    # library
    ("GET", "/library.json", "subject"),
    ("GET", "/library/stamp", "subject"),
    ("GET", "/library/results.json", "subject"),
    ("GET", "/library/table/*", "subject"),
    ("GET", "/library/view/*", "subject"),
    ("GET", "/library/note/*", "subject"),
    ("GET", "/library/ledger/*", "subject"),
    ("GET", "/library/evidence/*", "subject"),
    ("POST", "/library/ledger/*", "subject"),
    ("POST", "/library/feedback", "subject"),
    ("GET", "/library/marked/*", "subject"),
    ("POST", "/annotate/burn", "subject"),
    ("POST", "/doc/delete", "subject"),
    ("POST", "/artifact", "subject"),
    ("GET", "/materials.json", "subject"),
    ("POST", "/material/delete", "subject"),
    # pages
    ("GET", "/result/*", "subject"),
    ("GET", "/source/*", "subject?"),
    # machines
    ("GET", "/relay.json", "atlas"),
    ("POST", "/meeting", "atlas"),
    ("POST", "/default-agent", "atlas"),
    ("POST", "/colibri", "atlas"),
    # Rendered PDF pages: one cache for every session (`course/paper.py`).
    ("GET", "/paper/*", "paper"),
    # writing
    ("POST", "/annotate/save", "subject?"),
)

# An ended session is read-only: anything that would talk to its tutor or
# change it is 409; End (a retried commit), /poke, /seen and reads still
# answer. A cluster report reopens it (`sessions.reopen`).
ENDED_REFUSES = ("/say", "/slate/save", "/text/save", "/handover", "/session",
                 "/mode", "/bind", "/upload", "/file", "/annotate/save",
                 "/annotate/burn", "/artifact")

# The route classes UNPREFIXED names. A cross-subject one is 404 under
# `/s/<id>/`.
SUBJECT_CLASSES = ("subject", "subject?")
CROSS = "atlas"
NOT_IN_SESSION = (CROSS,)


def unprefixed_route(method, path):
    """How UNPREFIXED answers `method path`, or None."""
    for want, pattern, how in UNPREFIXED:
        if want != method:
            continue
        if pattern.endswith("*"):
            if path.startswith(pattern[:-1]) and len(path) > len(pattern) - 1:
                if how == "icon" and not ICON.match(path):
                    continue
                return how
        elif path == pattern:
            return how
    return None


class _Idle(object):
    """The hub of an unprefixed request, which has no session: a dirty mark
    with nobody to tell."""

    class worker(object):
        dirty = threading.Event()

mimetypes.add_type("font/woff2", ".woff2")
mimetypes.add_type("font/woff", ".woff")
mimetypes.add_type("application/manifest+json", ".webmanifest")


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "mathboard"

    def log_message(self, fmt, *args):
        pass

    # A narrow request log: every failure, but not the poll or the stream,
    # which would bury the one line anybody wants.
    QUIET_GET = re.compile(
        r"^/(events|board\.json|courses\.json|health|static/|figure/|"
        r"icon-\d+\.png|apple-touch-icon\.png|manifest\.webmanifest|sw\.js|"
        r"slate/(page-|state)|answers/|uploads/|notes/|favicon|"
        r"library/(view/|stamp))")

    def log_request(self, code="-", size="-"):
        try:
            status = int(code)
        except (TypeError, ValueError):
            status = 0
        path = (self.path or "").split("?", 1)[0]
        inner = SESSION_PREFIX.match(path)
        inner = (inner.group(2) or "/") if inner else path
        if self.command == "GET" and status < 400 and self.QUIET_GET.match(inner):
            return
        length = ""
        try:
            n = int((self.headers or {}).get("Content-Length") or 0)
            if n:
                length = " %d bytes in" % n
        except (TypeError, ValueError):
            pass
        self.note("%s %s -> %s%s" % (self.command, path, code, length))

    def note(self, line):
        """One timestamped line into board.log, which is this process's stderr."""
        try:
            sys.stderr.write("[%s] %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), line))
            sys.stderr.flush()
        except (OSError, ValueError):
            pass

    # -- helpers ---------------------------------------------------------
    # Text assets go gzipped when accepted (board.js is large over Tailscale),
    # compressed once per (path, mtime).
    GZIP_TYPES = ("text/html", "text/css", "text/javascript", "application/javascript",
                  "application/x-javascript")
    _gzipped = {}

    def accepts_gzip(self):
        for part in ((self.headers or {}).get("Accept-Encoding") or "").split(","):
            bits = [b.strip() for b in part.split(";")]
            if bits[0].lower() != "gzip":
                continue
            for b in bits[1:]:
                if b.replace(" ", "").startswith("q="):
                    try:
                        return float(b.split("=", 1)[1]) > 0
                    except ValueError:
                        return False
            return True
        return False

    def gzipped(self, data, gzip_key):
        slot, stamp = gzip_key
        held = self._gzipped.get(slot)
        if held and held[0] == stamp:
            return held[1]
        packed = gzip.compress(data, compresslevel=9, mtime=0)
        self._gzipped[slot] = (stamp, packed)
        return packed

    def send_bytes(self, data, ctype, cache=False, status=200, nosniff=False, extra=None,
                   gzip_key=None):
        """`gzip_key` is (slot, stamp): set, a text asset may go out gzipped."""
        compressible = (gzip_key is not None
                        and ctype.split(";")[0].strip().lower() in self.GZIP_TYPES)
        packed = compressible and self.accepts_gzip()
        if packed:
            data = self.gzipped(data, gzip_key)
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        if compressible:
            # Either body can go out at this URL, so a cache keys on what was asked.
            self.send_header("Vary", "Accept-Encoding")
        if packed:
            self.send_header("Content-Encoding", "gzip")
        if nosniff:
            self.send_header("X-Content-Type-Options", "nosniff")
        if extra:
            self.send_header(extra[0], extra[1])
        if cache:
            self.send_header("Cache-Control", "public, max-age=86400")
        else:
            # The shell is never held by the browser, so a fix always arrives.
            self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if getattr(self, "head_only", False):
            return
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def send_json(self, obj, status=200):
        self.send_bytes(json.dumps(obj).encode("utf-8"), "application/json", status=status)

    # Inline-safe types for uploads; anything else downloads, since uploaded
    # .html or .svg would run script on this origin.
    INLINE_OK = {"image/png", "image/jpeg", "image/gif", "image/webp", "application/pdf"}

    def send_file(self, path, cache=False, untrusted=False, download=None):
        """`download` is a filename: save this rather than show it, so an iPad
        gets the share sheet instead of an inline preview."""
        if not os.path.isfile(path):
            self.send_bytes(b"not found", "text/plain", status=404)
            return
        ctype = mimetypes.guess_type(path)[0] or "application/octet-stream"
        if path.endswith(".svg") and not untrusted:
            ctype = "image/svg+xml"
        extra = None
        if download:
            extra = ("Content-Disposition",
                     'attachment; filename="%s"' % download)
        elif untrusted and ctype not in self.INLINE_OK:
            ctype = "application/octet-stream"
            extra = ("Content-Disposition",
                     'attachment; filename="%s"' % os.path.basename(path))
        gzip_key = None
        st = os.stat(path)
        if not untrusted and not download:
            gzip_key = (path, (st.st_mtime_ns, st.st_size))
        if st.st_size > self.STREAM_OVER and gzip_key is None:
            return self.stream_file(path, st.st_size, ctype, cache, untrusted, extra)
        with open(path, "rb") as fh:
            self.send_bytes(fh.read(), ctype, cache=cache, nosniff=untrusted, extra=extra,
                            gzip_key=gzip_key)

    # A file bigger than this (an upload, a material) goes out a chunk at a
    # time rather than read whole into memory.
    STREAM_OVER = 8 * 1024 * 1024

    def stream_file(self, path, size, ctype, cache, nosniff, extra):
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(size))
        if nosniff:
            self.send_header("X-Content-Type-Options", "nosniff")
        if extra:
            self.send_header(extra[0], extra[1])
        self.send_header("Cache-Control", "public, max-age=86400" if cache
                         else "no-store")
        self.end_headers()
        if getattr(self, "head_only", False):
            return
        try:
            with open(path, "rb") as fh:
                while True:
                    chunk = fh.read(1 << 16)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass

    MAX_BODY = 64 * 1024 * 1024   # a slate page is ~200 KB; this is generous

    def read_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length > self.MAX_BODY:
            raise ValueError("body too large")
        buf = b""
        while len(buf) < length:
            chunk = self.rfile.read(min(65536, length - len(buf)))
            if not chunk:
                break
            buf += chunk
        return buf

    # -- routing ---------------------------------------------------------
    # With a `registry`, `/s/<id>/...` goes to that session's Repo and Hub with
    # the prefix stripped, and unprefixed requests only where UNPREFIXED lists
    # them. A test server with `repo` and `hub` serves one session unprefixed.
    def _scope(self):
        """`(path, query)` of this request, with `self.repo` and `self.hub`
        set to the session it is for. None after a 404 was sent."""
        parsed = urllib.parse.urlparse(self.path)
        path = urllib.parse.unquote(parsed.path)
        query = urllib.parse.parse_qs(parsed.query)
        registry = getattr(self.server, "registry", None)
        if registry is None:
            self.repo = self.server.repo
            self.hub = self.server.hub
            return path, query
        m = SESSION_PREFIX.match(path)
        if not m:
            self.repo = self.hub = None
            return path, query
        entry = registry.get(m.group(1))
        if entry is None:
            self.send_json({"ok": False, "error": "no such session"}, status=404)
            return None
        self.repo, self.hub = entry.repo, entry.hub
        return m.group(2) or "/", query

    def do_GET(self):
        scoped = self._scope()
        if scoped is None:
            return None
        path, query = scoped
        if self.repo is None:
            return self.unprefixed("GET", path, query)
        if getattr(self.server, "registry", None):
            if path in ("/", "/board", "/board/"):
                return self.send_file(os.path.join(WEB, "board.html"))
            if unprefixed_route("GET", path) in NOT_IN_SESSION:
                return self.not_in_session(path)
        return self.session_get(self.repo, path)

    def session_get(self, repo, path):
        if path in ("/", "/index.html", "/home"):
            return self.send_file(os.path.join(WEB, "home.html"))
        if path in ("/board", "/board/"):
            return self.send_file(os.path.join(WEB, "board.html"))

        # Installable-app files must sit at the root: the service worker's scope
        # is its own directory, and iOS looks for /apple-touch-icon.png.
        if ICON.match(path):
            return self.send_file(os.path.join(WEB, os.path.basename(path)), cache=True)
        if path in ("/slate", "/slate/"):
            return self.send_file(os.path.join(WEB, "slate.html"))
        # A page of its own, so feedback never touches the lesson.
        if path in ("/library", "/library/"):
            return self.send_file(os.path.join(WEB, "library.html"))
        if re.match(r"^/slate/page-\d+\.png$", path):
            return self.send_file(os.path.join(repo.slate, os.path.basename(path)))

        for mod in (routes.pages, routes.taking, routes.library, routes.lesson,
                    routes.writing, routes.machines):
            answered = mod.get(self, repo, path)
            if answered is not routes.NOT_MINE:
                return answered
        return self.send_bytes(b"not found", "text/plain", status=404)

    def do_HEAD(self):
        """Same routing as GET, headers only. Health checks and proxies use it."""
        self.head_only = True
        try:
            self.do_GET()
        finally:
            self.head_only = False

    def do_POST(self):
        scoped = self._scope()
        if scoped is None:
            return None
        path, query = scoped
        if self.repo is None:
            return self.unprefixed("POST", path, query)
        if (getattr(self.server, "registry", None)
                and unprefixed_route("POST", path) in NOT_IN_SESSION):
            return self.not_in_session(path)
        return self.session_post(self.repo, path)

    def not_in_session(self, path):
        """A cross-subject route asked for under `/s/<id>/`: it is served
        unprefixed only."""
        return self.send_json({"ok": False, "error": "%s is served outside a "
                               "session, without /s/<id>" % path}, status=404)

    def session_post(self, repo, path):
        if (path in ENDED_REFUSES and getattr(repo, "stored", False)
                and repo.state().get("ended")):
            # The body is unread; this connection carries nothing more.
            self.close_connection = True
            return self.send_json({"ok": False, "error": "this session has ended "
                                   "and is read-only"}, status=409)
        # A pull can remove a directory under a running server
        # (`Repo.ensure_dirs`).
        repo.ensure_dirs()
        return self.post_routes(repo, path)

    def post_routes(self, repo, path):
        for mod in (routes.saving, routes.library, routes.lesson, routes.writing,
                    routes.machines):
            answered = mod.post(self, repo, path)
            if answered is not routes.NOT_MINE:
                return answered
        # The body is unread; this connection carries nothing more.
        self.close_connection = True
        return self.send_bytes(b"not found", "text/plain", status=404)

    # -- unprefixed ------------------------------------------------------
    def unprefixed(self, method, path, query):
        """Answer a request outside `/s/<id>/` that UNPREFIXED lists; 404
        for anything else."""
        how = unprefixed_route(method, path)
        if how is None:
            self.close_connection = True
            return self.send_json({"ok": False, "error": "not found"}, status=404)
        registry = self.server.registry
        if how == "home":
            return self.send_file(os.path.join(WEB, "home.html"))
        if how == "page":
            return self.send_file(os.path.join(WEB, "library.html"))
        if how == "icon":
            return self.send_file(os.path.join(WEB, os.path.basename(path)), cache=True)
        if how == "pages":
            return routes.pages.get(self, None, path)
        if how == "paper":
            target = paper.page_file(os.path.basename(path))
            if not target:
                return self.send_json({"ok": False, "error": "not found"}, status=404)
            return self.send_file(target, cache=True)
        if how == "health":
            out = {"ok": True, "atlas": registry.atlas, "serving": registry.loaded()}
            from ..runner import service as runner
            if runner.RUNNER is not None:
                out["turns"] = runner.RUNNER.state()
            if "code" in query:
                out["code"] = {"running": code_stamp.LOADED, "tree": code_stamp.tree()}
            return self.send_json(out)
        if how == "sessions":
            return self.send_json(self.session_listing(registry))
        if how == "new":
            return self.new_session(registry)
        if how == "subjects":
            return self.send_json({"ok": True, "subjects": [
                {k: one[k] for k in ("id", "kind", "slug", "name")}
                for one in subjects.all(registry.atlas)]})
        if how == "subject-new":
            return self.new_subject(registry)
        if how == "subject-delete":
            return self.delete_subject(registry)
        if how == "session-delete":
            return self.delete_session(registry)
        if how == "notices":
            # Cluster lines no session took (D16), newest first; no turn ran.
            return self.send_json({"ok": True,
                                   "notices": cluster.notices(registry.atlas)})
        if how == "assistants":
            # The home screen's default-assistant setting: what POST
            # /default-agent chooses among. None when it could not be asked.
            from .. import assistants
            return self.send_json({"ok": True, "assistants": assistants.listing()})
        if how in SUBJECT_CLASSES:
            ident = (query.get("subject") or [""])[0]
            if ident:
                repo = registry.subject(ident)
                if repo is None:
                    return self.send_json({"ok": False, "error": "no such subject"},
                                          status=404)
            elif how == "subject?":
                repo = registry.atlas_repo()
            else:
                return self.send_json({"ok": False,
                                       "error": "name the subject: ?subject=<id>"},
                                      status=400)
        else:
            # how == CROSS
            repo = registry.atlas_repo()
        # A sessionless Repo: nothing here may be made under it, so the
        # directories `session_post` re-asserts are not.
        self.repo, self.hub = repo, _Idle()
        if method == "POST":
            return self.post_routes(repo, path)
        return self.session_get(repo, path)

    def new_session(self, registry):
        """POST /sessions/new {title?, view?}: an unbound session in teach,
        titled by the optional `title`; `view: "slate"` makes a notes canvas.
        Its record and the URL it opens at: its board, or its slate."""
        try:
            body = self.read_body()
            payload = json.loads(body.decode("utf-8")) if body.strip() else {}
        except (ValueError, UnicodeDecodeError):
            return self.send_json({"ok": False, "error": "bad json"}, status=400)
        if not isinstance(payload, dict):
            payload = {}
        title = payload.get("title")
        title = str(title).strip()[:200] if title else None
        try:
            rec = sessions.new(title, base=registry.atlas,
                               view=payload.get("view") or "board")
        except sessions.Refused as exc:
            return self.send_json({"ok": False, "error": str(exc)}, status=400)
        self.note("session %s opened" % rec["id"])
        return self.send_json({"ok": True, "id": rec["id"], "session": rec,
                               "url": sessions.url(rec)})

    @staticmethod
    def session_listing(registry):
        """GET /sessions.json: every session, newest first, each with the
        URL it opens at (`sessions.url`) and its subject's name; an open one also with its newest
        card and the count of cards since `seen` (`sessions.summary`)."""
        names = {one["id"]: one["name"] for one in subjects.all(registry.atlas)}
        out = []
        for rec in sessions.all(registry.atlas):
            one = dict(rec, url=sessions.url(rec),
                       subject_name=names.get(rec.get("subject")) or None)
            if not rec.get("ended"):
                one.update(sessions.summary(rec, registry.atlas))
            out.append(one)
        return {"ok": True, "sessions": out}

    def new_subject(self, registry):
        """POST /subjects/new {kind: course|project, name, phi}: make the
        subject and commit it (`subjects.create`). A project needs `phi`
        answered; a refusal is 400 in `subjects.create`'s own words."""
        try:
            body = self.read_body()
            payload = json.loads(body.decode("utf-8")) if body.strip() else {}
        except (ValueError, UnicodeDecodeError):
            return self.send_json({"ok": False, "error": "bad json"}, status=400)
        if not isinstance(payload, dict):
            return self.send_json({"ok": False, "error": "bad json"}, status=400)
        parent = {"course": "courses", "project": "projects"}.get(payload.get("kind"))
        name = str(payload.get("name") or "").strip()
        if not parent:
            return self.send_json({"ok": False,
                                   "error": "kind is course or project"}, status=400)
        if "/" in name or "\\" in name:
            return self.send_json({"ok": False,
                                   "error": "a name has no slash in it"}, status=400)
        phi = payload.get("phi")
        if phi is not None and not isinstance(phi, bool):
            return self.send_json({"ok": False,
                                   "error": "phi is true or false"}, status=400)
        try:
            made, ok, said = subjects.create("%s/%s" % (parent, name), phi=phi,
                                             base=registry.atlas)
        except subjects.Refused as exc:
            return self.send_json({"ok": False, "error": str(exc)}, status=400)
        if not ok:
            return self.send_json({"ok": False,
                                   "error": "not committed, so not made: %s" % said},
                                  status=500)
        self.note("subject %s made" % made["id"])
        return self.send_json({"ok": True, "said": said, "subject": {
            k: made[k] for k in ("id", "kind", "slug", "name")}})

    def _payload(self):
        """The JSON object of a small POST body, or None after a 400."""
        try:
            body = self.read_body()
            payload = json.loads(body.decode("utf-8")) if body.strip() else {}
        except (ValueError, UnicodeDecodeError):
            payload = None
        if not isinstance(payload, dict):
            self.send_json({"ok": False, "error": "bad json"}, status=400)
            return None
        return payload

    def delete_subject(self, registry):
        """POST /subject/delete {subject, typed}: `subjects.delete`. 400 for a
        subject that is none or a typed name that is not its slug; 409, with
        the reason, for D23 (`"phi": false` literally at HEAD) and for an open
        session, a coding session or an outstanding request on it."""
        payload = self._payload()
        if payload is None:
            return None
        ident = str(payload.get("subject") or "").strip()
        try:
            _where, said = subjects.delete(ident, payload.get("typed"),
                                           base=registry.atlas)
        except subjects.Busy as exc:
            return self.send_json({"ok": False, "error": str(exc)}, status=409)
        except subjects.Refused as exc:
            return self.send_json({"ok": False, "error": str(exc)}, status=400)
        self.note("subject %s deleted" % ident)
        return self.send_json({"ok": True, "subject": ident, "said": said})

    def delete_session(self, registry):
        """POST /session/delete {id}: the session to the trash
        (`sessions.delete`), and out of the registry. 409 while a turn of it
        runs or waits."""
        payload = self._payload()
        if payload is None:
            return None
        sid = str(payload.get("id") or "").strip()
        if not sessions.path(sid, registry.atlas):
            return self.send_json({"ok": False, "error": "no such session"},
                                  status=404)
        from ..runner import service as runner
        if runner.RUNNER is not None and runner.RUNNER.busy(sid):
            return self.send_json({"ok": False, "error": "a turn of this "
                                   "session is running or waiting; delete it "
                                   "once that is done"}, status=409)
        sessions.delete(sid, base=registry.atlas)
        registry.get(sid)            # drops its entry, the session being gone
        self.note("session %s deleted" % sid)
        return self.send_json({"ok": True, "id": sid})

    # -- server sent events ---------------------------------------------
    def sse(self, hub):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "keep-alive")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()
        # Subscribed before the whole payload is read, so no delta falls
        # between the two; one that is already in it applies again unchanged.
        q, cv = hub.subscribe()
        try:
            self.wfile.write(b"retry: 1000\n\n")
            self.wfile.write(("data: " + hub.payload + "\n\n").encode("utf-8"))
            self.wfile.flush()
            while not hub.stopped.is_set():
                with cv:
                    if not q:
                        cv.wait(PING_SECONDS)
                    pending = q[:]
                    del q[:]
                if pending:
                    # Every one, in order: each is a delta on the one before.
                    for payload in pending:
                        self.wfile.write(("data: " + payload + "\n\n").encode("utf-8"))
                else:
                    self.wfile.write(b": ping\n\n")
                self.wfile.flush()
        except Exception:
            pass
        finally:
            hub.unsubscribe((q, cv))
            # A stream ends only when it broke or its hub was dropped; either
            # way the socket carries nothing more.
            self.close_connection = True
