"""walk.py -- what a walkthrough is held over.

A walkthrough is the sitting for machinery that ALREADY EXISTS. The board had
no such thing, and the gap is not a small one: every sitting it did have ends in
the student producing something -- a proof, a problem written up, an answer to a
question set cold -- and in a working project most of what has to be understood
was written months ago and is not going to be written again. A tutor with only
those sittings does the one thing it can do, which is manufacture exercises, and
there is a card in PSYCH-ASR that proves it: invented diarization arithmetic on
fictional numbers, skipped twice, in a repository whose owner wanted the
correction algorithm sitting in `transcript/corrections.py` explained to them.

So the scope of a walkthrough is a piece of the repository's own source, and the
lesson is reading it: predict what this returns, say which branch runs, trace
this input through it by hand. That is not a new teaching method -- it is the
hand-check ladder out of live/TEACHING.md pointed at a file instead of at a
definition, and TEACHING.md already describes it as a rung before a change. It
is a sitting of its own now because in these repositories it is the whole of the
work rather than the approach to it.

What this module owns, and it is deliberately the same thing `review.py` owns:
the list of what can be named, and the rule that a name arriving from the board
is checked against that list before it reaches anything. Nothing is registered,
nothing is declared, and nothing invented reaches the tutor's prompt.

Standard library only, like everything else.
"""

import os
import re
import time

from . import review

# What a walkthrough can be held over: source, in the languages these
# repositories are actually written in. A document is not machinery -- a README
# is read by reading it, and a walkthrough over one would be a lecture with
# extra steps.
SOURCE = (".py", ".go", ".js", ".mjs", ".ts", ".jsx", ".tsx", ".R", ".r",
          ".sh", ".bash", ".lean", ".sql", ".jl", ".rs", ".c", ".h", ".cpp",
          ".hpp", ".java", ".m")

# Directories that hold no machinery of this repository's own: `review.IGNORE`
# is the same judgement made for the same reason, and the two must not be
# allowed to disagree about what `node_modules` is.
# `slurm_jobs` is deliberately NOT here. A job script is machinery in these
# repositories -- it is where the resource ask, the array shape and the arguments
# the pipeline actually runs with live -- and it is a thing somebody genuinely
# needs walked through.
IGNORE = set(review.IGNORE) | {"data", "test_data", "results", "notebooks",
                               "latex", "textbook", "chapters",
                               "handwritten", "transcripts", "references"}

# A file with nothing in it is not a walkthrough, and a generated one is not
# either. Both are offered as choices nobody would make.
MIN_BYTES = 200

# A picker on a tablet scrolls; a repository with a thousand source files is
# still not a thing to be offered whole. The largest of these repositories has
# 188 and this is comfortably past it, so the cap is a guard rather than a
# policy.
MAX_UNITS = 250

# How a definition of a given name is recognised, per language. This is a grep
# and not a parser, and that is a decision rather than a shortcut: parsing five
# languages to answer "is there a thing called `grade` in here" is a dependency
# and a maintenance burden for a question a person answers by looking for the
# same line. What it must never do is say yes when there is no such definition,
# which is why every pattern is anchored at the start of a line.
DEFINITION = {
    ".py": r"^\s*(?:async\s+def|def|class)\s+%s\b",
    ".go": r"^\s*(?:func(?:\s+\([^)]*\))?|type)\s+%s\b",
    ".js": r"^\s*(?:export\s+)?(?:async\s+)?(?:function|class|const|let|var)\s+%s\b",
    ".lean": r"^\s*(?:theorem|lemma|def|structure|instance)\s+%s\b",
    ".sh": r"^\s*(?:function\s+)?%s\s*\(\)",
    ".R": r"^\s*%s\s*(?:<-|=)\s*function\b",
    ".rs": r"^\s*(?:pub\s+)?(?:fn|struct|enum|trait|impl)\s+%s\b",
}
DEFINITION[".mjs"] = DEFINITION[".ts"] = DEFINITION[".jsx"] = DEFINITION[".tsx"] = DEFINITION[".js"]
DEFINITION[".bash"] = DEFINITION[".sh"]
DEFINITION[".r"] = DEFINITION[".R"]


# A SHEBANG IS AS GOOD A DECLARATION AS A SUFFIX, and it is what `file(1)`
# would use. `SOURCE` keys on the extension, and the entire surface of colibrì
# is `bin/coli`, `bin/coli-up`, `bin/coli-ask` and `bin/coli-code` -- bash
# scripts with a `#!` line and no suffix at all. So a walkthrough of that
# workspace offered six files and not one of them was the one you would ask for.
#
# Which language it is comes off the same line, because `_has_definition` has to
# know: a symbol named inside `bin/coli-up` is looked for with the `.sh`
# patterns, and a name it cannot check is a name it will not carry.
#
# `SCRIPT` is the answer for a script whose interpreter nothing here recognises.
# It is deliberately not a key in `DEFINITION`: the file is still machinery and
# is still offered, and a symbol inside it simply cannot be verified. It is spelt
# `#!` because that is the only thing the file actually said about itself.
SCRIPT = "#!"

