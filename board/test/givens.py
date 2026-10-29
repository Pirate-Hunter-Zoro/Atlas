#!/usr/bin/env python3
"""A problem's statement and its givens, read from the write-up on disk.

    python3 test/givens.py

The fixtures are tracked write-ups: Probability's hw04 as committed at
0a591419, so the owner adding a problem does not move it, and Galois Theory's
ch07 homework.

  * hw04 problem 5 gives P and p, each with math.js text the calculator
    defines; problem 14 gives its four matrices.
  * Galois ch07 problem 17 renders whole: its italic title, (a) to (d), and
    its mathematics exactly as written.
  * An entry that is not a number leaves `calc` null and keeps the given; a
    signed fraction is a number; an inverse, transpose or power after a
    value is part of it, and an operator after it leaves `calc` null.
  * `state.load_problem` reads the pinned set only, caches on its mtime, and
    falls back to the next problem when nothing is pinned; the payload
    carries it as `problem`.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD_DIR = os.path.dirname(HERE)
ATLAS = os.path.dirname(BOARD_DIR)
sys.path.insert(0, BOARD_DIR)

from tutorboard.course import givens, homework                     # noqa: E402
from tutorboard.course import repo as course_repo                  # noqa: E402
from tutorboard.lesson import state                                # noqa: E402

fails = []


def check(name, cond, detail=""):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name + (("\n       " + str(detail)) if detail else ""))


HW04_AT = "0a591419:courses/Probability/homework/hw04/hw04.tex"
HW04 = os.path.join(tempfile.mkdtemp(prefix="tutor-hw04-"), "hw04.tex")
with open(HW04, "wb") as fh:
    fh.write(subprocess.run(["git", "-C", ATLAS, "show", HW04_AT],
                            capture_output=True, check=True).stdout)
CH07 = os.path.join(ATLAS, "courses", "Galois-Theory", "chapters",
                    "ch07-splitting-fields", "homework", "ch07-homework.tex")

# --- hw04 problem 5 ------------------------------------------------------------
body = givens.statement(HW04, "5")
got = givens.givens(body or "")
by = dict((g["name"], g) for g in got)
check("hw04 problem 5 has a statement", body and "Find $E[X_3]$" in body)
check("it gives P and p, in that order", [g["name"] for g in got] == ["P", "p"], got)
check("P's calc is P = [1/2, 1/3, 1/6; 0, 1/3, 2/3; 1/2, 0, 1/2]",
      by.get("P", {}).get("calc") == "P = [1/2, 1/3, 1/6; 0, 1/3, 2/3; 1/2, 0, 1/2]",
      by.get("P"))
check("p's calc is p = [1/4, 1/4, 1/2]",
      by.get("p", {}).get("calc") == "p = [1/4, 1/4, 1/2]", by.get("p"))
check("each carries its TeX, name and value as written",
      by["P"]["tex"].startswith("P=\\begin{pmatrix} \\tfrac12")
      and by["P"]["tex"].endswith("\\end{pmatrix}")
      and by["p"]["tex"] == "p=\\left(\\tfrac14,\\ \\tfrac14,\\ \\tfrac12\\right)")
check("and an id of its own", [g["id"] for g in got] == ["P", "p"])

# --- hw04 problem 14 -----------------------------------------------------------
got = givens.givens(givens.statement(HW04, "14") or "")
check("hw04 problem 14 gives four matrices",
      len(got) == 4 and all(g["calc"] for g in got)
      and [g["id"] for g in got] == ["P_1", "P_2", "P_3", "P_4"], got)
check("named in bold as written, defined as P_1 to P_4",
      got and got[0]["name"] == "\\mathbf{P}_1"
      and got[0]["calc"] == "P_1 = [0, 1/2, 1/2; 1/2, 0, 1/2; 1/2, 1/2, 0]"
      and got[3]["calc"].startswith("P_4 = [1/4, 3/4, 0, 0, 0; "))

# --- Galois ch07 problem 17 ----------------------------------------------------
body = givens.statement(CH07, "17")
card = givens.to_card(body or "")
lines = card.split("\n")
check("Galois ch07 problem 17 renders (a)-(d), one paragraph each",
      [l[:7] for l in lines if l.startswith("**(")] ==
      ["**(a)**", "**(b)**", "**(c)**", "**(d)**"], card)
check("with its title in italics and nothing of the LaTeX list left",
      lines[0] == "*The Galois group of $x^4-2$*"
      and "\\begin{enumerate}" not in card and "\\item" not in card
      and "\\textit" not in card and "\\emph" not in card and "\\par" not in card,
      card[:200])
check("and the mathematics exactly as written",
      "$\\tau\\sigma\\tau^{-1}=\\sigma^{-1}$" in card
      and "$\\QQ((1-i)\\alpha)$" in card and "*Hint:*" in card)
check("it names no givens: nothing in it is a named matrix or tuple",
      givens.givens(body or "") == [])

# --- what the markdown rules leave alone ---------------------------------------
check("math is never rewritten, even where it looks like markup",
      givens.to_card("Take $a--b$ and \\textbf{bold} with $\\textit{x}$.")
      == "Take $a--b$ and **bold** with $\\textit{x}$.")
check("itemize is a list, enumerate a numbered one",
      givens.to_card("\\begin{itemize}\\item one\n\\item two\\end{itemize}")
      == "- one\n\n- two"
      and givens.to_card("\\begin{enumerate}\\item one\\item two\\end{enumerate}")
      == "1. one\n\n2. two")
# --- what the card's renderer would otherwise show raw -------------------------
check("A $ INSIDE BRACES DOES NOT CLOSE THE MATH: hw01's `P(\\text{$E$ before $F$})` "
      "is one span, as KaTeX's auto-render reads it",
      givens.split_math("so $P(\\text{$E$ before $F$})$ holds")
      == [(False, "so "), (True, "$P(\\text{$E$ before $F$})$"), (False, " holds")])
check("font declarations say nothing: hw01's `\\upshape\\emph{Hint:}` is *Hint:*",
      givens.to_card("\\upshape\\emph{Hint:} Use it. {\\bf bold} {\\itshape it} {\\small s}")
      == "*Hint:* Use it. **bold** *it* s")
check("an escaped dollar keeps its backslash, so the card parks it rather than "
      "pairing it with the next one into a formula",
      givens.to_card("A ticket costs \\$5 and a meal \\$10 when $x>0$.")
      == "A ticket costs \\$5 and a meal \\$10 when $x>0$.")
check("TeX accents are the letter, and an escaped quote is the quote",
      givens.to_card("L'H\\^opital, G\\\"odel, \\'{e}t\\'e and \\\"so\\\" it\\'s")
      == "L'Hôpital, Gödel, été and \"so\" it's")
check("a TeX single quote is a pair of quotes (ch06's `duplicating the cube')",
      givens.to_card("(impossibility of `duplicating the cube')")
      == "(impossibility of ‘duplicating the cube’)")
check("a proof is its run-in head and one box; a theorem is bold with its note",
      givens.to_card("\\begin{proof}[Proof that {$[L:K]=2$}] Done. \\qed \\end{proof}"
                     "\\begin{lemma}[Tower] X. \\end{lemma}")
      == "*Proof that $[L:K]=2$.* Done. ∎\n\n**Lemma (Tower).** X.")
check("run-in headings are bold where they stand",
      givens.to_card("\\paragraph{(a) The tower.} Then \\section*{Part} next")
      == "**(a) The tower.** Then **Part** next")
check("\\qedhere is the box's place, said once; \\dots before a star keeps the star",
      givens.to_card("\\begin{proof} Done.\\qedhere\\end{proof} \\dots*x* and \\section*{A}")
      == "*Proof.* Done. ∎\n\n…*x* and **A**")
check("a label holding $[L:K]$ is one label",
      givens.to_card("\\begin{itemize}\\item[{$[L:K]=2$}] degree two\\end{itemize}")
      == "**$[L:K]=2$** degree two")
check("a code span ending in a prime is code, not a TeX quote",
      givens.to_card("Use \\texttt{foldl'} instead of \\texttt{foldl}, `the cube')")
      == "Use `foldl'` instead of `foldl`, ‘the cube’)")
check("an address, \\verb and \\ensuremath reach the card as written, untouched by "
      "the dash and tie rules, for the card's renderer to set",
      givens.to_card("\\url{https://x.org/~me--a} \\href{https://y.org/a--b}{the \\textbf{site}} "
                     "\\verb|x--1| \\ensuremath{a--b}")
      == "\\url{https://x.org/~me--a} \\href{https://y.org/a--b}{the **site**} "
         "\\verb|x--1| \\ensuremath{a--b}")
sym = givens.givens("$$A=\\begin{bmatrix} a & 1 \\\\ 0 & \\tfrac{3}{4} \\end{bmatrix}$$ "
                    "and $v=\\left(-\\frac{1}{2}, .5\\right)$")
check("a symbolic entry keeps the given and leaves calc null",
      [g["name"] for g in sym] == ["A", "v"] and sym[0]["calc"] is None
      and sym[1]["calc"] == "v = [-1/2, 0.5]", sym)

signed = givens.givens("$A=\\begin{bmatrix}\\frac{-1}{2} & 1\\\\ 0 & 1\\end{bmatrix}$ "
                       "and $p = \\left(\\frac{-1}{4}, \\frac{5}{-4}, -\\frac{-1}{2}\\right)$")
check("a sign inside a fraction's braces is still a number",
      [g["calc"] for g in signed] == ["A = [-1/2, 1; 0, 1]", "p = [-1/4, -5/4, 1/2]"],
      signed)
post = givens.givens("$Q = \\begin{pmatrix}1&2\\\\3&4\\end{pmatrix}^{-1}$, "
                     "$x = \\left(1,2,3\\right)^T$, $y = \\left(1,2\\right)'$, "
                     "$M = \\begin{pmatrix}1&0\\\\0&1\\end{pmatrix}^{n}$, "
                     "$N = \\begin{pmatrix}1&0\\\\0&1\\end{pmatrix}^2 + I$")
check("an inverse, transpose or power after a value stays in its tex and its calc",
      [g["tex"] for g in post][:2]
      == ["Q=\\begin{pmatrix}1&2\\\\3&4\\end{pmatrix}^{-1}", "x=\\left(1,2,3\\right)^T"]
      and [g["calc"] for g in post]
      == ["Q = inv([1, 2; 3, 4])", "x = transpose([1, 2, 3])", "y = transpose([1, 2])",
          None, None], post)

# --- load_problem --------------------------------------------------------------
tmp = tempfile.mkdtemp(prefix="tutor-givens-")
try:
    root = os.path.join(tmp, "course")
    os.makedirs(os.path.join(root, "homework", "hw04"))
    tex = os.path.join(root, "homework", "hw04", "hw04.tex")
    shutil.copyfile(HW04, tex)
    with open(os.path.join(root, "tutorboard.json"), "w", encoding="utf-8") as fh:
        json.dump({"name": "Probability"}, fh)
    repo = course_repo.Repo(root, os.path.join(root, "live"))
    st = {"hw": "homework/hw04/hw04.tex", "problem": "5"}
    got = state.load_problem(repo, st)
    check("load_problem names the pinned problem and every label in the set",
          got and got["label"] == "5" and got["pinned"] is True
          and got["labels"] == ["2", "3", "5", "14"] and got["set"] == "hw04", got)
    check("with its card and its givens",
          "$$P=\\begin{pmatrix}" in got["card"]
          and [g["id"] for g in got["givens"]] == ["P", "p"])
    reads = []
    real_open = open

    def counting_open(path, *a, **kw):
        if os.path.abspath(str(path)) == tex:
            reads.append(path)
        return real_open(path, *a, **kw)

    import builtins
    builtins.open = counting_open
    try:
        again = state.load_problem(repo, st)
    finally:
        builtins.open = real_open
    check("a second payload is served from the cache, the file unread",
          again == got and not reads, reads)
    with open(tex, "a", encoding="utf-8") as fh:
        fh.write("% touched\n")
    os.utime(tex, ns=(os.stat(tex).st_atime_ns, os.stat(tex).st_mtime_ns + 10 ** 9))
    builtins.open = counting_open
    try:
        state.load_problem(repo, st)
    finally:
        builtins.open = real_open
    check("and an edited write-up is read again", len(reads) == 1, reads)
    unpinned = {"hw": "homework/hw04/hw04.tex"}
    check("with nothing pinned and the set written up, no problem is on screen",
          state.load_problem(repo, unpinned)["label"] is None
          and state.load_problem(repo, unpinned)["labels"] == ["2", "3", "5", "14"])
    homework.pose(tex, "16", "")
    check("nor while the next one's statement is still a placeholder",
          state.load_problem(repo, unpinned)["label"] is None)
    homework.pose(tex, "16", "Show that state $1$ is recurrent.")
    fell = state.load_problem(repo, unpinned)
    check("and once it is stated, the panel falls back to it",
          fell["label"] == "16" and fell["pinned"] is False
          and fell["card"] == "Show that state $1$ is recurrent.", fell)
    check("and nothing is read where nothing is pinned",
          state.load_problem(repo, {}) is None
          and state.load_problem(repo, {"hw": "../elsewhere.tex"}) is None)

    from tutorboard.server import hub, tikz                     # noqa: E402
    with open(repo.state_path, "w", encoding="utf-8") as fh:
        json.dump(st, fh)
    data = hub.Hub(repo, tikz.TikzWorker(repo)).build()
    check("the payload carries it as `problem`",
          (data.get("problem") or {}).get("label") == "5")
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print()
if fails:
    print("%d FAILURES" % len(fails))
    sys.exit(1)
print("a problem's statement and givens come off the write-up whole")
