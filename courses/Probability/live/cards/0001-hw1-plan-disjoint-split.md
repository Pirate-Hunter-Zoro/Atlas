---
kind: question
title: Homework 1 — the six problems, and the split everything rests on
---

The sheet assigns six, and we do all of them in this order:

1. **Problem 1 (stated on the sheet).** From the axioms, prove $P(E \cup F) = P(E) + P(F) - P(EF)$.
2. **Ross 8** — Bonferroni's inequality.
3. **Ross 10** — Boole's inequality.
4. **Ross 12.**
5. **Ross 39.**
6. **Ross 41.**

Practice problems 4, 5, 6, 7, 17 are not handed in. We leave them.

Starting with Problem 1.

---

Axiom 3 is the only axiom that lets you add probabilities, and it pays out **only on mutually exclusive events**:

$$P\!\left(\bigcup_{i} E_i\right) = \sum_i P(E_i) \quad \text{when the } E_i \text{ are pairwise disjoint.}$$

$E$ and $F$ are not disjoint in general, so you cannot write $P(E\cup F) = P(E)+P(F)$. That is the whole difficulty of Problem 1, and the whole method is: **carve everything into disjoint pieces first, then add.**

The carving tool is one identity. For any two events, $E$ slices $F$ into the part inside $E$ and the part outside it:

$$F = EF \cup E^{c}F, \qquad EF \cap E^{c}F = \emptyset.$$

Every point of $F$ is either in $E$ or not; nothing is in both halves.

---

**Your move.** Before the proof, make sure the operation is fluent. Roll one die, $\Omega = \{1,2,3,4,5,6\}$, and take

$$E = \{1,2,3,4\}, \qquad F = \{3,4,5\}.$$

Write out, as explicit lists of outcomes:

- $EF$
- $E^{c}F$
- $E \cup E^{c}F$

and say whether that last set equals $E \cup F$, and whether $E$ and $E^{c}F$ are disjoint.
