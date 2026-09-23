#!/usr/bin/env python3
"""The board typesets twice, and both engines must know the same words.

    python3 test/vocabulary.py

LaTeX gets the course's own `latex/coursemacros.sty` and then `board-macros.tex`,
whose every line is `\\providecommand` -- the course wins, the board fills gaps.
KaTeX in the browser got `web/macros.js` and nothing else, so the vocabularies
were not the same and nothing said so.

Measured against `courses/Probability`: 33 of its 44 macros were unknown to the
browser and two more were known at the WRONG ARITY. The second is the worse one.
`\\E[number of records by time n]` reaching the glass as its own source is ugly
and announces itself; `\\EE{X}` rendering as a bare blackboard E with the
brackets silently dropped is a card that looks typeset and says something else.

So the rule is now the same on both sides -- THE COURSE'S OWN DEFINITION WINS --
and this holds it for every course in the tree rather than for the one that was
reported.
"""

import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from tutorboard import coursemacros                           # noqa: E402

fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


# ---- the parser -------------------------------------------------------------
got = coursemacros.parse(r"""
\newcommand{\E}{\mathbb{E}}
\newcommand{\EE}[1]{\E\!\left[#1\right]}
\newcommand{\EEc}[2]{\E\!\left[#1 \,\middle|\, #2\right]}
\renewcommand{\headrulewidth}{0pt}
\providecommand{\Var}{\operatorname{Var}}
\newcommand{\set}[1]{\left\{#1\right\}}
\newcommand{\opt}[2][d]{#1#2}
\newcommand{\broken}{\mathbb{E}
""")
check("a plain definition is read", got.get("\\E") == "\\mathbb{E}")
check("and one with arguments keeps them as KaTeX takes them, which is the same "
      "shape LaTeX uses", got.get("\\EE") == "\\E\\!\\left[#1\\right]")
check("two arguments too", "#2" in got.get("\\EEc", ""))
check("`\\renewcommand` and `\\providecommand` are definitions as well",
      "\\Var" in got)
check("BRACES ARE COUNTED, NOT MATCHED BY A REGEX -- a body is full of them, and "
      "an escaped brace is a literal rather than a depth change",
      got.get("\\set") == "\\left\\{#1\\right\\}")
check("page furniture is not mathematics and is left out",
      "\\headrulewidth" not in got)
check("A DEFAULTED OPTIONAL ARGUMENT IS REFUSED RATHER THAN GUESSED AT. KaTeX "
      "has no equivalent, so taking it would shift every argument by one -- and "
      "a macro mis-read onto the glass is worse than one missing from it",
      "\\opt" not in got)
check("an unbalanced body is skipped rather than half-read",
      "\\broken" not in got)
check("nothing it could not read becomes an empty definition",
      all(v for v in got.values()))

# ---- every course in the tree ----------------------------------------------
js = open(os.path.join(ROOT, "web", "macros.js"), encoding="utf-8").read()
board = {}
for m in re.finditer(r'"(\\\\[A-Za-z]+)"\s*:\s*"((?:[^"\\]|\\.)*)"', js):
    board[m.group(1).replace("\\\\", "\\")] = m.group(2)
check("the board has a vocabulary of its own for what no course defines",
      len(board) > 40)

atlas = os.path.dirname(ROOT)
styles = sorted(glob.glob(os.path.join(atlas, "courses", "*", "latex",
                                       "coursemacros.sty")))
check("there are courses to check", bool(styles))


def arity(body):
    return max([int(x) for x in re.findall(r"#(\d)", body)] or [0])


for sty in styles:
    where = os.path.dirname(os.path.dirname(sty))
    name = os.path.basename(where)
    coursemacros.forget()
    mine = coursemacros.for_workspace(where)
    check("%s's macros reach the browser" % name, bool(mine))
    served = dict(board)
    served.update(mine)
    missing = sorted(k for k in mine if k not in served)
    check("%s: nothing it defines is unknown to KaTeX" % name, not missing)
    wrong = sorted(k for k in mine if arity(served[k]) != arity(mine[k]))
    check("%s: nothing it defines is served at another arity -- that is the "
          "failure that renders WRONG rather than raw" % name, not wrong)

# ---- and the wiring ---------------------------------------------------------
hub = open(os.path.join(ROOT, "tutorboard", "server", "hub.py"),
           encoding="utf-8").read()
check("the payload carries them, per workspace, because the vocabulary is the "
      "course's rather than the machine's",
      '"macros": coursemacros.for_workspace(self.repo.root)' in hub)

bjs = open(os.path.join(ROOT, "web", "board.js"), encoding="utf-8").read()
check("the page takes them off the payload", "setCourseMacros(data.macros)" in bjs)
check("and hands the merged table to KaTeX rather than the board's own",
      "macros: courseMacros()" in bjs)
check("the course's definition is laid OVER the board's, so a course is right "
      "about its own notation",
      bjs.index("var base = window.BOARD_MACROS") < bjs.index("courseMacrosRaw ? JSON.parse"))

print("%d FAILURES" % len(fails) if fails
      else "both engines know what the course writes in, and the course decides")
sys.exit(1 if fails else 0)
