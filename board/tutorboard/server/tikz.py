"""TikZ to SVG, off the request thread.

A diagram takes seconds to compile and a card has to appear in a tenth of one,
so the card lands with a placeholder and the picture arrives when it is ready.

One compiler thread serves the whole process. Every stored session caches in
`sessions/.tikz/`, under `digest(kind, src, root)`: a hash of the source and of
the subject's macros, so one figure in two subjects whose macros differ is two
files, and the same figure in two sessions on one subject is compiled once.

    TikzWorker(repo)        one session's handle: submit, dirty, start, stop
    digest(kind, src, root) a figure's name in the cache
"""

import hashlib
import os
import shutil
import subprocess
import tempfile
import threading

from .. import paths, tex


TIKZ_DOC = r"""\documentclass[border=6pt,varwidth=%(width)s]{standalone}
\usepackage{amsmath,amssymb,amsthm,mathtools}
\usepackage{tikz}
\usepackage{tikz-cd}
\usetikzlibrary{arrows.meta,positioning,calc,fit,shapes.geometric}
%(macros)s
\input{board-macros.tex}
\begin{document}
%(body)s
\end{document}
"""


# ---------------------------------------------------------------------------
# the cache key
# ---------------------------------------------------------------------------
def macro_files(root):
    """What a figure compiled for `root` reads besides its own source: every
    `.sty` and `.tex` directly in `<root>/latex/`, and the board's macros."""
    found = []
    where = os.path.join(root, "latex")
    try:
        names = sorted(os.listdir(where))
    except OSError:
        names = []
    for name in names:
        full = os.path.join(where, name)
        if name.endswith((".sty", ".tex")) and os.path.isfile(full):
            found.append(full)
    found.append(os.path.join(paths.TOOL, "tex", "board-macros.tex"))
    return found


_MACROS = {}
_MACROS_LOCK = threading.Lock()


def macros_key(root):
    """A hash of the macro files `root` compiles with, recomputed only when
    one of them changes (by path, mtime and size)."""
    stamp = []
    for path in macro_files(root):
        try:
            st = os.stat(path)
        except OSError:
            continue
        stamp.append((path, st.st_mtime_ns, st.st_size))
    stamp = tuple(stamp)
    with _MACROS_LOCK:
        hit = _MACROS.get(root)
        if hit and hit[0] == stamp:
            return hit[1]
    h = hashlib.sha1()
    for path, _m, _s in stamp:
        h.update(os.path.basename(path).encode("utf-8") + b"\x00")
        try:
            with open(path, "rb") as fh:
                h.update(fh.read())
        except OSError:
            pass
        h.update(b"\x00")
    key = h.hexdigest()[:16]
    with _MACROS_LOCK:
        _MACROS[root] = (stamp, key)
    return key


def digest(kind, src, root):
    """The cache name of one figure: its kind, its source and `root`'s macros."""
    key = kind + "\x00" + src + "\x00" + macros_key(root)
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# the one compiler
# ---------------------------------------------------------------------------
class Compiler(threading.Thread):
    """Compiles queued figures one at a time, then marks dirty every session
    that asked for the figure."""

    daemon = True

    def __init__(self):
        threading.Thread.__init__(self, name="tikz")
        self.cv = threading.Condition()
        self.queue = []
        # (cache, name) -> the handles waiting on it.
        self.waiting = {}
        # Figures that left neither an .svg nor an .err. Asking again would
        # compile them again on every rebuild, forever.
        self.lost = set()

    def submit(self, handle, cache, root, jobs):
        with self.cv:
            for name, kind, src in jobs:
                key = (cache, name)
                if key in self.lost:
                    continue
                if key in self.waiting:
                    self.waiting[key].add(handle)
                    continue
                self.waiting[key] = set([handle])
                self.queue.append((cache, root, name, kind, src))
            if self.queue:
                self.cv.notify()

    def run(self):
        while True:
            with self.cv:
                while not self.queue:
                    self.cv.wait()
                cache, root, name, kind, src = self.queue.pop(0)
            try:
                compile_figure(cache, root, name, kind, src)
            except Exception as exc:  # never let the worker die      # noqa: BLE001
                try:
                    _fail(cache, name, str(exc))
                except OSError:
                    pass
            done = (os.path.exists(os.path.join(cache, name + ".svg"))
                    or os.path.exists(os.path.join(cache, name + ".err")))
            with self.cv:
                handles = self.waiting.pop((cache, name), set())
                if not done:
                    self.lost.add((cache, name))
            for handle in handles:
                handle.dirty.set()