# What an interpreter on a `#!` line means for the patterns in `DEFINITION`. The
# whole line is searched rather than the last word of it, so `#!/usr/bin/env
# python3` and `#!/bin/bash` both land -- and the order matters for one pair:
# `sh` is a substring of `bash`, so `bash` is asked first.
INTERPRETERS = (
    ("python", ".py"),
    ("bash", ".sh"),
    ("zsh", ".sh"),
    ("Rscript", ".R"),
    ("node", ".js"),
    ("julia", ".jl"),
    ("sh", ".sh"),
)

# How much of a file is read to find its shebang. A shebang is the first line or
# there is no shebang; reading a couple of hundred bytes rather than one line is
# what stops a file with no newline in it at all being read whole.
SHEBANG_BYTES = 256


def _shebang(root, rel):
    """What a `#!` line declares this file to be, or "".

    `""` means it declared nothing: no shebang, so not machinery this can name.
    Otherwise the extension the interpreter stands in for, or `SCRIPT` where the
    interpreter is one `INTERPRETERS` does not list.

    Asked only of a file with NO extension, so nothing here can override what a
    suffix already said.
    """
    try:
        with open(os.path.join(root, rel), "rb") as fh:
            first = fh.read(SHEBANG_BYTES).split(b"\n", 1)[0]
    except OSError:
        return ""
    line = first.decode("utf-8", "replace")
    if not line.startswith(SCRIPT):
        return ""
    for word, ext in INTERPRETERS:
        if word in line:
            return ext
    return SCRIPT


def _language(root, rel):
    """What this file is, as a key `SOURCE` and `DEFINITION` understand.

    The extension where there is one, what the `#!` line declares where there is
    not, and `""` for a file that said nothing at all. One function, because
    "which language is this" is asked by both `_walkable` and `_has_definition`
    and the two must give the same answer.
    """
    ext = os.path.splitext(rel)[1]
    return ext if ext else _shebang(root, rel)


def _walkable(root, rel):
    """Is this path a piece of machinery somebody could be walked through?

    An extension answers first and a `#!` line answers for a file that has none.
    A README has an extension and is refused by it; a licence, a lock file or a
    data dump has neither, and is refused for having said nothing.
    """
    name = os.path.basename(rel)
    if name.startswith(".") or name == "__init__.py":
        # An `__init__.py` is a namespace rather than a thing that does
        # anything, and offering forty of them buries the files that do.
        return False
    said = _language(root, rel)
    if said not in SOURCE and said != SCRIPT:
        return False
    try:
        return os.path.getsize(os.path.join(root, rel)) >= MIN_BYTES
    except OSError:
        return False


# Every other discovery on this board is a directory listing or a `stat`, and is
# redone on every payload because it costs nothing to. This one is a walk of the
# whole repository, and the payload is rebuilt on every change and polled four
# times a second -- so it is remembered for a little while. Source files do not
# appear on a quarter-second boundary, and a file added during a sitting is
# offered by the time anybody has finished writing it.
CACHE_SECONDS = 30
_cache = {}


def units(root):
    """Every source file in this repository, as something a walkthrough can cover.

    A file rather than a function, because a file is a thing that exists on disk
    and a function is a thing found by reading one. A walkthrough usually starts
    at one function inside one file, and `resolve` will take its name and carry
    it -- but what is OFFERED is what can be listed without reading anything,
    which is the same discipline as every other discovery here.
    """
    root = os.path.abspath(root)
    hit = _cache.get(root)
    if hit and time.time() - hit[0] < CACHE_SECONDS:
        return hit[1]
    found = _scan(root)
    _cache[root] = (time.time(), found)
    return found


def _scan(root):
    out = []
    for here, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs
                         if not d.startswith(".") and d not in IGNORE)
        rel_dir = os.path.relpath(here, root)
        rel_dir = "" if rel_dir == "." else rel_dir
        for name in sorted(files):
            rel = os.path.join(rel_dir, name) if rel_dir else name
            if not _walkable(root, rel):
                continue
            out.append({"name": rel, "label": rel, "short": name,
                        "dir": rel_dir or ".", "kind": "file",
                        "path": rel, "symbol": ""})
            if len(out) >= MAX_UNITS:
                return out
    return out


def kind(root):
    """`files`, or nothing at all to walk through."""
    return "files" if units(root) else ""


def _has_definition(root, rel, symbol):
    """Does this file actually define something by that name?

    Asked before a symbol is carried into a sitting label or a tutor's prompt.
    A walkthrough announced as being over `psych_asr.evaluate.grade` when there
    is no `grade` in that file sends the tutor looking for machinery that is not
    there, and it will find something else and teach that instead.
    """
    pattern = DEFINITION.get(_language(root, rel))
    if not pattern:
        return False
    rx = re.compile(pattern % re.escape(symbol), re.MULTILINE)
    try:
        with open(os.path.join(root, rel), "r", encoding="utf-8",
                  errors="replace") as fh:
            return bool(rx.search(fh.read()))
    except OSError:
        return False


