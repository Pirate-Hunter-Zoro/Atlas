"""The HTTP handler: headers, bodies, the event stream, and a table of routes.

What is NOT here is every route. That was nine hundred lines of `if path == ...`
in two methods, and the cost of it was not length -- it was that finding out what
one path did meant reading past all the others, and adding one meant editing the
method everybody else was editing. The families live in `routes/`; this keeps the
plumbing they all use and the order they are asked in.
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

from .. import paths, sessions, subjects
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

# EVERY ROUTE SERVED WITHOUT A `/s/<id>` PREFIX, and how. Anything else
# unprefixed is 404 on a session server. A pattern ending in `*` is a prefix.
# Each route module's own table says which class each of its routes is in.
#
#   subject   a subject's own routes. Unprefixed, `?subject=<id>` names the
#             subject and a sessionless Repo over it serves; under
#             `/s/<id>/` the session's own subject does.
#   subject?  the same, and with no `?subject=` the Atlas root serves (the
#             meeting deck's ink and pages).
#   atlas     cross-subject: unprefixed only, served by a sessionless Repo over
#             the Atlas root, and 404 under `/s/<id>/`.
#
# The rest are the handler's own. An ask any of these makes of a subject's
# tutor goes through `registry.runner_route`.
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
    ("GET", "/notices.json", "notices"),
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
    ("POST", "/library/direction", "subject"),
    ("POST", "/doc/delete", "subject"),
    ("POST", "/writeup", "subject?"),
    ("POST", "/sittings", "atlas"),
    ("POST", "/sittings/items", "atlas"),
    ("POST", "/sittings/deck", "atlas"),
    ("POST", "/sittings/decks", "atlas"),
    # machines
    ("GET", "/meeting", "meeting"),
    ("GET", "/meeting/", "meeting"),
    ("GET", "/courses.json", "atlas"),
    ("GET", "/atlas.json", "atlas"),
    ("GET", "/news", "atlas"),
    ("GET", "/missions", "atlas"),
    ("GET", "/mission", "atlas"),
    ("GET", "/meeting/deck.json", "atlas"),
    ("GET", "/meeting/view", "atlas"),
    ("GET", "/meeting/pdf", "atlas"),
    ("POST", "/notes/what", "atlas"),
    ("POST", "/notes", "atlas"),
    ("POST", "/meeting/direction", "atlas"),
    ("POST", "/default-agent", "atlas"),
    ("POST", "/colibri", "atlas"),
    ("POST", "/writeup/scopes", "atlas"),
    ("POST", "/elsewhere", "atlas"),
    ("POST", "/switch", "atlas"),
    # Rendered PDF pages: one cache for every session (`course/paper.py`).
    ("GET", "/paper/*", "paper"),
    # writing
    ("POST", "/annotate/save", "subject?"),
)

# The route classes UNPREFIXED names. A cross-subject one (and the meeting
# page, which is its page) is 404 under `/s/<id>/`.
SUBJECT_CLASSES = ("subject", "subject?")
CROSS = "atlas"
NOT_IN_SESSION = (CROSS, "meeting")


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

    # A request log, deliberately narrow.
    #
    # `board.log` used to hold nothing but "listening", which made two very
    # different failures the same observation: a send that never left the iPad
    # and a send this server rejected both looked like silence. Diagnosing the
    # first one cost a scratch server and a jsdom probe. Now the file says what
    # arrived.
    #
    # The poll and the stream are left out on purpose. /board.json is asked for
    # several times a second and /events never ends, so logging either buries
    # the one line anybody actually wants -- but a failure is logged whatever
    # the path, because a 500 on the poll is worth knowing about.
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
    # Text assets go out gzipped when the client says it takes gzip: board.js
    # alone is over half a megabyte, and the iPad fetches it over Tailscale.
    # Each is compressed once per content, held by slot and stamp (a file's
    # path and mtime), and replaced when the stamp moves.
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
            # The shell must never be held by the browser: an installed app that
            # cannot pick up a fix is an app nobody can repair.
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

    # Types that are safe to hand back inline for a file somebody uploaded.
    # Everything else is downloaded rather than rendered -- an uploaded .html or
    # .svg would otherwise run script on this origin.
    INLINE_OK = {"image/png", "image/jpeg", "image/gif", "image/webp", "application/pdf"}

    def send_file(self, path, cache=False, untrusted=False, download=None):
        """`download` is a filename, and it means SAVE THIS rather than show it.

        A PDF is in `INLINE_OK`, so a browser handed one renders it in the tab --
        which is the right default for looking at a figure and the wrong one for
        a document somebody asked to keep. On an iPad an inline PDF is a preview
        with no obvious route into Files; an attachment goes straight to the
        share sheet, and from there to iCloud, a phone, or an email to a
        professor. So the caller says which it wants, and the filename is the
        name the file will have on the other side.
        """
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
        if not untrusted and not download:
            st = os.stat(path)
            gzip_key = (path, (st.st_mtime_ns, st.st_size))
        with open(path, "rb") as fh:
            self.send_bytes(fh.read(), ctype, cache=cache, nosniff=untrusted, extra=extra,
                            gzip_key=gzip_key)

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
    # A session server (`app.main`) has a `registry`: `/s/<id>/...` is served
    # by that session's Repo and Hub with the prefix stripped, and an
    # unprefixed request is answered only when UNPREFIXED lists it. A server
    # a test builds with `repo` and `hub` and no registry serves one session,
    # unprefixed, as before.
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
        # A PAGE OF ITS OWN, not a panel over the lesson. "View all papers and
        # presentations related to a project very easily" means not opening a
        # sitting to get there -- and feedback written from it must not touch the
        # lesson somebody else is mid-proof in. `/slate` is the precedent.
        if path in ("/library", "/library/"):
            return self.send_file(os.path.join(WEB, "library.html"))
        # THE MEETING DECK, and it is a page of its own for the same reason the
        # library is: it belongs to the REPOSITORY rather than to the workspace
        # this board serves, and nothing on it may touch the sitting. Only the
        # bare path -- `/meeting/view`, `/meeting/deck.json` and `/meeting/pdf`
        # are data and are answered by `routes.machines` below.
        if path in ("/meeting", "/meeting/"):
            return self.send_file(os.path.join(WEB, "meeting.html"))
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
        # Before anything writes. The directories were made when this process
        # started and a pull can have removed one since -- see `Repo.ensure_dirs`.
        # Ten stat calls against a route that is about to write a PNG.
        repo.ensure_dirs()
        return self.post_routes(repo, path)

    def post_routes(self, repo, path):
        for mod in (routes.saving, routes.library, routes.lesson, routes.writing,
                    routes.machines):
            answered = mod.post(self, repo, path)
            if answered is not routes.NOT_MINE:
                return answered
        return self.send_bytes(b"not found", "text/plain", status=404)

    # -- unprefixed ------------------------------------------------------
    def unprefixed(self, method, path, query):
        """Answer a request outside `/s/<id>/` that UNPREFIXED lists; 404
        for anything else."""
        how = unprefixed_route(method, path)
        if how is None:
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
            if "code" in query:
                out["code"] = {"running": code_stamp.LOADED, "tree": code_stamp.tree()}
            return self.send_json(out)
        if how == "sessions":
            return self.send_json({"ok": True, "sessions": [
                dict(rec, url="/s/%s/board" % rec.get("id"))
                for rec in sessions.all(registry.atlas)]})
        if how == "new":
            return self.new_session(registry)
        if how == "subjects":
            return self.send_json({"ok": True, "subjects": [
                {k: one[k] for k in ("id", "kind", "slug", "name")}
                for one in subjects.all(registry.atlas)]})
        if how == "notices":
            return self.send_json({"ok": True, "notices": []})
        if how == "meeting":
            return self.send_file(os.path.join(WEB, "meeting.html"))
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
        """POST /sessions/new: an unbound session in teach, titled by the body's
        optional `title`; its record and the URL of its board."""
        try:
            body = self.read_body()
            payload = json.loads(body.decode("utf-8")) if body.strip() else {}
        except (ValueError, UnicodeDecodeError):
            return self.send_json({"ok": False, "error": "bad json"}, status=400)
        title = payload.get("title") if isinstance(payload, dict) else None
        title = str(title).strip()[:200] if title else None
        rec = sessions.new(title, base=registry.atlas)
        self.note("session %s opened" % rec["id"])
        return self.send_json({"ok": True, "id": rec["id"], "session": rec,
                               "url": "/s/%s/board" % rec["id"]})

    # -- server sent events ---------------------------------------------
    def sse(self, hub):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "keep-alive")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()
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
                    for payload in pending[-1:]:
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
