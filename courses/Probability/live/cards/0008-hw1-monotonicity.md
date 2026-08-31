---
kind: question
title: The second thing Boole needs — a smaller set has smaller probability
---

The $F_i$ do two jobs at once. They are disjoint, so axiom 3 fires on their union. And each one sits inside the set it came from:

$$F_i \subseteq E_i,$$

since $F_i$ is $E_i$ with things deleted. That is what will let you trade $\sum P(F_i)$ up for $\sum P(E_i)$ and get the inequality.

But the trade needs a fact you do not yet have:

$$A \subseteq B \ \implies\ P(A) \le P(B).$$

Like $P(A)\le 1$, this reads as obvious and **is not an axiom**. Nothing in the three axioms mentions containment at all. It has to be proved, and it is proved by the move you have now used four times: carve the bigger set into the part inside $A$ and the part outside it.

Since $A\subseteq B$, the part of $B$ inside $A$ is all of $A$. So

$$B = A \cup A^{c}B,$$

and those two pieces are disjoint.

---

**Your move.** Take $P$ of that, and finish it: prove that $A \subseteq B$ implies $P(A) \le P(B)$.

Two lines. The last step is the same appeal to non-negativity you made when you proved $P(A)\le 1$.
