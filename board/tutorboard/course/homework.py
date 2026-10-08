"""homework.py -- where a course keeps its problem sets, and how much of one is done.

Both the server and the command line need this. The server needs it so the board
can say "hw04, two of four written up" without anyone running a command; the
command line needs it to compile the right file and to file handwriting beside
it.

Two shapes exist in the wild and neither is more correct than the other:

    homework/hw04/hw04.tex                  numbered by assignment  (Probability)
    chapters/ch07-*/homework/ch07-homework.tex   numbered by chapter (Galois)

So this discovers rather than assumes, exactly like course discovery itself. A
session settles it by its pin, session.json `writeup`, which `board writeup
use` writes and the first `board writeup add` writes when it makes one.

THE WRITE-UP of any session is one of these: the bound set, written in place,
or else `docs/<session-slug>/writeup.tex`, a new artifact from the one
template, `board/tex/writeup.tex.in`. `start` makes it, `add` writes one agreed
answer into it, and `build` compiles it and records the outcome for the board.

The problem labels are opaque strings, not integers: one course numbers problems
1, 2, 3 and the other numbers them 7.1, 7.2, 7.3.

Standard library only, like everything else.
"""

import fnmatch
import glob
import json
import os
import re
import shutil
import time

# The scaffold both courses' templates emit. The assistant fills the region; the
# markers stay put, and they are how anything can tell written-up from not.
# `%+` rather than `%`: a doubled comment marker is an ordinary thing to write
# and the region it opens is no less real for it.
SOLUTION_OPEN = re.compile(r"^\s*%+\s*=+\s*SOLUTION\s+(?P<label>\S+)\s*=+\s*$")
SOLUTION_CLOSE = re.compile(r"^\s*%+\s*=+\s*END\s+SOLUTION\s+(?P<label>\S+)\s*=+\s*$")
PROBLEM = re.compile(r"\\begin\{problem\}\{(?P<label>[^}]*)\}")

LAYOUTS = (
    os.path.join("homework", "*", "*.tex"),
    os.path.join("chapters", "*", "homework", "*.tex"),
)

# A session's own write-up, an artifact at `docs/<slug>/writeup.tex`. It is no
# problem set -- `sets` never lists it -- and is found only by the session's pin.
DOCS_LAYOUT = os.path.join("docs", "*", "*.tex")
PINNABLE = LAYOUTS + (DOCS_LAYOUT,)
WRITEUP_SOURCE = "writeup.tex"

# The one template every write-up starts from: a session's, and a course's
# chapter notes and sets laid down by `board textbook scaffold`.
TEMPLATE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "tex", "writeup.tex.in")

# The build record the board's banner paints, in the session directory.
RECORD = "hw.json"


def _name_for(root, tex):
    """What to call this set: the folder that identifies it, not the file.

    `homework/hw04/hw04.tex` is hw04. `chapters/ch07-splitting-fields/homework/
    ch07-homework.tex` is ch07 -- the chapter is the identity there, and the long
    slug is decoration.
    """
    rel = os.path.relpath(tex, root).split(os.sep)
    if rel[0] in ("homework", "docs") and len(rel) >= 3:
        return rel[1]
    if rel[0] == "chapters" and len(rel) >= 2:
        m = re.match(r"(ch\d+)", rel[1])
        return m.group(1) if m else rel[1]
    return os.path.splitext(os.path.basename(tex))[0]


# WHAT A SET IS CALLED, AND WHICH CHAPTER IT IS FOR.
#
# `ch04` and `worksheet-field-extensions` are directory names, and a directory
# name is not a title. A person looking for "the two chapter 4 sets" is looking
# for the book problems and the worksheet, and on a map labelled with slugs only
# one of those two says chapter 4 anywhere.
#
# Both answers are derived, because a course that has to maintain a registry of
# its own worksheets has been given a chore rather than a tool:
#
#   THE TITLE comes off the source, which already carries one. A template writes
#   `% Worksheet --- Field Extensions and the Ring F[x]` into the banner and the
#   scaffolder writes `\section*{...}`; either is what its author calls it out
#   loud. A set named after its chapter is called after the chapter instead,
#   because "Ch 04 homework" is what that is.
#
#   THE CHAPTER comes off the name where the course numbers its sets that way,
#   off a declaration where the author wrote one, and off the slug otherwise:
#   `worksheet-field-extensions` minus its prefix is `field-extensions`, which
#   is chapter 4's own slug in `chapters.tsv`. A slug matching two chapters
#   matches neither -- `worksheet-automorphisms-splitting-fields` names two, and
#   a wrong chapter is worse than none.
#
# The declaration is the escape hatch and it is one line in the `.tex`, because
# the alternative for a set whose slug says nothing is that nothing can ever
# place it. It is read from a comment so it reaches no built document.
CHAPTER_DECLARED = re.compile(r"^\s*%+\s*chapter:\s*(\d+)\s*$", re.M)