def _candidates(name):
    """Every file path a typed or tapped name could mean, most specific first.

    A person names machinery the way their language names it. In Python that is
    `psych_asr.evaluate.grade`, and the last component is as likely to be the
    function inside the module as it is to be the module -- so both readings are
    produced here, and the caller keeps whichever one is on disk.
    """
    raw = str(name or "").strip().strip("/")
    if not raw:
        return []
    out = []

    # `path/to/file.py::grade`, which is how a scope records a symbol once it
    # has been resolved, and how somebody types one unambiguously.
    if "::" in raw:
        path, _, symbol = raw.partition("::")
        return [(path.strip(), symbol.strip())]

    out.append((raw, ""))
    if os.path.splitext(raw)[1] in SOURCE:
        # Already a filename: a dot in it is an extension, not a module
        # separator, and splitting on it would produce nonsense.
        return out

    parts = raw.split(".")
    if len(parts) > 1:
        stem = "/".join(parts)
        for ext in SOURCE:
            out.append((stem + ext, ""))
        if len(parts) > 2:
            # The last component read as a name INSIDE the module before it.
            head, symbol = "/".join(parts[:-1]), parts[-1]
            for ext in SOURCE:
                out.append((head + ext, symbol))
    return out


def resolve(root, wanted):
    """Match names from a request against the source this repository has.

    Returns (chosen, unknown), the same contract as `review.resolve`: a name
    that matches nothing comes back rather than being dropped, because walking
    through two files when three were named is a worse answer than saying which
    one was not recognised.

    A name is matched as a repository-relative path, as a bare filename where
    that is unambiguous, or as a dotted module path with an optional symbol on
    the end -- `psych_asr.evaluate.grade` finds the module, and
    `psych_asr.transcript.corrections.apply_corrections` finds the module and
    carries the function. A symbol is kept only when the file really defines it.
    """
    every = units(root)
    by_path = {u["path"].lower(): u for u in every}
    by_base = {}
    for u in every:
        # A bare filename is only a name if the repository has one of them. Two
        # `config.py` and it is ambiguous, and an ambiguous name resolves to
        # nothing rather than to whichever was walked first.
        by_base.setdefault(u["short"].lower(), []).append(u)

    chosen, unknown, seen = [], [], set()
    for name in wanted or []:
        found = None
        for path, symbol in _candidates(name):
            key = path.lower()
            u = by_path.get(key)
            if u is None:
                hits = by_base.get(key) or []
                u = hits[0] if len(hits) == 1 else None
            if u is None:
                continue
            if symbol and not _has_definition(root, u["path"], symbol):
                # The file is real and the name inside it is not. Keep looking:
                # `a.b.c` may yet be the module `a/b/c.py`, which is the reading
                # produced after this one.
                continue
            found = dict(u, symbol=symbol)
            break
        if not found:
            unknown.append(name)
            continue
        if (found["path"], found["symbol"]) in seen:
            continue
        seen.add((found["path"], found["symbol"]))
        found["name"] = label(found)
        found["label"] = found["name"]
        found["short"] = found["symbol"] or found["short"]
        chosen.append(found)

    order = {u["path"]: i for i, u in enumerate(every)}
    chosen.sort(key=lambda u: (order.get(u["path"], 0), u["symbol"]))
    return chosen, unknown


def label(u):
    """What one piece of scope is called, everywhere it is named.

    `psych_asr/evaluate/grade.py::grade` -- the file and, where there is one,
    the thing inside it. One spelling, in the sitting label, on the strip, in
    `state.json` and in the tutor's prompt, so that the scope written when the
    sitting opened is the same string that is re-resolved when the board asks
    what it covers.
    """
    return u["path"] + ("::" + u["symbol"] if u.get("symbol") else "")


def scope(root, state):
    """What the sitting in front of us is a walkthrough of, checked on the way out.

    Re-resolved rather than trusted, for the reason `review.scope` is: a file
    can be renamed or a function deleted between the sitting being opened and
    the board asking what it covers, and a scope naming machinery that is no
    longer there would send the tutor to read a file that does not exist.
    """
    chosen, _ = resolve(root, (state or {}).get("walk") or [])
    return chosen


def sitting_label(chosen):
    """What `board open` files this sitting under, and what the badge reads.

    Short names, because it goes in a title bar beside a course name. A
    walkthrough is usually over one thing, occasionally two, and past three it
    is counted rather than listed -- a label is an identifier and the scope
    itself is on the strip underneath.
    """
    if not chosen:
        return "Walkthrough"
    if len(chosen) <= 3:
        return "Walkthrough — " + ", ".join(u["short"] for u in chosen)
    return "Walkthrough — %d files" % len(chosen)


def status(root, state):
    """What the board shows, and what the command line prints.

    None when there is no source in this repository at all, which is a real
    answer about a narrative repository and not an empty list.
    """
    every = units(root)
    if not every:
        return None
    chosen = scope(root, state)
    return {
        "of": "files",
        "units": every,
        "scope": [u["name"] for u in chosen],
        "chosen": chosen,
        "total": len(every),
        "label": sitting_label(chosen),
    }
