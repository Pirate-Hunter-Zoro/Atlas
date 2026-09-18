"""symbols.py -- what one file DEFINES, and what each definition uses.

`map.py` draws the repository at the grain of a directory: `psych_asr/evaluate`
is a box, and the arrow into it carries twenty-five imports. That is the right
picture for finding your way around and the wrong one for *"when we work on a
TODO, it's obvious what moving parts we'll be affecting"* -- a directory is not
a moving part. The things that move are the classes and the functions, which is
why an IntelliJ diagram is worth what it is worth: its nodes are the things and
its arrows are uses.

So this module answers one question, for one file: what is defined in here, and
what does each of those definitions reach for. Nothing else. `map.py` decides
what to draw with the answer.

HOW FAR WITHOUT A PARSER, AND THE ANSWER IS NOT THE SAME IN EVERY LANGUAGE.

  * **Python is parsed**, with `ast` from the standard library -- which is this
    codebase's own rule in every module, and most of this repository is Python.
    A parser gives classes, functions, decorators, base classes and the names a
    body actually mentions EXACTLY rather than approximately.
  * **Everything else is grepped**, with `walk.DEFINITION` -- the per-language
    pattern that already answers *"is there a thing called X defined here"* and
    is already trusted to check a walkthrough's symbol before it reaches a
    prompt. It is anchored at the start of a line, so it is honest about
    definitions.

A regex is honest about definitions and a liar about calls. So a grepped file
reports its definitions and NO uses at all, and says `exact` is false -- which
`map.py` puts on the diagram, because a Lean box nobody may trust as much as a
Python one has to say so rather than look identical.

Standard library only, like everything else.
"""

import ast
import os
import re

from . import walk

# What a definition may be. Three words, because a picture with six kinds of
# box on it is a legend rather than a diagram -- and because a module-level
# table is a different thing from a function and drawing it as one is a lie
# about what moves when you change it.
KINDS = ("class", "function", "value")

# Which of those three a declaring keyword means. `walk.DEFINITION` matches the
# keyword as well as the name, so the keyword is already in hand: `const els =
# {...}` in a JavaScript file is a value, and calling it a function because the
# pattern that found it also finds functions is the sort of small lie a diagram
# is read as truth.
DECLARES = (
    ("class", ("class", "struct", "trait", "enum", "impl", "structure",
               "interface", "type")),
    ("value", ("const", "let", "var")),
)

# How many definitions one file may put on a picture. Past this it is the ugly
# grid again with more effort, and the count says it was capped rather than
# letting somebody believe a forty-symbol module has forty symbols.
MAX_SYMBOLS = 40

# How long a symbol's one-line purpose may be, matching `map.DOES`. Repeated
# rather than imported because `map` imports this and the cycle is not worth a
# constant.
SAYS = 110

# How far above a definition a leading comment may start. A `//` or `#` block
# immediately above a function is the sentence its author wrote about it, and
# it is the only `does` a grepped language gets.
COMMENT_LINES = 4

# Which comment a language writes. Keyed the way `walk.DEFINITION` is keyed.
COMMENT = {".go": "//", ".js": "//", ".mjs": "//", ".ts": "//", ".jsx": "//",
           ".tsx": "//", ".rs": "//", ".c": "//", ".h": "//", ".cpp": "//",
           ".hpp": "//", ".java": "//", ".lean": "--",
           ".sh": "#", ".bash": "#", ".R": "#", ".r": "#", ".jl": "#"}


def _short(text, limit=SAYS):
    text = re.sub(r"\s+", " ", str(text or "").strip())
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    return (cut or text[:limit]).rstrip(" ,;:.") + "…"


def _first_sentence(said):
    said = re.sub(r"\s+", " ", str(said or "").strip())
    if not said:
        return ""
    return _short(re.split(r"(?<=[.!?])\s+", said, maxsplit=1)[0])


