"""The macros a COURSE writes in, so the glass renders what the .tex renders.

LaTeX reads the course's `latex/coursemacros.sty`, then `board-macros.tex`
(all `\\providecommand`); KaTeX gets `web/macros.js` plus this, so the same
rule holds on the glass: the course's own definition wins, and the board
fills what the course did not define.

The constraint: a small parser, never execution. `\\newcommand` and its
`\\renew`/`\\provide` spellings with braces counted; anything it cannot read
is skipped rather than guessed, because a misread macro on the glass is
worse than a missing one. KaTeX's `throwOnError` is false, so a bad body
colours one formula.
"""

import os
import re
import time


# `\newcommand{\name}[2][opt]{...}`. An optional-argument default is matched
# so it can be refused: KaTeX would shift the arguments by one.
_DEF = re.compile(
    r"\\(?:new|renew|provide)command\s*\{?\s*\\([A-Za-z]+)\s*\}?"
    r"\s*(?:\[(\d+)\])?\s*(\[[^\]]*\])?\s*\{")

TTL = 30.0
_CACHE = {}


def _body(text, open_brace):
    """The balanced `{...}` starting at `open_brace`, or None. `\\{` and `\\}`
    do not move the depth."""
    depth, i, n = 0, open_brace, len(text)
    while i < n:
        c = text[i]
        if c == "\\":
            i += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[open_brace + 1:i]
        i += 1
    return None


def parse(text):
    """`{"\\\\name": "body"}` for every definition this can read with
    confidence; KaTeX takes `#1`-style bodies verbatim."""
    out = {}
    for m in _DEF.finditer(text or ""):
        name, arity, optional = m.group(1), m.group(2), m.group(3)
        if optional:
            continue                 # no KaTeX equivalent; see the module note
        body = _body(text, m.end() - 1)
        if body is None:
            continue
        # Skip what only the preamble uses.
        if name in _NOT_MATHS:
            continue
        out["\\" + name] = body.strip()
    return out


# Page furniture: meaningless inside `$...$`.
_NOT_MATHS = frozenset((
    "headrulewidth", "footrulewidth", "baselinestretch", "arraystretch",
    "labelitemi", "labelenumi", "thesection", "thepage",
))


def for_workspace(root):
    """The course macros for this workspace, or {}. Cached on the file's
    mtime; never raises."""
    path = os.path.join(str(root or ""), "latex", "coursemacros.sty")
    try:
        stamp = os.stat(path).st_mtime_ns
    except OSError:
        return {}
    hit = _CACHE.get(path)
    now = time.time()
    if hit and hit[0] == stamp and now - hit[1] < TTL:
        return hit[2]
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            got = parse(fh.read())
    except OSError:
        got = {}
    _CACHE[path] = (stamp, now, got)
    return got


def forget():
    """Drop the cache. For a test."""
    _CACHE.clear()
