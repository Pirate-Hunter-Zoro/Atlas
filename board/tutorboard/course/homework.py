"""homework.py -- where a course keeps its problem sets, and how much of one is done.

Two layouts exist, `homework/hw04/hw04.tex` and
`chapters/ch07-*/homework/ch07-homework.tex`, so sets are discovered, never
assumed; a session settles which by its pin, session.json `writeup`. A
session's write-up is the bound set written in place, else
`docs/<slug>/writeup.tex` from `board/tex/writeup.tex.in`: `start` makes it,
`add` writes an agreed answer, `build` compiles it for the banner.

The constraint: problem labels are opaque strings (`7.1`, `13`, `2(b)`),
never integers.
"""

import fnmatch
import glob
import json
import os
import re
import shutil
import time

# The region markers every template emits; they are how written-up is told
# from not. `%+` as well as `%`, since a doubled marker is ordinary.
SOLUTION_OPEN = re.compile(r"^\s*%+\s*=+\s*SOLUTION\s+(?P<label>\S+)\s*=+\s*$")
SOLUTION_CLOSE = re.compile(r"^\s*%+\s*=+\s*END\s+SOLUTION\s+(?P<label>\S+)\s*=+\s*$")
PROBLEM = re.compile(r"\\begin\{problem\}\{(?P<label>[^}]*)\}")

LAYOUTS = (
    os.path.join("homework", "*", "*.tex"),
    os.path.join("chapters", "*", "homework", "*.tex"),
)

# A session's own write-up: no problem set (`sets` never lists it), found
# only by its pin.
DOCS_LAYOUT = os.path.join("docs", "*", "*.tex")
PINNABLE = LAYOUTS + (DOCS_LAYOUT,)
WRITEUP_SOURCE = "writeup.tex"

# The one template every write-up starts from: a session's, and a course's
# chapter notes and sets laid down by `board textbook scaffold`.
TEMPLATE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "tex", "writeup.tex.in")

# The build record the board's banner paints, in the session directory.
RECORD = "hw.json"


# ---------------------------------------------------------------------------
# A course's chapters: how a course that follows a book orders itself
# ---------------------------------------------------------------------------
# A book-following course says so on disk: `chapters.tsv` (num, from, to,
# slug, title) or `chapters/chNN-slug/` directories. Neither means no book.
CHAPTERS_TSV = "chapters.tsv"


def _chapters_from_tsv(root):
    out = []
    try:
        with open(os.path.join(root, CHAPTERS_TSV), "r", encoding="utf-8",
                  errors="replace") as fh:
            for line in fh:
                line = line.rstrip("\n")
                if not line.strip() or line.lstrip().startswith("#"):
                    continue
                cols = [c.strip() for c in line.split("\t") if c.strip() != ""]
                if len(cols) < 2:
                    continue
                out.append({"num": cols[0],
                            "slug": cols[-2] if len(cols) >= 3 else "",
                            "title": cols[-1]})
    except OSError:
        return []
    return out


def _chapters_from_dirs(root):
    out = []
    for path in sorted(glob.glob(os.path.join(root, "chapters", "ch*"))):
        if not os.path.isdir(path):
            continue
        name = os.path.basename(path)
        m = re.match(r"ch(\d+)[-_]?(.*)$", name)
        if not m:
            continue
        out.append({"num": m.group(1).lstrip("0") or "0", "slug": name,
                    "title": m.group(2).replace("-", " ").strip()})
    return out


def chapters(root):
    """Every chapter of the book this course follows, in the course's order:
    `[{num, slug, title}]`. Empty where the subject is not a book."""
    return _chapters_from_tsv(root) or _chapters_from_dirs(root)


def opening(root):
    """The chapter a course with no other instruction opens at, or None."""
    every = chapters(root)
    return every[0] if every else None


def chapter_label(chapter):
    """How a chapter is written on a line: `Ch 7 — Splitting fields`."""
    if not chapter:
        return ""
    title = (chapter.get("title") or chapter.get("slug") or "").strip()
    num = str(chapter.get("num") or "").strip()
    if num and title:
        return "Ch %s — %s" % (num, title)
    return title or ("Ch %s" % num if num else "")