def _read(root, rel):
    try:
        with open(os.path.join(root, rel), "r", encoding="utf-8",
                  errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


# ---------------------------------------------------------------------------
# Python, parsed
# ---------------------------------------------------------------------------
def _names_in(node):
    """Every name the body of one definition mentions, deduplicated.

    Both halves of a dotted reference: `naming.stem` contributes `naming` and
    `stem`, because which of the two is the thing that was imported depends on
    how the import was written and the caller resolves it either way.
    """
    out = []
    for sub in ast.walk(node):
        got = ""
        if isinstance(sub, ast.Name):
            got = sub.id
        elif isinstance(sub, ast.Attribute):
            got = sub.attr
        if got and got not in out:
            out.append(got)
    return out


def _bases_of(node):
    """The base classes of a class definition, by the name they are written as."""
    out = []
    for base in getattr(node, "bases", []) or []:
        got = base.id if isinstance(base, ast.Name) else (
            base.attr if isinstance(base, ast.Attribute) else "")
        if got and got not in out:
            out.append(got)
    return out


def _python(root, rel, text):
    """Every top-level class and function in a Python file, with what it uses.

    TOP LEVEL ONLY. A class's methods are a third depth below a third depth, and
    a diagram is a thing somebody looks at rather than unfolds for ever -- so a
    class box says how many methods it has instead, which is the fact somebody
    reads off an IntelliJ diagram anyway.
    """
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        # A file that will not parse is not a file to guess about. It reports
        # nothing and says it is not exact, which is the honest pair.
        return {"exact": False, "defines": [], "imports": {},
                "why": "this file would not parse"}

    # WHICH LOCAL NAME CAME FROM WHERE. `from ..artifacts.naming import stem`
    # makes `stem` a name in this file that belongs to another one, and that is
    # the whole of how a use becomes an arrow that leaves the module.
    brought = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            where = ("." * (node.level or 0)) + (node.module or "")
            for alias in node.names:
                brought[alias.asname or alias.name] = (where, alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                brought[alias.asname or alias.name.split(".")[0]] = \
                    (alias.name, "")

    out = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            kind = "class"
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            kind = "function"
        else:
            continue
        says = _first_sentence(ast.get_docstring(node) or "")
        if kind == "class":
            methods = len([b for b in node.body
                           if isinstance(b, (ast.FunctionDef,
                                             ast.AsyncFunctionDef))])
            if not says and methods:
                says = "%d method%s" % (methods, "" if methods == 1 else "s")
        uses = [n for n in _names_in(node) if n != node.name]
        out.append({
            "name": node.name,
            "kind": kind,
            "line": node.lineno,
            "does": says,
            "uses": uses,
            "bases": _bases_of(node) if kind == "class" else [],
            "private": node.name.startswith("_"),
        })
    return {"exact": True, "defines": out[:MAX_SYMBOLS], "imports": brought,
            "capped": len(out) > MAX_SYMBOLS, "why": ""}


# ---------------------------------------------------------------------------
# everything else, grepped
# ---------------------------------------------------------------------------
# The same per-language patterns `walk.DEFINITION` holds, with the name left
# open instead of a name being checked. One source of truth for "what a
# definition of X looks like", asked the other way round.
_ANY = r"[A-Za-z_][A-Za-z0-9_]*"


def _grepped(root, rel, text, language):
    """Every definition a line-anchored pattern can see, and no uses at all.

    A regex is honest about definitions and a liar about calls, so this reports
    the boxes and refuses to draw arrows between them. `exact` is false and
    `map.py` says so on the picture.
    """
    pattern = walk.DEFINITION.get(language)
    if not pattern:
        return {"exact": False, "defines": [], "imports": {},
                "why": "nothing here knows how this language declares things"}
    rx = re.compile(pattern % ("(?P<name>" + _ANY + ")"))
    mark = COMMENT.get(language, "")
    lines = text.splitlines()
    out, seen = [], set()
    for i, line in enumerate(lines):
        m = rx.match(line)
        if not m:
            continue
        name = m.group("name")
        if name in seen:
            continue
        seen.add(name)
        said_by = line[:m.start("name")]
        kind = "function"
        for word, keywords in DECLARES:
            if any(re.search(r"\b%s\b" % k, said_by) for k in keywords):
                kind = word
                break
        says = ""
        if mark:
            said = []
            for back in range(1, COMMENT_LINES + 1):
                if i - back < 0:
                    break
                before = lines[i - back].strip()
                if not before.startswith(mark):
                    break
                said.insert(0, before[len(mark):].strip())
            says = _first_sentence(" ".join(said))
        out.append({"name": name, "kind": kind, "line": i + 1,
                    "does": says, "uses": [], "bases": [],
                    "private": name.startswith("_")})
    return {"exact": False, "defines": out[:MAX_SYMBOLS], "imports": {},
            "capped": len(out) > MAX_SYMBOLS,
            "why": "found by pattern rather than parsed, so its arrows are "
                   "not drawn"}


# ---------------------------------------------------------------------------
# the one question this module answers
# ---------------------------------------------------------------------------
def of(root, rel):
    """What this file defines, and what each definition uses.

    `exact` is the field that matters as much as the list: true where a parser
    read the file, false where a pattern did. A caller drawing a picture has to
    be able to say which, because a box nobody may trust as much as its
    neighbour must not look identical to it.

    `imports` maps a name used in this file to (where it came from, what it is
    called there), and is empty for a grepped language. It is what turns a use
    into an arrow that leaves the file.
    """
    language = walk._language(root, rel)
    text = _read(root, rel)
    if not text:
        return {"exact": False, "defines": [], "imports": {}, "capped": False,
                "why": "this file could not be read"}
    if language == ".py":
        return _python(root, rel, text)
    return _grepped(root, rel, text, language)


def exact(root, rel):
    """Would this file be parsed, or only grepped? Asked without reading it."""
    return walk._language(root, rel) == ".py"
