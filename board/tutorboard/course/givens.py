"""givens.py -- a problem's statement, as a card and as the data it gives.

    statement(tex, label)  the body of `\\begin{problem}{label}` in the write-up
                           at `tex`, or None
    to_card(body)          that body as the markdown a card renders: `\\textit`,
                           `\\emph`, `\\textbf`, `\\par` and enumerate/itemize made
                           markdown, the mathematics left exactly as written
    givens(body)           [{id, name, tex, calc}]: every named matrix
                           environment or `\\left(...\\right)` tuple. `calc` is
                           math.js text (`P = [1/2, 1/3; 0, 1]`), null when an
                           entry is symbolic; an inverse, transpose or power
                           after the value is kept in both.
    figure_source(tex)     the kind-`latex` source a given is typeset from on
                           the slate

The constraint: nothing inside mathematics is rewritten. Math is parked
before any text rule runs and put back after, so a rule can never reach it.
"""

import re

# Mathematics, in the order it is looked for at each position.
_MATH_ENVS = ("equation", "equation*", "align", "align*", "gather", "gather*",
              "multline", "multline*", "eqnarray", "eqnarray*", "displaymath")
_ENV_OPEN = re.compile(r"\\begin\{(%s)\}" % "|".join(re.escape(e) for e in _MATH_ENVS))

# A placeholder for parked mathematics: no brace, no backslash, no markdown.
_PARK = "\x00%d\x00"
_PARKED = re.compile("\x00(\\d+)\x00")