# The set name a course numbers by chapter: `ch04`, `ch7`, `chapter-12`.
CHAPTER_NAMED = re.compile(r"^(?:ch|chapter)[-_]?0*(\d+)$", re.I)

# What a worksheet's directory is called before the part that names its topic.
SET_PREFIXES = ("worksheet-", "worksheet_", "hw-", "homework-", "set-", "ps-")

# A title in the source. The banner comment first, because both of this course's
# templates put it there and it is the line an author edits; then the headings a
# built document would show.
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


# A due date is not a title, and a scaffolder that wrote the name twice did not
# mean it as one. Both of these appear verbatim in this machine's courses.
_DUE = re.compile(r"\s*[.;,]?\s*Due\b[^.]*\.?\s*$", re.I)
_SAID_TWICE = re.compile(r"^(?P<one>.{3,40}?)\s+[—–-]+\s+(?P=one)\s*$")

# How long a title may be before a drawer row stops being readable. Cut on a
# word, because a title chopped mid-word reads as a rendering fault.
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
            # A banner rule of dashes matches the shape of a title and is not
            # one; so does a row of equals signs closing the block.
            if title and not set(title) <= set("-=_–— "):
                return title
    return ""


def _chapter_for(root, name, tex, text):
    """Which chapter this set is for, as an int, or `None`.

    Three routes, in order of how much they know: the course's own numbering,
    the author's declaration, then the slug. The slug route refuses an ambiguous
    match rather than guessing between two chapters.
    """
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
    from . import syllabus
    hits = []
    for c in syllabus.chapters(root):
        try:
            num = int(str(c.get("num") or "").strip())
        except ValueError:
            continue
        if str(c.get("slug") or "").strip().lower() == slug:
            hits.append(num)
    return hits[0] if len(hits) == 1 else None


def title_for(root, name, tex):
    """What to call this set on a map or in a list of documents.

    A set the course numbers by chapter is called after the number and nothing
    else: the chapter box beside it already carries the chapter's own title, and
    repeating it makes two long labels that differ by one word. Everything else
    is called what its source calls it.
    """
    found = CHAPTER_NAMED.match(name or "")
    if found:
        return "Ch %02d homework" % int(found.group(1))
    return _title_in(_read(tex)) or name


def sets(root):
    """Every problem set in this repository, newest last.

    Each carries `title` and `chapter` beside the identity fields: what a person
    calls it, and which chapter it belongs under, both derived from the source
    rather than recorded anywhere.
    """
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
    """The sheet as it was handed out, if the set keeps one.

    A homework sitting is not the assistant's to choose the problems for: they
    are assigned, and the assignment is a document. `homework/hwNN/assignment/`
    is where the courses put it, so point at what is actually there rather than
    letting an assistant infer a problem list from a chapter.
    """
    out = []
    for pattern in ("assignment/*", "*.pdf"):
        for path in sorted(glob.glob(os.path.join(set_dir, pattern))):
            if os.path.isfile(path) and not path.endswith((".aux", ".log", ".out")):
                out.append(path)
        if out:
            break
    return out


def _hints(text):
    """Set names a piece of prose could be naming.

    A session is opened with a human label -- "Ch 7 -- splitting fields",
    "Homework 4" -- and that is usually enough to say which set is meant.
    """
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
    """The problem set this session is about, or None if it cannot be settled.

    Pinned beats guessed, and an ambiguous guess is no answer at all -- compiling
    or filing handwriting into the wrong set is worse than saying which ones
    there are and stopping.
    """
    every = sets(root)
    found = _pinned(root, every, (state or {}).get("hw")) or _named(every, state)
    if found:
        return found
    if len(every) == 1:
        return every[0]
    return None