_COMPILER = None
_COMPILER_LOCK = threading.Lock()


def compiler():
    """The process's one Compiler, started on first use."""
    global _COMPILER
    with _COMPILER_LOCK:
        if _COMPILER is None:
            _COMPILER = Compiler()
            _COMPILER.start()
        return _COMPILER


class TikzWorker(object):
    """One session's handle on the compiler, and its hub's dirty mark.

    Jobs submitted before `start` are held, so a hub a test drives by hand
    compiles nothing. `stop` holds new jobs again; the compiler is shared and
    runs on.
    """

    def __init__(self, repo):
        self.repo = repo
        self.dirty = threading.Event()
        self.started = False
        self.held = []
        self.lock = threading.Lock()

    def start(self):
        with self.lock:
            self.started = True
            held, self.held = self.held, []
        if held:
            self.submit(held)

    def stop(self):
        with self.lock:
            self.started = False

    def submit(self, jobs):
        with self.lock:
            if not self.started:
                have = set(j[0] for j in self.held)
                self.held.extend(j for j in jobs if j[0] not in have)
                return
            repo = self.repo
        if jobs:
            compiler().submit(self, repo.tikz, repo.root, jobs)


# ---------------------------------------------------------------------------
# one figure
# ---------------------------------------------------------------------------
def _fail(cache, name, msg):
    """Write `<name>.err` whole or not at all: sessions share the cache."""
    fd, tmp = tempfile.mkstemp(dir=cache, prefix=".err-")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(msg)
    os.replace(tmp, os.path.join(cache, name + ".err"))


def compile_figure(cache, root, name, kind, src):
    """Compile one figure with `root`'s macros into `<cache>/<name>.svg`,
    or write `<name>.err` saying why not."""
    os.makedirs(cache, exist_ok=True)
    # A blank line inside a tikzpicture or tikzcd is a \par and blows up the
    # cell. Markdown fences pick up trailing whitespace, so strip it here.
    src = "\n".join(ln for ln in src.split("\n") if ln.strip()).strip()
    macros = ""
    if os.path.exists(os.path.join(root, "latex", "coursemacros.sty")):
        macros = r"\usepackage{coursemacros}"
    body = src
    if kind == "tikzcd" and "\\begin{tikzcd}" not in src:
        body = "\\begin{tikzcd}\n%s\n\\end{tikzcd}" % src
    elif kind == "tikz" and "\\begin{tikzpicture}" not in src and "\\begin{tikzcd}" not in src:
        body = "\\begin{tikzpicture}\n%s\n\\end{tikzpicture}" % src

    work = tempfile.mkdtemp(prefix="_work-%s-" % name, dir=cache)
    try:
        source = os.path.join(work, "fig.tex")
        with open(source, "w", encoding="utf-8") as fh:
            fh.write(TIKZ_DOC % {"width": "0pt", "macros": macros, "body": body})

        env = tex.tex_env([os.path.join(root, "latex"), os.path.join(paths.TOOL, "tex")])

        proc = subprocess.run(
            ["latex", "-interaction=nonstopmode", "-halt-on-error",
             "-output-directory=" + work, source],
            cwd=work, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=90,
        )
        dvi = os.path.join(work, "fig.dvi")
        if proc.returncode != 0 or not os.path.exists(dvi):
            log = os.path.join(work, "fig.log")
            detail = ""
            if os.path.exists(log):
                with open(log, "r", encoding="utf-8", errors="replace") as fh:
                    lines = [ln for ln in fh if ln.startswith("!") or ".tex:" in ln]
                detail = "".join(lines[:8])
            _fail(cache, name, detail or proc.stdout.decode("utf-8", "replace")[-800:])
            return

        made = os.path.join(work, "fig.svg")
        proc = subprocess.run(
            ["dvisvgm", "--no-fonts", "--exact-bbox", "--zoom=1.35",
             "--output=" + made, dvi],
            cwd=work, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=90,
        )
        if proc.returncode != 0 or not os.path.exists(made):
            _fail(cache, name, proc.stdout.decode("utf-8", "replace")[-800:])
            return
        os.replace(made, os.path.join(cache, name + ".svg"))
    finally:
        shutil.rmtree(work, ignore_errors=True)