def statement(tex, label):
    """The statement of problem `label` in the write-up at `tex`, as written,
    or None when the file or the problem is not there."""
    try:
        with open(tex, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return None
    return statement_in(text, label)


def statement_in(text, label):
    """`statement` over the text of a write-up already read."""
    opener = "\\begin{problem}{%s}" % label
    at = text.find(opener)
    if at < 0:
        return None
    body = text[at + len(opener):]
    end = body.find("\\end{problem}")
    return (body[:end] if end >= 0 else body).strip("\n")


# ---------------------------------------------------------------------------
# where the mathematics is
# ---------------------------------------------------------------------------
def _escaped(text, i):
    """Is the character at `i` escaped by an odd run of backslashes?"""
    n = 0
    while i - n - 1 >= 0 and text[i - n - 1] == "\\":
        n += 1
    return n % 2 == 1


def split_math(text):
    """`[(is_math, piece)]` covering `text`. A math piece keeps its
    delimiters: `$...$`, `$$...$$`, `\\[...\\]`, `\\(...\\)` and the display
    environments. An unclosed delimiter is text."""
    out, buf, i, n = [], [], 0, len(text)

    def flush():
        if buf:
            out.append((False, "".join(buf)))
            del buf[:]

    while i < n:
        c = text[i]
        end = -1
        if c == "$" and not _escaped(text, i):
            if text.startswith("$$", i):
                close = text.find("$$", i + 2)
                while close >= 0 and _escaped(text, close):
                    close = text.find("$$", close + 1)
                end = close + 2 if close >= 0 else -1
            else:
                close = i + 1
                while close < n and (text[close] != "$" or _escaped(text, close)):
                    close += 1
                end = close + 1 if close < n else -1
        elif c == "\\" and text.startswith("\\[", i) and not _escaped(text, i):
            close = text.find("\\]", i + 2)
            end = close + 2 if close >= 0 else -1
        elif c == "\\" and text.startswith("\\(", i) and not _escaped(text, i):
            close = text.find("\\)", i + 2)
            end = close + 2 if close >= 0 else -1
        elif c == "\\":
            m = _ENV_OPEN.match(text, i)
            if m:
                closer = "\\end{%s}" % m.group(1)
                close = text.find(closer, m.end())
                end = close + len(closer) if close >= 0 else -1
        if end > i:
            flush()
            out.append((True, text[i:end]))
            i = end
            continue
        buf.append(c)
        i += 1
    flush()
    return out


def _strip_math(piece):
    """The mathematics inside a math piece's delimiters."""
    for left, right in (("$$", "$$"), ("\\[", "\\]"), ("\\(", "\\)"), ("$", "$")):
        if piece.startswith(left) and piece.endswith(right) and len(piece) >= len(left) + len(right):
            return piece[len(left):len(piece) - len(right)]
    m = _ENV_OPEN.match(piece)
    if m:
        return piece[m.end():piece.rfind("\\end{")]
    return piece


# ---------------------------------------------------------------------------
# the card
# ---------------------------------------------------------------------------
def _group(text, at):
    """`(inside, end)` of the brace group opening at `text[at]`, or None."""
    if at >= len(text) or text[at] != "{":
        return None
    depth = 0
    for j in range(at, len(text)):
        ch = text[j]
        if ch == "\\":
            continue
        if ch == "{" and not _escaped(text, j):
            depth += 1
        elif ch == "}" and not _escaped(text, j):
            depth -= 1
            if depth == 0:
                return text[at + 1:j], j + 1
    return None


# A command with one argument, and what its argument becomes.
_WRAP = {
    "textit": "*%s*", "emph": "*%s*", "textsl": "*%s*",
    "textbf": "**%s**", "texttt": "`%s`",
    "underline": "%s", "textrm": "%s", "textsf": "%s", "textup": "%s",
    "mbox": "%s", "text": "%s", "ref": "%s", "eqref": "(%s)",
    "footnote": " (%s)",
}
# Commands that say nothing on a card.
_DROP_ARG = ("label", "cite", "index", "vspace", "vspace*", "hspace", "hspace*")
_DROP = ("noindent", "medskip", "smallskip", "bigskip", "hfill", "centering",
         "indent", "relax", "nobreak", "allowbreak")
_WORDS = {"ldots": "…", "dots": "…", "quad": " ", "qquad": " ", "newline": "\n",
          "LaTeX": "LaTeX", "TeX": "TeX", "S": "§", "P": "¶", "par": "\n\n"}


def _commands(text):
    """Text commands made markdown, innermost first; what is not known is
    left as written."""
    out, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if c != "\\":
            out.append(c)
            i += 1
            continue
        m = re.match(r"\\([A-Za-z]+\*?)\s*", text[i:])
        if not m:
            # A control symbol: \% \& \_ \# \$ \{ \} and spacing.
            sym = text[i + 1:i + 2]
            if sym in "%&_#${}":
                out.append(sym)
            elif sym in (",", ";", ":", "!", " ", "/", "@"):
                out.append(" " if sym in (",", ";", ":", " ") else "")
            elif sym == "\\":
                # A line break, with any `[length]` after it.
                rest = re.match(r"\\\\\*?(?:\[[^\]]*\])?", text[i:])
                out.append("\n")
                i += len(rest.group(0))
                continue
            else:
                out.append(text[i:i + 2])
            i += 2
            continue
        name = m.group(1)
        after = i + m.end()
        if name in _WRAP:
            got = _group(text, after)
            if got:
                inner = _commands(got[0])
                out.append(_WRAP[name] % inner.strip() if inner.strip() else "")
                i = got[1]
                continue
        if name in _DROP_ARG:
            got = _group(text, after)
            if got:
                i = got[1]
                continue
        if name in _DROP:
            i = after
            continue
        if name in _WORDS:
            out.append(_WORDS[name])
            # A word command eats the space after it; keep one.
            i = i + 1 + len(name)
            continue
        out.append(text[i:after])
        i = after
    return "".join(out)


_ROMAN = ["i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x", "xi", "xii"]


def _label_maker(opts):
    """How the items of an enumerate are labelled, from its `[...]` options:
    a function of the item's index, or None for a plain numbered list."""
    m = re.search(r"label\s*=\s*\{?([^,\]}]*\\(?:alph|Alph|roman|Roman|arabic)\*[^,\]}]*)\}?",
                  opts or "")
    if not m:
        bare = (opts or "").strip()
        if not bare or "=" in bare:
            return None
        m = re.match(r"(.*?)(a|A|i|I|1)(.*)$", bare)
        if not m:
            return None
        style = {"a": "alph", "A": "Alph", "i": "roman", "I": "Roman", "1": "arabic"}[m.group(2)]
        pattern = m.group(1) + "\\" + style + "*" + m.group(3)
    else:
        pattern = m.group(1).strip()

    def label(k):
        return re.sub(r"\\(alph|Alph|roman|Roman|arabic)\*", lambda s: {
            "alph": chr(ord("a") + k % 26), "Alph": chr(ord("A") + k % 26),
            "roman": _ROMAN[k] if k < len(_ROMAN) else str(k + 1),
            "Roman": (_ROMAN[k] if k < len(_ROMAN) else str(k + 1)).upper(),
            "arabic": str(k + 1)}[s.group(1)], pattern)
    return label


_LIST_OPEN = re.compile(r"\\begin\{(enumerate|itemize)\}")


def _list_end(text, start, env):
    """Where the `\\end{env}` matching an opener ending at `start` begins."""
    depth = 1
    pat = re.compile(r"\\(begin|end)\{%s\}" % env)
    for m in pat.finditer(text, start):
        depth += 1 if m.group(1) == "begin" else -1
        if depth == 0:
            return m.start(), m.end()
    return len(text), len(text)


def _items(body):
    """The top-level `\\item`s of a list body: `[(label or None, text)]`."""
    out, depth, i, cur = [], 0, 0, None
    for m in re.finditer(r"\\begin\{(?:enumerate|itemize)\}|\\end\{(?:enumerate|itemize)\}"
                         r"|\\item\b\s*(?:\[([^\]]*)\])?", body):
        tok = m.group(0)
        if tok.startswith("\\begin"):
            depth += 1
        elif tok.startswith("\\end"):
            depth -= 1
        elif depth == 0:
            if cur is not None:
                cur[1] = body[cur[2]:m.start()]
                out.append((cur[0], cur[1]))
            cur = [m.group(1), "", m.end()]
    if cur is not None:
        out.append((cur[0], body[cur[2]:]))
    return out


# Marks a line a list made, so paragraph folding leaves it alone.
_KEEP = "\x01"


def _lists(text, depth=0):
    """enumerate and itemize made markdown lines, nested by indent."""
    out, at = [], 0
    for _ in range(1000):
        m = _LIST_OPEN.search(text, at)
        if not m:
            break
        env = m.group(1)
        opts = ""
        start = m.end()
        o = re.match(r"\s*\[([^\]]*)\]", text[start:])
        if o:
            opts = o.group(1)
            start += o.end()
        end, after = _list_end(text, start, env)
        out.append(text[at:m.start()])
        label = _label_maker(opts) if env == "enumerate" else None
        lines = []
        for k, (own, item) in enumerate(_items(text[start:end])):
            inner = _lists(item, depth + 1)
            first, _, rest = inner.partition("\n" + _KEEP)
            words = " ".join(first.split())
            if own is not None:
                mark = "**%s**" % own.strip()
            elif label:
                mark = "**%s**" % label(k)
            elif env == "enumerate":
                mark = "%d." % (k + 1)
            else:
                mark = None
            pad = "  " * depth
            if mark and mark.startswith("**") and depth == 0:
                lines.append(_KEEP + "%s %s" % (mark, words))
            else:
                lines.append(_KEEP + pad + ("- " if not mark or mark.startswith("**") else "")
                             + ("%s " % mark if mark else "") + words)
            if rest:
                lines.append(_KEEP + rest)
        sep = "\n" if depth else "\n\n"
        out.append("\n\n" + sep.join(lines) + "\n\n")
        at = after
    out.append(text[at:])
    return "".join(out)


def _fold(text):
    """Paragraphs on one line each, blank-line separated; list lines kept."""
    blocks = []
    for block in re.split(r"\n\s*\n", text):
        lines = block.split("\n")
        kept, prose = [], []
        for line in lines:
            if line.startswith(_KEEP):
                if prose:
                    kept.append(" ".join(" ".join(prose).split()))
                    prose = []
                kept.append(line[1:].rstrip())
            else:
                prose.append(line)
        if prose:
            kept.append(" ".join(" ".join(prose).split()))
        kept = [k for k in kept if k.strip()]
        if kept:
            blocks.append("\n".join(kept))
    return "\n\n".join(blocks)


def _comments(text):
    """`%` to the end of a line, unless escaped."""
    return "\n".join(re.sub(r"(?<!\\)%.*$", "", line) for line in text.split("\n"))


def _dashes(text):
    return (text.replace("---", "—").replace("--", "–").replace("``", "“")
            .replace("''", "”").replace("~", " "))


def to_card(body):
    """A problem's statement as card markdown. Text commands become markdown
    and the mathematics comes back exactly as written."""
    parked = []

    def park(piece):
        parked.append(piece)
        return _PARK % (len(parked) - 1)

    text = "".join(park(p) if math else p
                   for math, p in split_math(_comments(body or "")))
    text = _lists(text)
    text = _commands(text)
    text = _dashes(text)
    text = _fold(text)
    return _PARKED.sub(lambda m: parked[int(m.group(1))], text).strip()


# ---------------------------------------------------------------------------
# the givens
# ---------------------------------------------------------------------------
_MATRIX = re.compile(r"\\begin\{(pmatrix|bmatrix|Bmatrix|vmatrix|Vmatrix|matrix|"
                     r"smallmatrix|array)\}")
_TUPLE = re.compile(r"\\left\s*(\(|\[|\\\{)")
_FONT = r"\\(?:mathbf|mathrm|mathit|mathsf|mathcal|mathbb|boldsymbol|bm|vec)\s*\{\s*[A-Za-z]\s*\}"
_SUB = r"(?:\s*_\s*(?:\{[^{}]*\}|[A-Za-z0-9]))?"
_SUP = r"(?:\s*\^\s*(?:\{[^{}]*\}|[A-Za-z0-9]))?"
_NAME = re.compile(r"(?P<name>(?:%s|\\[A-Za-z]+|[A-Za-z])%s%s)\s*=\s*$" % (_FONT, _SUB, _SUP))

# What sits between the cells of a tuple and around a number.
_SPACE = re.compile(r"\\[,;:! ]|\\q?quad\b|~|\s+")
_NUM = r"[0-9]+(?:\.[0-9]*)?|\.[0-9]+"
_ARG = r"(?:\{\s*([+-]*(?:%s))\s*\}|([0-9]))" % _NUM


def _number(cell):
    """Math.js text for one entry, or None when it is not a plain number or a
    fraction of two."""
    s = _SPACE.sub("", cell or "")
    sign = ""
    while s[:1] in ("-", "+"):
        if s[0] == "-":
            sign = "" if sign else "-"
        s = s[1:]
    if not s:
        return None
    m = re.match(r"\\[dt]?frac\s*%s\s*%s$" % (_ARG, _ARG), s)
    if m:
        a = m.group(1) or m.group(2)
        b = m.group(3) or m.group(4)
        # A sign inside either brace: -\frac{1}{2}, \frac{-1}{2}, \frac{1}{-2}.
        for part in (a, b):
            if part.count("-") % 2:
                sign = "" if sign else "-"
        a, b = a.lstrip("+-"), b.lstrip("+-")
        return "%s%s/%s" % (sign, _plain(a), _plain(b))
    m = re.match(r"(%s)/(%s)$" % (_NUM, _NUM), s)
    if m:
        return "%s%s/%s" % (sign, _plain(m.group(1)), _plain(m.group(2)))
    if re.match(r"(%s)$" % _NUM, s):
        return sign + _plain(s)
    return None


def _plain(num):
    """`.8` as `0.8` and `2.` as `2`, which math.js reads either way."""
    if num.startswith("."):
        num = "0" + num
    return num.rstrip(".") if num.endswith(".") else num


def _identifier(name):
    """A math.js name for a given's TeX name, or None. `\\mathbf{P}_1` is
    `P_1`; a superscript or a compound subscript has none."""
    s = re.sub(r"\s+", "", name)
    s = re.sub(r"\\(?:mathbf|mathrm|mathit|mathsf|mathcal|mathbb|boldsymbol|bm|vec)\{([A-Za-z])\}",
               r"\1", s)
    m = re.match(r"(\\?[A-Za-z]+)(?:_(?:\{([A-Za-z0-9]+)\}|([A-Za-z0-9])))?$", s)
    if not m:
        return None
    base = m.group(1)
    if base.startswith("\\"):
        base = base[1:]
        if base in ("pi", "e", "i", "Ans"):
            return None
    elif len(base) != 1:
        return None
    sub = m.group(2) or m.group(3)
    return base + ("_" + sub if sub else "")


def _matrix_end(math, start, env):
    depth = 1
    pat = re.compile(r"\\(begin|end)\{%s\}" % re.escape(env))
    for m in pat.finditer(math, start):
        depth += 1 if m.group(1) == "begin" else -1
        if depth == 0:
            return m.start(), m.end()
    return None


def _tuple_end(math, start):
    depth = 1
    for m in re.finditer(r"\\(left|right)\b", math[start:]):
        depth += 1 if m.group(1) == "left" else -1
        if depth == 0:
            at = start + m.start()
            close = re.match(r"\\right\s*(\)|\]|\\\}|\.)", math[at:])
            return at, at + (close.end() if close else len("\\right"))
    return None


def _split_top(text, sep):
    """`text` split on `sep` outside braces."""
    out, depth, cur = [], 0, []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        if depth == 0 and text.startswith(sep, i) and not _escaped(text, i):
            out.append("".join(cur))
            cur = []
            i += len(sep)
            continue
        cur.append(ch)
        i += 1
    out.append("".join(cur))
    return out


def _rows(inner):
    """A matrix body as rows of cells, an empty trailing row dropped."""
    rows = re.split(r"\\\\\*?(?:\s*\[[^\]]*\])?", inner)
    if rows and not rows[-1].strip():
        rows.pop()
    return [_split_top(r, "&") for r in rows]


def _calc(ident, value_kind, inner):
    if not ident:
        return None
    if value_kind == "matrix":
        rows = _rows(inner)
        if not rows or len(set(len(r) for r in rows)) != 1:
            return None
        nums = [[_number(c) for c in r] for r in rows]
        if any(v is None for r in nums for v in r):
            return None
        return "%s = [%s]" % (ident, "; ".join(", ".join(r) for r in nums))
    cells = _split_top(inner, ",")
    nums = [_number(c) for c in cells]
    if not nums or any(v is None for v in nums):
        return None
    return "%s = [%s]" % (ident, ", ".join(nums))


def _postfix(math, end):
    """`(end, wrap)` for a `^...` or `'` straight after a value ending at
    `end`: the end past it, and how its math.js text is wrapped -- a format
    string, `""` for no operator, or None for one with no math.js reading."""
    m = re.match(r"\s*('+)", math[end:])
    if m:
        k = len(m.group(1))
        return end + m.end(), ("transpose(%s)" if k % 2 else "%s")
    m = re.match(r"\s*\^\s*", math[end:])
    if not m:
        return end, ""
    at = end + m.end()
    got = _group(math, at)
    if got:
        arg, after = got[0], got[1]
    else:
        tok = re.match(r"\\[A-Za-z]+|[A-Za-z0-9]", math[at:])
        if not tok:
            return end, ""
        arg, after = tok.group(0), at + tok.end()
    arg = re.sub(r"\s+", "", arg)
    if arg == "-1":
        return after, "inv(%s)"
    if arg in ("T", "\\top", "\\intercal", "\\mathsf{T}", "\\mathrm{T}", "t"):
        return after, "transpose(%s)"
    if re.match(r"[0-9]+$", arg):
        return after, "%s^" + arg
    return after, None


def _slug(name):
    s = re.sub(r"\\(?:mathbf|mathrm|mathit|mathsf|mathcal|mathbb|boldsymbol|bm|vec)", "", name)
    s = re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")
    return s or "given"


def givens(body):
    """Every named matrix or `\\left(...\\right)` tuple in a statement's
    mathematics, in order: `[{id, name, tex, calc}]`."""
    out, seen = [], {}
    for is_math, piece in split_math(body or ""):
        if not is_math:
            continue
        math = _strip_math(piece)
        found = []
        for m in _MATRIX.finditer(math):
            got = _matrix_end(math, m.end(), m.group(1))
            if not got:
                continue
            start = m.end()
            if m.group(1) == "array":
                spec = _group(math, start)
                if spec:
                    start = spec[1]
            found.append((m.start(), got[1], "matrix", math[start:got[0]]))
        for m in _TUPLE.finditer(math):
            got = _tuple_end(math, m.end())
            if got:
                found.append((m.start(), got[1], "tuple", math[m.end():got[0]]))
        found.sort()
        last_end = -1
        for begin, end, kind, inner in found:
            # One value inside another (a tuple of matrices) counts once.
            if begin < last_end:
                continue
            named = _NAME.search(math[:begin])
            if not named:
                continue
            # An inverse, a transpose or a power after it is part of the value.
            end, wrap = _postfix(math, end)
            last_end = end
            name = re.sub(r"\s+", "", named.group("name"))
            tex = (name + "=" + math[begin:end]).strip()
            ident = _identifier(name)
            slug = ident or _slug(name)
            seen[slug] = seen.get(slug, 0) + 1
            # Followed by an operator, the value is not the whole right side.
            more = re.match(r"\s*(?:[-+*/]|\\(?:cdot|times|otimes|circ)\b)", math[end:])
            calc = _calc(ident, kind, inner) if wrap is not None and not more else None
            if calc and wrap:
                lhs, _, rhs = calc.partition(" = ")
                calc = "%s = %s" % (lhs, wrap % rhs)
            out.append({"id": slug if seen[slug] == 1 else "%s-%d" % (slug, seen[slug]),
                        "name": name, "tex": tex, "calc": calc})
    return out


def figure_source(tex):
    """What a given is typeset from on the slate: `server/tikz.py`'s kind
    `latex` figure of this source, named by its digest. One unbreakable box,
    since the figure's page is as narrow as its content, and no page style,
    since a course's preamble may set a running head."""
    return "\\thispagestyle{empty}\\mbox{$\\displaystyle %s$}" % tex


def problem(text, label):
    """`{statement, card, givens}` for problem `label` in a write-up's text,
    or None where the problem is not there."""
    body = statement_in(text, label)
    if body is None:
        return None
    stated = "\\todo{" not in body and bool(body.strip())
    return {"statement": body, "stated": stated,
            "card": to_card(body) if stated else "",
            "givens": givens(body) if stated else []}