def chapter_dir(root, name):
    """`chapters/<dir>` of a chapter named by label, slug or title, or "".
    Looked up on disk: a slug `rings` lives in `ch03-rings`."""
    want = str(name or "").strip()
    if not want:
        return ""
    for c in chapters(root):
        if want not in (chapter_label(c), c.get("slug"), c.get("title")):
            continue
        slug = c.get("slug") or ""
        num = str(c.get("num") or "").strip()
        cands = []
        if slug:
            cands.append(slug)
            if num.isdigit():
                cands.append("ch%02d-%s" % (int(num), slug))
        if num.isdigit():
            cands.extend(sorted(os.path.basename(p) for p in glob.glob(
                os.path.join(root, "chapters", "ch%02d*" % int(num)))))
        for one in cands:
            if os.path.isdir(os.path.join(root, "chapters", one)):
                return "chapters/" + one
    return ""


def _name_for(root, tex):
    """What to call this set: the folder that identifies it (`hw04`, `ch07`),
    not the file."""
    rel = os.path.relpath(tex, root).split(os.sep)
    if rel[0] in ("homework", "docs") and len(rel) >= 3:
        return rel[1]
    if rel[0] == "chapters" and len(rel) >= 2:
        m = re.match(r"(ch\d+)", rel[1])
        return m.group(1) if m else rel[1]
    return os.path.splitext(os.path.basename(tex))[0]


# A set's title and chapter are derived, never registered. The title comes
# from the source's banner comment or heading (a chapter-numbered set is named
# after its chapter). The chapter comes from the course's numbering, a
# declaration comment in the `.tex`, or the slug matched against
# `chapters.tsv`; a slug matching two chapters matches neither.
CHAPTER_DECLARED = re.compile(r"^\s*%+\s*chapter:\s*(\d+)\s*$", re.M)

# The set name a course numbers by chapter: `ch04`, `ch7`, `chapter-12`.
CHAPTER_NAMED = re.compile(r"^(?:ch|chapter)[-_]?0*(\d+)$", re.I)

# What a worksheet's directory is called before the part that names its topic.
SET_PREFIXES = ("worksheet-", "worksheet_", "hw-", "homework-", "set-", "ps-")

# A title in the source: the banner comment first, then headings.
_TITLE_LINES = (
    re.compile(r"^\s*%+\s{2,}(?P<t>[A-Z][^\n]{3,90}?)\s*$", re.M),
    re.compile(r"\\section\*?\{(?P<t>[^}]{3,90})\}"),
    re.compile(r"\\title\s*\{(?P<t>[^}]{3,90})\}"),
)


