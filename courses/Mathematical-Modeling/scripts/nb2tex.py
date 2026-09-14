#!/usr/bin/env python3
"""nb2tex.py -- turn a Wolfram .nb into a printable, turn-in-able .tex.

    python3 scripts/nb2tex.py lessons/lesson-01/work/"Adv Lesson 01 Exercises.nb"
    python3 scripts/nb2tex.py IN.nb -o OUT.tex --title "Lesson 01 exercises"

WHY THIS EXISTS. The submission format for this course is a printed notebook
with the output cleared -- not a .nb file (README, "Submission format"). Wolfram
Engine can print one itself, but only once it is activated, and activation needs
an interactive terminal that an assistant does not have. This route needs
nothing but pdflatex, so a submission can be produced on any machine.

WHAT IT DOES NOT DO. Output cells are dropped, always: that is the submission
format, and it is also the only honest thing to do for a notebook nothing has
evaluated. Input cells are transcribed, never authored -- every character in the
output came out of the .nb.

TWO-DIMENSIONAL FORMS. A notebook stores typeset input as boxes: FractionBox for
a built-up fraction, SubscriptBox on \\[PartialD] for the partial-derivative
template, and so on. Those are printed here in the equivalent LINEAR syntax,
which is what the notebook's own opening cell says the exercises were written in
and which evaluates identically. Nothing is reinterpreted beyond that: Wolfram
full names that have no linear spelling are left exactly as the file stores them.
"""

import argparse
import os
import re
import sys


# --- a small parser for the subset of Wolfram syntax a .nb file uses -------
# Standard library only, like everything else here. This reads expressions
# (heads, brackets, lists, strings, rules) and nothing more -- it is not an
# evaluator and must never become one.

class Tok:
    def __init__(self, src):
        self.s = src
        self.i = 0

    def peek(self):
        while self.i < len(self.s) and self.s[self.i] in " \t\r\n":
            self.i += 1
        return self.s[self.i] if self.i < len(self.s) else ""

    def take(self):
        c = self.peek()
        self.i += 1
        return c


def parse(t):
    """One expression. Returns a str (atom), or ('call', head, args), or a list."""
    c = t.peek()
    if c == '"':
        return parse_string(t)
    if c == "{":
        t.take()
        return parse_seq(t, "}")
    if c == "(":                      # parenthesised group; only grouping matters
        t.take()
        inner = parse_seq(t, ")")
        return inner[0] if len(inner) == 1 else inner
    atom = parse_atom(t)
    if t.peek() == "[":
        t.take()
        return ("call", atom, parse_seq(t, "]"))
    return atom


def parse_seq(t, close):
    out = []
    if t.peek() == close:
        t.take()
        return out
    while True:
        out.append(parse_expr(t))
        c = t.take()
        if c == close:
            return out
        if c != ",":
            # Malformed input: stop rather than loop. Callers get what parsed.
            return out


def parse_expr(t):
    """An expression, plus the one operator that appears at argument level: ->."""
    left = parse(t)
    while True:
        save = t.i
        c = t.peek()
        if c == "-" and t.s[t.i:t.i + 2] == "->":
            t.i += 2
            right = parse(t)
            left = ("rule", left, right)
            continue
        if c == ":" and t.s[t.i:t.i + 2] == ":>":
            t.i += 2
            right = parse(t)
            left = ("rule", left, right)
            continue
        t.i = save
        return left


def parse_string(t):
    t.take()                                   # opening quote
    out = []
    while t.i < len(t.s):
        c = t.s[t.i]; t.i += 1
        if c == "\\":
            nxt = t.s[t.i] if t.i < len(t.s) else ""
            if nxt == "[":                     # \[Pi] and friends: keep whole
                j = t.s.index("]", t.i) + 1
                out.append(t.s[t.i - 1:j])
                t.i = j
            elif nxt == "n":
                out.append("\n"); t.i += 1
            elif nxt == "t":
                out.append("\t"); t.i += 1
            else:
                out.append(nxt); t.i += 1
        elif c == '"':
            break
        else:
            out.append(c)
    return "".join(out)


def parse_atom(t):
    start = t.i
    while t.i < len(t.s) and (t.s[t.i].isalnum() or t.s[t.i] in "_$.`'\\"):
        t.i += 1
    if t.i == start:                           # punctuation we do not model
        t.i += 1
    return t.s[start:t.i]


# --- boxes to linear Mathematica ------------------------------------------

NAMES = {
    "\\[Pi]": "Pi",
    "\\[ExponentialE]": "E",
    "\\[ImaginaryI]": "I",
    "\\[Infinity]": "Infinity",
    "\\[Equal]": "==",
    "\\[Rule]": "->",
    "\\[LessEqual]": "<=",
    "\\[GreaterEqual]": ">=",
    "\\[NotEqual]": "!=",
    "\\[Prime]": "'",
    "\\[IndentingNewLine]": "\n",
    "\\[LineSeparator]": "\n",
}

ATOMIC = re.compile(r"^[A-Za-z0-9_$.]+$|^\w+\[.*\]$")


