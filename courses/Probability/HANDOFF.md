# HANDOFF

**Session:** Homework 1 sitting (`board open` — homework, `homework/hw01/hw01.tex`).
Due 2 September 2026.

## What the sheet assigns

From `homework/hw01/assignment/Prob.Homework1.2026.pdf`, in this order:

1. Instructor's own: from the axioms, prove $P(E\cup F)=P(E)+P(F)-P(EF)$.
2. Ross ch.1 ex. 8 — Bonferroni's inequality.
3. Ross ch.1 ex. 10 — Boole's inequality.
4. Ross ch.1 ex. 12 — first-occurrence probability $P(E)/[P(E)+P(F)]$.
5. Ross ch.1 ex. 39 — stores A/B/C, Bayes.
6. Ross ch.1 ex. 41 — black/brown rats, Bayes in two parts.

Practice only, **not** handed in: ch.1 ex. 4, 5, 6, 7, 17. Left undone by design.

## State of the scaffold

`homework/hw01/hw01.tex` already carries all six statements, transcribed faithfully
and verified against `chapters/ch01-.../reading/ch01.pdf` (book pages 15–19).
All six solution regions are **empty**. `board hw` is bound to the file and reports
0 of 6 written up.

## Where the lesson got to

Card 0001 (`live/cards/0001-hw1-plan-disjoint-split.md`) — stated the plan, then taught
the one thing Problem 1 needs: axiom 3 pays out only on mutually exclusive events, so
the method is to carve into disjoint pieces, using $F = EF \cup E^{c}F$.

It ends with a **hand-check**, not the exercise: with $\Omega=\{1,\dots,6\}$,
$E=\{1,2,3,4\}$, $F=\{3,4,5\}$, list $EF$, $E^{c}F$, $E\cup E^{c}F$, and say whether
that equals $E\cup F$ and whether $E$ and $E^{c}F$ are disjoint.

Expected: $EF=\{3,4\}$, $E^{c}F=\{5\}$, $E\cup E^{c}F=\{1,2,3,4,5\}=E\cup F$, disjoint.

## Next thing to teach

Once the check lands, pose Problem 1 itself. The proof they should reach:
$E\cup F = E \cup E^{c}F$ (disjoint, so axiom 3 gives
$P(E\cup F)=P(E)+P(E^{c}F)$), and $F = EF \cup E^{c}F$ (disjoint, so
$P(F)=P(EF)+P(E^{c}F)$, hence $P(E^{c}F)=P(F)-P(EF)$). Substitute.
Do **not** hand them that — they write it on the slate.

Nothing has come back from the student yet in this session, so nothing is known
right or wrong. No prior handoff existed.