def bound(root, state):
    """The set this sitting is WRITING INTO, or None -- pinned or named, only.

    Narrower than `find`, and deliberately: `find` also falls back to the lone
    set in a course, which is the right answer for "compile the thing" and the
    wrong one for "put a homework line in front of the assistant every turn".
    A course with one set would then carry that line through a sitting about
    something else entirely, and a line that is sometimes noise stops being read.

    A session label naming a chapter IS a binding. `board writeup use` writes
    the pin, but a lecture that opens as "Ch 4 -- field extensions" and works
    the chapter's exercises is writing them up into ch04's file whether or not
    anybody ran that command, and the write-up is owed either way.
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
    """Every problem in a set, in the order it appears, and how far along it is.

    `stated` is whether the statement has been transcribed -- the templates ship
    a \\todo placeholder -- and `written` is whether anything but comments sits
    inside its solution region. The assistant fills both; this only reports.
    """
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
    """Every problem still without a written solution, in the file's own order.

    Which is the order the assignment has them, because the skeleton is laid down
    in one pass before any of it is filled: a `problem` environment per assigned
    label with a placeholder statement and an empty solution region. That is what
    makes "in order" a property of the document rather than a rule the assistant
    has to keep in its head while the student jumps about.

    It is the answer to two questions at once, and they used to have none. What is
    left to do -- and, once a student has skipped something, what has to be come
    back to. A skipped problem is not a finished one; it is an empty region with
    the rest of the sheet done around it, and that is exactly what this returns.
    """
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
        # What is left, in order, and the one to return to. A student may work
        # the sheet in any order they like; the document is written in the
        # sheet's, and the first empty region is where the next agreed answer
        # goes -- whether it was skipped an hour ago or has not been posed yet.
        "outstanding": outstanding(probs),
        "next": (outstanding(probs) or [None])[0],
    }


def compiled_pdf(root, tex_path):
    """Where the PDF for this `.tex` actually landed, or None.

    Three callers wanted this and all three had their own guess, and all three
    were wrong in the same way: look beside the source, then in `build/` NEXT TO
    the source. A course's `scripts/build.sh` does neither -- it walks up from
    the source to the nearest `chNN-*` / `hwNN` unit directory and compiles
    there, so the write-up for `chapters/ch03-rings/homework/ch03-homework.tex`
    comes out in `chapters/ch03-rings/build/`, one level ABOVE the directory
    being searched. The guess found nothing, `hw.json` recorded `"pdf": null` on
    a build that had just succeeded, and the board -- which offers the download
    only when there IS a PDF -- never offered it. The document was on disk the
    whole time and the button for it could not appear.

    So this looks where the build actually puts things, in the order it decides:
    beside the source, then `build/` beside it, then the unit's `build/`. And it
    matches the SOURCE'S OWN basename rather than taking any PDF in the
    directory -- a chapter's `build/` holds `ch03-notes.pdf` next to
    `ch03-homework.pdf`, and a glob that returns whichever came first hands
    somebody the reading for an evening they spent writing up exercises.
    """
    if not tex_path:
        return None
    base = os.path.splitext(os.path.basename(tex_path))[0]
    here = os.path.dirname(os.path.abspath(tex_path))

    places = [here, os.path.join(here, "build")]
    # Up to the nearest unit directory, the way scripts/build.sh does it. Bounded
    # by the repository, so a source outside it cannot walk the whole disk.
    stop = os.path.abspath(root)
    unit = here
    while unit != stop and os.path.dirname(unit) != unit:
        if re.match(r"^(ch\d+|hw\d+)", os.path.basename(unit)):
            places.append(os.path.join(unit, "build"))
            break
        unit = os.path.dirname(unit)

    for place in places:
        candidate = os.path.join(place, base + ".pdf")
        if os.path.isfile(candidate):
            return candidate
    return None



# ---------------------------------------------------------------------------
# the write-up: start one, add an agreed answer, build it
# ---------------------------------------------------------------------------
# A label goes into `\begin{problem}{...}`, the region markers and a PNG name,
# so it is matched rather than escaped: `7.1`, `13`, `2(b)`, `q-3`.
LABEL_RE = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._()-]{0,23}\Z")

# The line on stdin between the statement and the argument.
SPLIT = "---"

# A fenced code block in a statement or an argument: set verbatim, which needs
# no package and no shell-escape.
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

    `(record, made)`. The bound set (pinned or named) is written in place, its
    doc.json listing the session. Else a new artifact, `docs/<slug>/writeup.tex`
    from the template, `<slug>` from `title`, the session's title, its chapter
    label, or its id. ValueError where `root` cannot hold one.
    """
    state = state or {}
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

    The argument goes in the solution region for `label`, replacing what was
    there. The statement goes in the problem environment when it still holds
    the `\\todo` placeholder or nothing; a transcribed statement is kept. A
    label the file does not have gets a problem and a region appended before
    `\\end{document}`, so a course set is written in the sheet's order and a
    session's write-up in the order answers were agreed.

    `({label, statement, region}, None)`, or `(None, why)` with nothing written.
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