def atomic(s):
    return bool(ATOMIC.match(s)) or (s.startswith("(") and s.endswith(")"))


def wrap(s):
    return s if atomic(s) else "(%s)" % s


def head_of(e):
    return e[1] if isinstance(e, tuple) and e[0] == "call" else None


NUM_PRECISION = re.compile(r"^(\d*\.?\d*)`+[0-9.]*$")


def box(e):
    """Render a box expression as linear Mathematica input."""
    if isinstance(e, str):
        # A trailing backtick is a number's precision mark. The front end draws
        # 6.` as plain "6.", and printing the backtick makes it look like a
        # derivative prime, which is the one thing it must not look like here.
        m = NUM_PRECISION.match(e)
        if m:
            return m.group(1)
        return NAMES.get(e, e)
    if isinstance(e, list):
        return "".join(box(x) for x in e)
    if isinstance(e, tuple) and e[0] == "rule":
        return ""                              # an option, not content
    if not (isinstance(e, tuple) and e[0] == "call"):
        return ""

    h, a = e[1], e[2]
    args = [x for x in a if not (isinstance(x, tuple) and x[0] == "rule")]

    if h == "RowBox":
        return row(args[0] if args and isinstance(args[0], list) else args)
    if h == "FractionBox":
        return "%s/%s" % (wrap(box(args[0])), wrap(box(args[1])))
    if h == "SuperscriptBox":
        b, x = box(args[0]), box(args[1])
        return b + "'" if x == "'" else "%s^%s" % (wrap(b), wrap(x))
    if h == "SubscriptBox":
        return "%s_%s" % (wrap(box(args[0])), box(args[1]))
    if h == "SqrtBox":
        return "Sqrt[%s]" % box(args[0])
    if h == "RadicalBox":
        return "Surd[%s, %s]" % (box(args[0]), box(args[1]))
    if h == "SubsuperscriptBox":
        return "%s_%s^%s" % (wrap(box(args[0])), box(args[1]), box(args[2]))
    if h == "OverscriptBox" or h == "UnderscriptBox":
        return box(args[0])
    if h in ("StyleBox", "TagBox", "FormBox", "InterpretationBox", "TemplateBox"):
        return box(args[0]) if args else ""
    if h == "GridBox":
        return box(args[0]) if args else ""
    return "".join(box(x) for x in args)


def row(items):
    """A RowBox's parts, with the two prefix operators put back into linear form.

    \\[PartialD] and \\[Integral] are typeset TEMPLATES: the notebook stores the
    operator and its operand side by side in one row, and there is no linear
    spelling of that arrangement. D[...] and Integrate[...] are the linear forms
    of those exact templates, so this is a change of spelling, not of meaning.
    """
    parts = list(items)

    # partial-derivative template: Subscript[\[PartialD], var] applied to what follows
    for k, it in enumerate(parts):
        if head_of(it) == "SubscriptBox":
            inner = it[2]
            if inner and box(inner[0]) in ("\\[PartialD]", "∂"):
                var = box(inner[1])
                body = join(parts[k + 1:])
                return join(parts[:k]) + "D[%s, %s]" % (body.strip(), var)

    # integral template: \[Integral] body \[DifferentialD] var
    joined = "".join(box(x) if not isinstance(x, str) else x for x in parts)
    if "\\[Integral]" in joined and "\\[DifferentialD]" in joined:
        flat = joined.replace("\\[Integral]", "", 1)
        body, _, var = flat.rpartition("\\[DifferentialD]")
        return "Integrate[%s, %s]" % (body.strip(), var.strip())

    return join(parts)


def join(parts):
    """Concatenate a row's parts, with a space after each argument separator.

    A RowBox stores "," as a part of its own and the front end puts the space in
    when it draws the row. Concatenating blindly gives N[1/13,50]; the notebook
    on screen says N[1/13, 50].
    """
    out = []
    for x in parts:
        s = box(x)
        out.append(", " if s == "," else s)
    return "".join(out)


# --- cells ------------------------------------------------------------------

def cells(nb):
    """Every Cell in the notebook, as (style, content-expression) pairs."""
    out = []

    def walk(e):
        if isinstance(e, list):
            for x in e:
                walk(x)
            return
        if not (isinstance(e, tuple) and e[0] == "call"):
            return
        if e[1] == "Cell":
            args = [x for x in e[2] if not (isinstance(x, tuple) and x[0] == "rule")]
            if len(args) >= 2 and isinstance(args[1], str):
                out.append((args[1], args[0]))
                return
            if args and head_of(args[0]) == "CellGroupData":
                walk(args[0][2])
                return
            return
        for x in e[2]:
            walk(x)

    walk(nb)
    return out


def content(e):
    """A cell's text: a plain string, or BoxData rendered linearly."""
    if isinstance(e, str):
        return e
    if head_of(e) == "BoxData":
        return box(e[2][0] if e[2] else "")
    if head_of(e) == "TextData":
        return "".join(x for x in e[2][0] if isinstance(x, str)) \
            if e[2] and isinstance(e[2][0], list) else box(e)
    return box(e)


