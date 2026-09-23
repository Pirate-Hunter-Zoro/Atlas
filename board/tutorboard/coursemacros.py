"""The macros a COURSE writes in, so the glass renders what the .tex renders.

The board typesets twice and the two engines were fed different vocabularies.
LaTeX gets the course's own `latex/coursemacros.sty` and then `board-macros.tex`,
whose every definition is `\\providecommand` -- so the course wins and the board
fills gaps. KaTeX in the browser got `web/macros.js` and nothing else, so a macro
the course defines and the board has never heard of reached the glass as source.

Measured on 23 September 2026 against `courses/Probability`: 33 of its 44 macros
were unknown to the browser, and two more were known at the WRONG ARITY, which is
the worse half. `\\EE` takes an argument in that course and none in the board's
table, so `\\EE{X}` drew as a bare blackboard E with the brackets silently gone:
a card that looks typeset and says something else. `\\E[...]` merely drew as
`\\E[...]`, which at least announces itself.

So this reads the course's file and the payload carries it. The rule is the one
the TeX side already follows and it now holds on both: **the course's own
definition wins, and the board fills what the course did not define.**

A PARSER RATHER THAN AN EXECUTION, and it is deliberately a small one.
`\\newcommand{\\name}[n]{body}` and its `\\renewcommand` and `\\providecommand`
spellings, with balanced braces counted rather than matched by a regex, because a
body is full of them. Anything it cannot read is SKIPPED rather than guessed at:
a macro missing from the glass is the defect this fixes, and a macro mis-read
into the glass is a worse one.

Nothing here validates the body against KaTeX. It cannot -- that engine is in the
browser -- and it does not need to: `throwOnError` is false at the call site, so a
body KaTeX dislikes colours one formula rather than blanking the lesson.
"""

import os
import re
import time


# `\newcommand{\name}[2][opt]{...}` -- the name, the arity, and where the body
# starts. The optional-argument default is matched so it can be REFUSED: KaTeX
# has no equivalent, and a macro whose first argument is optional would come out
# with its arguments shifted by one, which is the silent kind of wrong.
_DEF = re.compile(
    r"\\(?:new|renew|provide)command\s*\{?\s*\\([A-Za-z]+)\s*\}?"
    r"\s*(?:\[(\d+)\])?\s*(\[[^\]]*\])?\s*\{")

TTL = 30.0
_CACHE = {}


def _body(text, open_brace):
    """The balanced `{...}` starting at `open_brace`, or None. Braces counted.

    `\\{` and `\\}` are literal braces in a body -- `\\set` is defined with them
    -- so a backslash-escaped brace does not move the depth.
    """
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
    """`{"\\\\name": "body"}` for every definition this can read with confidence.

    KaTeX takes the body verbatim with `#1`-style parameters, which is the same
    shape LaTeX uses, so no rewriting is needed and none is done.
    """
    out = {}
    for m in _DEF.finditer(text or ""):
        name, arity, optional = m.group(1), m.group(2), m.group(3)
        if optional:
            continue                 # no KaTeX equivalent; see the module note
        body = _body(text, m.end() - 1)
        if body is None:
            continue
        # A definition of something KaTeX owns -- `\qedhere`, a page-furniture
        # length -- is not mathematics and is left alone. The test is whether the
        # body would mean anything in a formula, and the cheap honest version of
        # that is: skip what the course itself only uses in its preamble.
        if name in _NOT_MATHS:
            continue
        out["\\" + name] = body.strip()
    return out


# Page furniture. These are defined in a `.sty` because that is where a document
# class wants them, and they mean nothing inside `$...$`.
_NOT_MATHS = frozenset((
    "headrulewidth", "footrulewidth", "baselinestretch", "arraystretch",
    "labelitemi", "labelenumi", "thesection", "thepage",
))


def for_workspace(root):
    """The course macros for this workspace, or {}. Cached; never raises.

    The hub builds a payload four times a second and this is a file read and a
    parse, so it is cached on the file's mtime -- a macro added mid-sitting
    appears within the TTL rather than needing a restart, and an unchanged file
    costs one `stat`.
    """
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
