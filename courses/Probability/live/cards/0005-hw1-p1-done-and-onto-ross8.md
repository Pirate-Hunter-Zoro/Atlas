---
kind: correct
title: Problem 1 is done — and the fact Problem 2 will need
---

Correct. That is a complete proof.

The step that carried it is the one you were missing an hour ago: putting $P$ in front of a set identity and letting the annotated disjointness fire axiom 3. You did it twice and the two results substituted straight into your three-term sum. I am transcribing it into `hw01.tex` as you wrote it — the three-way carve, not the two-way one.

---

**Problem 2 is Ross 8, Bonferroni's inequality:**

$$P(EF) \ \ge\ P(E) + P(F) - 1.$$

Rearrange what you just proved and you get $P(EF) = P(E) + P(F) - P(E\cup F)$. So the inequality is asking for one thing only: that $P(E\cup F)$ is never bigger than $1$.

That sounds too obvious to prove, which is exactly the trap. **It is not an axiom.** The axioms give you $P(\Omega) = 1$, non-negativity, and additivity on disjoint sets — nothing that directly says an arbitrary event's probability is capped. It has to be derived, and it is derived by the move you now own.

---

**Your move.** Before Problem 2, one line. Let $A$ be any event. Prove from the axioms that

$$P(A) \le 1.$$

Carve $\Omega$ the way you carved $E$ and $F$, take $P$, and then use the one axiom that says something is non-negative.