def _read(tex, limit=40000):
    try:
        with open(tex, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read(limit)
    except OSError:
        return ""


# Due-date and duplicated-name lines are not titles.
_DUE = re.compile(r"\s*[.;,]?\s*Due\b[^.]*\.?\s*$", re.I)
_SAID_TWICE = re.compile(r"^(?P<one>.{3,40}?)\s+[—–-]+\s+(?P=one)\s*$")

# Max title length; cut on a word.
TITLE_MAX = 70


def _tidy(title):
    """A source's title line, as a person would want it on a map."""
    title = re.sub(r"\s+", " ", title or "").strip(" -=")
    # LaTeX spells its dashes with hyphens; the glass does not have to.
    title = title.replace("---", "—").replace("--", "–")
    title = _DUE.sub("", title).strip(" .,;—–-")
    said = _SAID_TWICE.match(title)
    if said:
        title = said.group("one").strip()
    if len(title) > TITLE_MAX:
        cut = title[:TITLE_MAX].rsplit(" ", 1)[0]
        title = (cut or title[:TITLE_MAX]).rstrip(" ,;:—–-") + "…"
    return title


def _title_in(text):
    """The title the source states, or `""`."""
    for pattern in _TITLE_LINES:
        found = pattern.search(text or "")
        if found:
            title = _tidy(found.group("t"))
            # A rule of dashes or equals signs is not a title.
            if title and not set(title) <= set("-=_–— "):
                return title
    return ""


def _chapter_for(root, name, tex, text):
    """Which chapter this set is for, as an int, or None: the course's
    numbering, then the author's declaration, then the slug (ambiguity
    refused)."""
    found = CHAPTER_NAMED.match(name or "")
    if found:
        return int(found.group(1))
    found = CHAPTER_DECLARED.search(text or "")
    if found:
        return int(found.group(1))

    slug = (name or "").lower()
    for prefix in SET_PREFIXES:
        if slug.startswith(prefix):
            slug = slug[len(prefix):]
            break
    else:
        return None
    if not slug:
        return None
    hits = []
    for c in chapters(root):
        try:
            num = int(str(c.get("num") or "").strip())
        except ValueError:
            continue
        if str(c.get("slug") or "").strip().lower() == slug:
            hits.append(num)
    return hits[0] if len(hits) == 1 else None


def title_for(root, name, tex):
    """What to call this set: a chapter-numbered set by its number alone
    (its chapter box carries the title), anything else by its source."""
    found = CHAPTER_NAMED.match(name or "")
    if found:
        return "Ch %02d homework" % int(found.group(1))
    return _title_in(_read(tex)) or name


def sets(root):
    """Every problem set in this repository, newest last, each with a derived
    `title` and `chapter`."""
    found = {}
    for pattern in LAYOUTS:
        for tex in glob.glob(os.path.join(root, pattern)):
            parts = os.path.relpath(tex, root).split(os.sep)
            if "build" in parts or os.path.basename(tex).startswith("."):
                continue
            # A chapter's notes file is not its homework.
            if parts[0] == "chapters" and "homework" not in parts:
                continue
            name = _name_for(root, tex)
            full = os.path.abspath(tex)
            found[full] = {
                "name": name,
                "title": title_for(root, name, full),
                "chapter": _chapter_for(root, name, full, _read(full)),
                "tex": full,
                "rel": os.path.relpath(tex, root),
                "dir": os.path.dirname(full),
            }
    return sorted(found.values(), key=lambda s: s["name"])


def assignment(set_dir):
    """The sheet as handed out (`homework/hwNN/assignment/`), if kept, so the
    problems are never inferred from a chapter."""
    out = []
    for pattern in ("assignment/*", "*.pdf"):
        for path in sorted(glob.glob(os.path.join(set_dir, pattern))):
            if os.path.isfile(path) and not path.endswith((".aux", ".log", ".out")):
                out.append(path)
        if out:
            break
    return out


def _hints(text):
    """Set names a session's human label could be naming."""
    out = []
    if not text:
        return out
    low = text.lower()
    for pat, fmt in ((r"\bhw\s*0*(\d+)", "hw%02d"),
                     (r"\bhomework\s*(?:set\s*)?0*(\d+)", "hw%02d"),
                     (r"\bch(?:apter)?\.?\s*0*(\d+)", "ch%02d")):
        for m in re.finditer(pat, low):
            out.append(fmt % int(m.group(1)))
    return out


def _record(root, tex):
    """One write-up as `sets` lists it."""
    name = _name_for(root, tex)
    full = os.path.abspath(tex)
    return {"name": name, "title": title_for(root, name, full),
            "chapter": _chapter_for(root, name, full, _read(full)),
            "tex": full, "rel": os.path.relpath(full, root), "dir": os.path.dirname(full)}


def _pinned(root, every, pinned):
    """The write-up `pinned` names: a set by name or path, or a session's own
    `docs/<slug>/*.tex`, which is no set and is found only by its pin."""
    if not pinned:
        return None
    want = os.path.abspath(os.path.join(root, pinned))
    for s in every:
        if s["tex"] == want or s["name"] == pinned:
            return s
    rel = os.path.relpath(want, root)
    if fnmatch.fnmatch(rel, DOCS_LAYOUT) and os.path.isfile(want):
        return _record(root, want)
    return None


def _named(every, state):
    """The set a session's label names: its chapter, course or title."""
    state = state or {}
    names = (_hints(state.get("chapter")) + _hints(state.get("course"))
             + _hints(state.get("title")))
    for n in names:
        for s in every:
            if s["name"] == n:
                return s
    return None


def find(root, state):
    """The problem set this session is about, or None. Pinned beats guessed,
    and an ambiguous guess is no answer: writing into the wrong set is worse
    than stopping."""
    every = sets(root)
    found = _pinned(root, every, (state or {}).get("hw")) or _named(every, state)
    if found:
        return found
    if len(every) == 1:
        return every[0]
    return None


def bound(root, state):
    """The set this sitting writes into, or None: pinned, or named by the
    session label (a chapter label is a binding). Narrower than `find`, which
    also falls back to a course's lone set: that line every turn would be noise.
    """
    every = sets(root)
    return _pinned(root, every, (state or {}).get("hw")) or _named(every, state)


def _region_written(lines):
    """Is there mathematics in here, or only the placeholder comment?"""
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("%"):
            continue
        return True
    return False


def problems(tex):
    """Every problem in a set, in order, with `stated` (the statement replaced
    its `\\todo`) and `written` (anything but comments in its region)."""
    try:
        with open(tex, "r", encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
    except OSError:
        return []

    order, seen = [], {}

    # Statements first, so a problem with no solution region at all still counts.
    depth_text = "\n".join(lines)
    for m in PROBLEM.finditer(depth_text):
        label = m.group("label").strip()
        if label in seen:
            continue
        body = depth_text[m.end():]
        end = body.find(r"\end{problem}")
        if end >= 0:
            body = body[:end]
        seen[label] = {"label": label, "stated": r"\todo{" not in body,
                       "written": False, "region": False}
        order.append(label)

    # Then the regions.
    i, n = 0, len(lines)
    while i < n:
        m = SOLUTION_OPEN.match(lines[i])
        if not m:
            i += 1
            continue
        label = m.group("label").strip()
        body, j = [], i + 1
        while j < n:
            close = SOLUTION_CLOSE.match(lines[j])
            if close and close.group("label").strip() == label:
                break
            body.append(lines[j])
            j += 1
        rec = seen.get(label)
        if rec is None:
            rec = {"label": label, "stated": True, "written": False, "region": False}
            seen[label] = rec
            order.append(label)
        rec["region"] = True
        rec["written"] = _region_written(body)
        i = j + 1

    return [seen[label] for label in order]


def outstanding(probs):
    """Every problem still without a written solution, in the file's order,
    which is the assignment's, since the skeleton is laid down in one pass. A
    skipped problem is one of these."""
    return [p["label"] for p in probs if not p["written"]]


def status(root, state):
    """What the board shows: which set, and how much of it is done."""
    s = find(root, state)
    if not s:
        every = sets(root)
        if not every:
            return None
        return {"name": None, "rel": None, "ambiguous": [e["name"] for e in every],
                "problems": [], "total": 0, "written": 0, "stated": 0}
    probs = problems(s["tex"])
    sheets = assignment(s["dir"])
    return {
        "name": s["name"],
        "rel": s["rel"],
        "dir": s["dir"],
        "assignment": [os.path.relpath(p, root) for p in sheets],
        "ambiguous": [],
        "problems": probs,
        "total": len(probs),
        "written": sum(1 for p in probs if p["written"]),
        "stated": sum(1 for p in probs if p["stated"]),
        # The first empty region is where the next agreed answer goes, in
        # sheet order whatever order they work in.
        "outstanding": outstanding(probs),
        "next": (outstanding(probs) or [None])[0],
    }


def compiled_pdf(root, tex_path):
    """The PDF `board build` wrote beside this `.tex` under its name, or None.
    `root` is kept for callers."""
    if not tex_path:
        return None
    candidate = os.path.splitext(os.path.abspath(tex_path))[0] + ".pdf"
    return candidate if os.path.isfile(candidate) else None



# ---------------------------------------------------------------------------
# the write-up: start one, add an agreed answer, build it
# ---------------------------------------------------------------------------
# A label goes into environments, markers and a PNG name, so it is matched,
# not escaped.
LABEL_RE = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._()-]{0,23}\Z")

# The line on stdin between the statement and the argument.
SPLIT = "---"

# A fenced code block, set verbatim: no package, no shell-escape.
FENCE = re.compile(r"^\s*(```|~~~)")

_TEX_SPECIAL = re.compile(r"([\\&%$#_{}~^])")
_TEX_WORDS = {"\\": r"\textbackslash{}", "~": r"\textasciitilde{}",
              "^": r"\textasciicircum{}"}


def tex_escape(text):
    """Plain text made safe for a LaTeX title or author."""
    return _TEX_SPECIAL.sub(lambda m: _TEX_WORDS.get(m.group(1), "\\" + m.group(1)),
                            str(text or ""))


def render(title, author=""):
    """`writeup.tex.in` with its title and author filled in."""
    with open(TEMPLATE, "r", encoding="utf-8") as fh:
        text = fh.read()
    return (text.replace("@@TITLE@@", tex_escape(title).strip())
            .replace("@@AUTHOR@@", tex_escape(author).strip()))


def split_input(text):
    """`(statement, argument)` from stdin: the statement, a line `---`, then
    the argument. With no `---` line it is all argument."""
    lines = str(text or "").splitlines()
    for i, line in enumerate(lines):
        if line.strip() == SPLIT:
            return ("\n".join(lines[:i]).strip("\n"), "\n".join(lines[i + 1:]).strip("\n"))
    return "", "\n".join(lines).strip("\n")


def verbatim(text):
    """`(tex, None)` with each fenced code block set as a verbatim
    environment and everything else as written, or `(None, why)`."""
    out, code, fenced_now = [], [], False
    for line in str(text or "").splitlines():
        if FENCE.match(line):
            if fenced_now:
                out += ["\\begin{verbatim}"] + code + ["\\end{verbatim}"]
                code, fenced_now = [], False
            else:
                fenced_now = True
            continue
        if fenced_now:
            if "\\end{verbatim}" in line:
                return None, "a code block may not contain \\end{verbatim}"
            code.append(line.expandtabs(4))
        else:
            out.append(line)
    if fenced_now:
        out += ["\\begin{verbatim}"] + code + ["\\end{verbatim}"]
    return "\n".join(out), None


def _claim(found, session):
    """Write the set's doc.json in place, listing this session, so the library
    lists it as an artifact and End commits it. An unchanged one is left."""
    from .. import artifacts
    d = os.path.dirname(found["tex"])
    have = artifacts.read(d) or {}
    sid = artifacts._session_id(session)
    same = have.get("source") == os.path.relpath(found["tex"], d).replace(os.sep, "/")
    if same and (not sid or sid in (have.get("sessions") or [])):
        return
    artifacts.place(d, found["tex"], have.get("title") or found["title"], session)


def start(root, state, session=None, title=None, author=""):
    """The write-up this session writes into, made when it has none.
    `(record, made)`. A `title` naming a set is that set; else the bound set
    in place; else `docs/<slug>/writeup.tex` from the template. ValueError
    where `root` cannot hold one.
    """
    state = state or {}
    named = (title or "").strip()
    if named:
        for one in sets(root):
            if named in (one["name"], one["rel"]):
                _claim(one, session)
                return one, False
    found = bound(root, state)
    if found and os.path.isfile(found["tex"]):
        _claim(found, session)
        return found, False
    from .. import artifacts
    sid = artifacts._session_id(session)
    said = (title or state.get("title") or state.get("chapter") or "").strip()
    if not said:
        said = "Writeup %s" % (sid or time.strftime("%Y-%m-%d"))
    art = artifacts.create(root, said, session, ".tex", source=WRITEUP_SOURCE)
    # Under `root` as given: `create` answers in real paths.
    tex = os.path.join(os.path.abspath(root), *(art["rel"].split("/") + [art["source"]]))
    with open(tex, "w", encoding="utf-8") as fh:
        fh.write(render(said, author))
    return _record(root, tex), True


def _find_problem(lines, label):
    """`(begin, end)` line indices of the problem environment for `label`."""
    opener = "\\begin{problem}{%s}" % label
    for i, line in enumerate(lines):
        if opener in line:
            for j in range(i, len(lines)):
                if "\\end{problem}" in lines[j]:
                    return i, j
            return i, None
    return None, None


def _find_region(lines, label):
    """`(open, close)` line indices of the solution region for `label`."""
    for i, line in enumerate(lines):
        m = SOLUTION_OPEN.match(line)
        if m and m.group("label").strip() == label:
            for j in range(i + 1, len(lines)):
                c = SOLUTION_CLOSE.match(lines[j])
                if c and c.group("label").strip() == label:
                    return i, j
            return i, None
    return None, None


def _markers(label):
    return ("% ===== SOLUTION " + label + " =====",
            "% ===== END SOLUTION " + label + " =====")


def add(tex, label, statement, argument):
    """Write one agreed answer into the write-up at `tex`.

    The argument replaces the solution region for `label`; the statement
    fills a `\\todo` or empty problem, never a transcribed one. An unknown
    label is appended before `\\end{document}`. `({label, statement,
    region}, None)`, or `(None, why)` with nothing written.
    """
    label = str(label or "").strip()
    if not LABEL_RE.match(label):
        return None, ("a label is letters, digits and . _ ( ) -, at most 24: %r"
                      % label)
    stmt, why = verbatim(statement)
    if why:
        return None, why
    arg, why = verbatim(argument)
    if why:
        return None, why
    if not arg.strip():
        return None, "no argument on stdin: the statement, a line ---, then their argument"
    try:
        with open(tex, "r", encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    except OSError as exc:
        return None, "cannot read %s: %s" % (tex, exc)
    said = {"label": label, "statement": "kept", "region": "filled"}
    begin, end = _find_problem(lines, label)
    if begin is not None and end is not None and end > begin:
        body = "\n".join(lines[begin + 1:end])
        if stmt.strip() and ("\\todo{" in body or not body.strip()):
            lines[begin + 1:end] = stmt.splitlines()
            said["statement"] = "written"
            begin, end = _find_problem(lines, label)
    opened, closed = _find_region(lines, label)
    arg_lines = arg.splitlines()
    if opened is not None and closed is not None:
        if _region_written(lines[opened + 1:closed]):
            said["region"] = "replaced"
        lines[opened + 1:closed] = arg_lines
    elif begin is not None and end is not None:
        top, bottom = _markers(label)
        lines[end + 1:end + 1] = [top] + arg_lines + [bottom]
    else:
        last = None
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].strip().startswith("\\end{document}"):
                last = i
                break
        if last is None:
            return None, "%s has no \\end{document} to write before" % tex
        top, bottom = _markers(label)
        stmt_lines = (stmt.splitlines() if stmt.strip()
                      else ["\\todo{statement not yet transcribed}"])
        lines[last:last] = (["\\begin{problem}{%s}" % label] + stmt_lines
                            + ["\\end{problem}", top] + arg_lines + [bottom, ""])
        said["statement"] = "written" if stmt.strip() else "placeholder"
        said["region"] = "added"
    tmp = tex + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    os.replace(tmp, tex)
    return said, None


def file_page(src, found, label):
    """Copy a sent page into the write-up's `handwritten/` as
    `<name>-<label>.png`; the path it went to."""
    dest_dir = os.path.join(found["dir"], "handwritten")
    os.makedirs(dest_dir, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9._-]", "-", label)
    dest = os.path.join(dest_dir, "%s-%s.png" % (found["name"], safe))
    shutil.copyfile(src, dest)
    return dest


def build(root, session_dir, found):
    """Compile the write-up with `board build` and record the outcome in the
    session's `hw.json`, which the board's banner paints: the LaTeX error
    itself when it fails. `(code, pdf, detail)`."""
    from .. import build as builder                          # local: TeX helpers
    tex_path = os.path.join(root, found["rel"])
    rec = builder.build(tex_path)
    out = (rec.get("detail") or "").strip()
    pdf = compiled_pdf(root, tex_path)
    record = {"ok": bool(rec["ok"]), "at": time.time(),
              "iso": time.strftime("%Y-%m-%d %H:%M:%S"),
              "set": found["name"],
              "pdf": os.path.relpath(pdf, root) if pdf else None,
              "detail": out[-1600:]}
    os.makedirs(session_dir, exist_ok=True)
    with open(os.path.join(session_dir, RECORD), "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=2)
    return (0 if rec["ok"] else 1), pdf, out


def last_build(session_dir):
    """The session's last build record, or None."""
    try:
        with open(os.path.join(session_dir, RECORD), "r", encoding="utf-8") as fh:
            got = json.load(fh)
    except (OSError, ValueError):
        return None
    return got if isinstance(got, dict) else None