# --- LaTeX ------------------------------------------------------------------

def tex_escape(s):
    # Straight ASCII quotes are what a notebook stores; TeX renders a bare " as
    # a CLOSING quote at both ends, so "?" comes out as ”?”. Pair them up.
    parts = s.split('"')
    if len(parts) > 1:
        s = parts[0]
        for k, piece in enumerate(parts[1:]):
            s += ("``" if k % 2 == 0 else "''") + piece
    for a, b in (("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"),
                 ("$", r"\$"), ("#", r"\#"), ("_", r"\_"), ("{", r"\{"),
                 ("}", r"\}"), ("~", r"\textasciitilde{}"),
                 ("^", r"\textasciicircum{}")):
        s = s.replace(a, b)
    return s


HEAD = r"""%% ===========================================================================
%%  Generated by scripts/nb2tex.py from
%%    %(source)s
%%  Do not edit this file: regenerate it. Output cells are dropped by design --
%%  the submission format for this course is a printed notebook with the output
%%  cleared (README, "Submission format").
%% ===========================================================================
\documentclass[11pt]{article}
\usepackage{coursemacros}
\usepackage{alltt}

\setlength{\parindent}{0pt}
\setlength{\parskip}{0.6em}

%% The notebook numbers its own sections ("1: Front-end tour"). Numbering them
%% again gives "1  1: Front-end tour", so the sections here are unnumbered and
%% the notebook's numbers are left to speak for themselves.
\pagestyle{fancy}
\fancyhf{}
\fancyhead[L]{%(runhead)s}
\fancyhead[R]{%(author)s}
\fancyfoot[C]{\thepage}
\renewcommand{\headrulewidth}{0.4pt}

\begin{document}

\begin{center}
  {\Large\bfseries %(title)s}\\[0.4em]
%(subtitle)s
  {\normalsize %(author)s}\\[0.2em]
  {\small %(date)s}
\end{center}
\vspace{0.5em}

"""

INPUT_ENV = r"""\begin{quote}\ttfamily\small\begin{alltt}
%s
\end{alltt}\end{quote}
"""


def convert(path, title=None, author=None, date=None, subtitle=None):
    src = open(path, encoding="utf-8", errors="replace").read()
    m = re.search(r"Notebook\[", src)
    if not m:
        sys.exit("not a Wolfram notebook: %s" % path)
    t = Tok(src[m.start():])
    nb = parse(t)

    every = cells(nb)

    # A notebook's Title cell is conventionally several lines: the title, then
    # the author, then the course. Use them rather than making any of it up --
    # and let an explicit --title/--author win where one is given.
    nb_title = nb_author = nb_sub = None
    for style, expr in every:
        if style == "Title":
            lines = [x.strip() for x in content(expr).split("\n") if x.strip()]
            if lines:
                nb_title = lines[0]
            if len(lines) > 1:
                nb_author = lines[1]
            if len(lines) > 2:
                nb_sub = " --- ".join(lines[2:])
            break

    title = title or nb_title or os.path.splitext(os.path.basename(path))[0]
    author = author or nb_author or ""
    subtitle = subtitle if subtitle is not None else (nb_sub or "")

    body, dropped, seen = [], 0, []
    for style, expr in every:
        if style in ("Output", "Print", "Message", "Graphics"):
            dropped += 1
            continue
        text = content(expr).strip("\n")
        if not text.strip():
            continue
        seen.append(style)
        if style == "Title":
            continue                       # the title block above carries it
        if style in ("Section", "Subsection", "Subsubsection"):
            cmd = {"Section": "section", "Subsection": "subsection",
                   "Subsubsection": "subsubsection"}[style]
            body.append("\\%s*{%s}" % (cmd, tex_escape(" ".join(text.split()))))
        elif style in ("Input", "Code"):
            body.append(INPUT_ENV % tex_escape(text))
        else:
            body.append(tex_escape(text))
        body.append("")

    head = HEAD % {
        "source": os.path.basename(path),
        "title": tex_escape(title),
        "subtitle": ("  {\\normalsize %s}\\\\[0.3em]\n" % tex_escape(subtitle)) if subtitle else "",
        "runhead": tex_escape(title),
        "author": tex_escape(author),
        "date": date or r"\today",
    }
    return head + "\n".join(body) + "\n\\end{document}\n", seen, dropped


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("notebook")
    ap.add_argument("-o", "--out", help="where to write the .tex")
    ap.add_argument("--title")
    ap.add_argument("--author", help="overrides the notebook's Title cell")
    ap.add_argument("--subtitle", help="overrides the notebook's Title cell")
    a = ap.parse_args()

    tex, seen, dropped = convert(a.notebook, a.title, a.author,
                                 subtitle=a.subtitle)
    out = a.out or os.path.splitext(a.notebook)[0] + ".tex"
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(tex)

    from collections import Counter
    counts = ", ".join("%d %s" % (n, s) for s, n in Counter(seen).most_common())
    print(out)
    print("  cells kept: %s" % counts)
    print("  output cells dropped: %d" % dropped)


if __name__ == "__main__":
    main()
