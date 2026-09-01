# HANDOFF

2026-09-01. Garling §1.1, lecture. Board: Ch 1 — Groups, fields and vector spaces.

## Settled — do not re-teach

Cycle notation, inverting a cycle, *right factor acts first*, multiplying permutations by tracking
points. Conjugation preserves cycle type and order. ⟨(1 2), (1 2 3)⟩ = S₃. Index 2 ⟹ normal
(**1.3**, written up).

**1.5, built alone**: G = S₄, H = the three 2+2 elements plus e, K = {e, (1 2)(3 4)} normal in H
because H is abelian, witness g = (1 2 3 4) with gkg⁻¹ = (1 4)(2 3) ∉ K. Written up as 01.5,
handwriting filed, compiled clean.

## Wrong, and why

Nothing mathematical. One teaching failure, mine: I posed the conjugation-as-relabelling shortcut
and asked for g(4) without ever having introduced the bracket — the function notation for a
permutation had never appeared. They replied "Not understanding", flat, with no ink.

## Next — one thing

**The open question is unanswered**: a permutation *is a function*, the cycle is its instruction
sheet (read left to right, wrap at the end, unwritten points stay put). σ = (1 3 4) on {1,2,3,4};
they owe σ(1), σ(2), σ(3), σ(4) = 3, 2, 4, 1.

Only once that bracket is fluent, return to the relabelling rule
g(a b)(c d)g⁻¹ = (g(a) g(b))(g(c) g(d)); with g = (2 3) the answer is **(1 3)(2 4)**. They did 1.5
by multiplying three permutations across four lines, and that habit must break before Galois theory.

After that: their own sheet, `handwritten/ch01-problem-list.pdf`, numbered 1–4 — **collides with
Garling's numbering, say which you mean**. Sheets 2 and 3 already carry complete ink: write them up,
do not teach them. Sheet 1 (even order ⟹ an element of order 2) is untouched and needs the pairing
argument.

## How this student works

"Not understanding" means *the step before did not land* — go back a whole step to notation, do not
re-ask louder and do not mark it wrong. Never introduce a symbol inside the question that uses it.
They never name a group they have not been shown. They patch the exact character you name and
nothing adjacent — repeat a request in a *new* form. Read the bottom block of a page. Margin
remarks and ellipses are deliberate. Plain questions get `note`, never `wrong`. Pictures are
instructions. Recurring slip: writing gkg⁻¹ as gg⁻¹ — fix silently. Check your own permutation
arithmetic before shipping a card.

## Machine

TeX Live 2026 **basic**: `stmaryrd` and `tikz-cd` missing, both guarded in `coursemacros.sty` with
`\IfFileExists`. A chapter with a tikzcd diagram still fails here; `tlmgr` needs an approval I could
not give.

Two headless runs once fired on the same inbox message and both wrote a card. If `board next` hands
you a number above the recap's card count, another run got there first — read that card and repair
it in place rather than adding a third.

Board `http://127.0.0.1:9098/`; iPad `https://board.tail0c6c62.ts.net/`. No `$…$` in card titles.
Unpushed.
