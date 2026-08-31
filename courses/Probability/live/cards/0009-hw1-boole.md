---
kind: question
title: Monotonicity holds — now Problem 3, Boole's inequality
---

Correct. $P(B) = P(A) + P(BA^{c})$ by disjointness, $P(BA^{c}) \ge 0$ by axiom 1, so $P(A) = P(B) - P(BA^{c}) \le P(B)$. The step that carried it is the same one every time: take $P$ of the carve, then throw away a non-negative piece.

One note on the writing, not the mathematics. Your first line ends `$\dots = P(A) + P(BA^{c}) = P(B)$` — the chain starts at $P(B)$ and ends at $P(B)$, so as written it says nothing. Drop that last equality; the line you want is $P(B) = P(A) + P(BA^{c})$.

You now hold both halves: the disjointification $F_1 = E_1$, $F_i = E_i E_1^{c}\cdots E_{i-1}^{c}$, and $A\subseteq B \implies P(A)\le P(B)$. Nothing else needs teaching.

---

**Your move. Problem 3 (Ross 1.10).** Show that

$$P\!\left(\bigcup_{i=1}^{n} E_i\right) \le \sum_{i=1}^{n} P(E_i).$$

This is known as Boole's inequality.

*Hint (as printed): Either use Equation (1.2) and mathematical induction, or else show that $\bigcup_{i=1}^{n} E_i = \bigcup_{i=1}^{n} F_i$, where $F_1 = E_1$, $F_i = E_i \bigcap_{j=1}^{i-1} E_j^{c}$, and use property (iii) of a probability.*

Either route is fine. Say at the top which one you are taking.
