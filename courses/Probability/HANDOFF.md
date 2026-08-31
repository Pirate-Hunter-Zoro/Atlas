# HANDOFF

**Session:** Homework 1 sitting — `homework/hw01/hw01.tex`. Due 2 September 2026.

**Assigned, in order:** instructor's own (inclusion–exclusion), then Ross ch.1
ex. 8, 10, 12, 39, 41. Practice only, not handed in: 4, 5, 6, 7, 17.

## Where they got to

**Done and agreed correct — 2 of 6 problems, plus both lemmas Ross 10 needs.**

- **Problem 1**, $P(E\cup F)=P(E)+P(F)-P(EF)$. Their own three-way carve into
  $EF, EF^{c}, FE^{c}$ — not the two-way route I taught. Written up in their shape.
- **Problem 8**, Bonferroni. They avoided the sign flip by adding $P(EF)$ to both
  sides instead of negating. The $P(A)\le 1$ proof they asked for is typeset as a
  Lemma above it.
- **Monotonicity**, $A\subseteq B\implies P(A)\le P(B)$ (card 0008). Correct, clean,
  two lines: $P(B)=P(A)+P(BA^{c})$ by disjointness, $P(BA^{c})\ge 0$ by axiom 1.
  Handwriting filed at `homework/hw01/handwritten/hw01-10.png`. Already transcribed
  as the Lemma at the top of `% ===== SOLUTION 10 =====`; the region below it is
  still theirs to fill.

**Proved along the way and owned:** carving a set by another, taking $P$ of a set
identity, $P(A)\le 1$, monotonicity, and the disjointification $F_i = E_i\cap
E_1^{c}\cap\dots\cap E_{i-1}^{c}$ (they skipped that check — treat as known).

**Open — Ross 10, Boole's inequality.** Attempted on card 0009, answered at 12:45
(`live/answers/t0006-r1.png`), sent back on card 0010. They took the
disjointification route and the **skeleton is correct**: $P(\bigcup E_i) =
P(\bigcup F_i) = \sum P(F_i)$ by axiom 3, then trade up by monotonicity. Two things
were sent back, and only the second is real:

1. They wrote $P(F_i)\ge P(E_i)$ where monotonicity gives $\le$. Fixed on the next
   revision; the main proof above the Aside is now correct and settled.
2. They asserted $\bigcup E_i = \bigcup F_i$ as part of the *definition* of $F_i$.
   It is not — it is the consequence the book's hint asks them to show, and their
   first step rests on it. Card 0010 granted them $\bigcup F_i \subseteq \bigcup E_i$
   as free and asked for the other inclusion.

**Rev 2 (13:38, `live/answers/t0007-r1.png`) — they went at the inclusion by
induction on $n$, not by the least-index argument I pointed at.** Their route works
and is nearly done: base case $n=1$ correct; inductive hypothesis
$\bigcup_1^{n-1}E_i\subseteq\bigcup_1^{n-1}F_i$; take $e\in\bigcup_1^{n}E_i$, done if
$e\in F_n$, else split. Their **first** case ($e\notin E_n$) is complete and correct.
They then wrote "SHIT / I am stuck" on the page and sent it.

**Why they are stuck, and it is a good one.** Their second case reads "$e\in E_n$ and
$e\notin E_i\ \forall i<n$" — which *is* the definition of $F_n$, contradicting the
standing assumption $e\notin F_n$. The case is empty, so of course nothing follows
from it. They negated a conjunction-with-a-quantifier wrongly: "outside every earlier
$E_i$" fails by there being **one** earlier $E_i$ you are inside, not by being
outside all of them. Card 0011 locates exactly that and asks them to state the two
cases $e\notin F_n$ really splits into — the second one finishes with a line they
have already written.

## What they get wrong

**Pattern, now twice running: transcription slips, not thinking errors.** Last turn a
chain that read $P(B)=\dots=P(B)$; this turn a reversed inequality used correctly one
clause later. The mathematics is sound; the pen is not. Flag these in one line and
move on — do not treat them as misunderstandings.

**The two real gaps, both about definitions rather than algebra:**

1. Not distinguishing what a construction is *defined* to be from what has to be
   *proved* about it ($\bigcup E_i=\bigcup F_i$ treated as definitional).
2. Negating a definition that is a conjunction under a quantifier. This is what
   stalled them on Boole and it is the thing to check has landed before moving on —
   $F_n$'s definition has the shape "in this **and** outside all of those", and the
   negation of the second half is existential, not universal.

Earlier in the session: stuck on Problem 1 for three revisions. Not algebra — they
had never put a $P$ in front of a set identity. Naming *which rule applies* failed
twice; naming the physical act and showing it on die numbers ($4/6 = 2/6+2/6$)
cleared it instantly.

## Build status — read this

`board hw build` reports `FAILED` with **no LaTeX log written at all** — the build
directory was untouched and `live/export/*/build/` came out empty. It fails
identically with `hw01.tex` reverted to its last known-good state, and
`board export --build` fails the same way, so **it is not the student's mathematics
and not the transcription**. `board doctor` finds `pdflatex` and it resolves to a
real binary; direct `pdflatex` invocation was refused by this session's permission
wall, which is the most likely cause of the silent failure. Last clean PDF is from
12:11 and does not contain the monotonicity lemma.

Next session: run `board hw build` first thing. If it still fails silently, the
toolchain needs looking at before any more write-up is trusted as compiled.

## Next

Read the inclusion proof coming back on card 0010. Then transcribe **their whole
Boole argument** beneath the Lemma already in `SOLUTION 10` — their route, their
order, with the two corrections folded in as they wrote them, not improved — and
`board hw file 10` the final page (the current `hw01-10.png` is the monotonicity
page and will need keeping or renaming alongside it). Then Problem 12.

## How this student works

- Skips checks they already have, honestly — pace stays high afterwards.
- **Says "I am stuck" on the page, in those words, and means it.** That is a real
  answer and the most useful one they send. It is never a wrong answer: go back one
  step and find what did not land, do not re-pose the same prompt.
- Takes his own route rather than the one pointed at (induction here, not the
  least-index argument). It works. Follow his route.
- Writes questions *and instructions to me* on the page ("(include this in writeup)").
  Read the whole page, not just the mathematics. Never mark a question wrong.
- Says plainly when a hint failed. Change mode, don't rephrase: show the act, with
  numbers.
- Invents his own route. Check it on its own terms; transcribe it, don't improve it.
