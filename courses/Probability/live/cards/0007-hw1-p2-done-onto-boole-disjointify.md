---
kind: correct
title: Problem 2 is done — and the trick Problem 3 turns on
---

Correct, both parts. And you dodged the one trap in it: instead of negating $P(E\cup F)\le 1$ and worrying about which way the inequality turns, you added $P(EF)$ to both sides. Nothing had to flip. That is the better route.

Noted — the $P(A)\le 1$ proof goes into the write-up as a lemma above it. I am transcribing Problem 2 now.

---

**Problem 3 is Ross 10, Boole's inequality**, and it needs one construction you have not met.

You cannot add $P(E_1),\dots,P(E_n)$ directly — the $E_i$ overlap, and axiom 3 still only pays out on disjoint sets. So you **shrink each set until they are disjoint**: keep only the part of $E_i$ that no earlier $E_j$ already covered.

$$F_1 = E_1, \qquad F_i = E_i \cap E_1^{c} \cap E_2^{c} \cap \dots \cap E_{i-1}^{c}.$$

In words: $F_i$ is $E_i$ with everything already counted stripped out.

Watch it on $\Omega=\{1,\dots,6\}$ with

$$E_1=\{1,2,3\},\quad E_2=\{2,3,4\},\quad E_3=\{4,5\}.$$

$F_1 = \{1,2,3\}$. For $F_2$, take $E_2$ and delete anything in $E_1$: the $2$ and the $3$ go, leaving $F_2 = \{4\}$.

---

**Your move.** One line, before the exercise. Compute

$$F_3 = E_3 \cap E_1^{c} \cap E_2^{c}$$

for those three sets, as an explicit list of outcomes.
