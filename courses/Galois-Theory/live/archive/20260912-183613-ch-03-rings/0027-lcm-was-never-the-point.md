---
kind: note
title: Both questions are right to ask. The lcm was never the point.
---

**1. The lcm is $\mathbb{Z}$'s convenience, and you do not need it.** You are right that a general integral domain $R$ has no lcm to appeal to — no ordering, no factorisation. But look at what $d$ was ever asked to do: clear finitely many denominators at once. *Any* common multiple does that; the least one was never required. And every commutative ring has one available — the **product** of the denominators. In $\mathbb{Z}$, for $\tfrac12 x + \tfrac13$, the product $2 \cdot 3 = 6$ clears them, and so would $12$, or $6000$. Minimality is a habit carried over from arithmetic, not a hypothesis of this problem. So the $\mathbb{Q}(x)$ case was not a special trick: replace "lcm" by "product" and the argument stops mentioning $\mathbb{Z}$ at all.

**2. Finitely many non-zero coefficients is not a requirement — it is the definition.** A polynomial *is* a tuple with only finitely many non-zero entries. Drop that and you have a formal power series, a different object living in $F[[x_1,\ldots,x_n]]$; without it $F[x_1,\ldots,x_n]$ is not even closed under the multiplication you know, since each coefficient of a product is a *finite* sum. So it is not a condition to impose on $F[x_1,\ldots,x_n]$ — it is what makes it that ring rather than the power series ring.

**Your move.** Let $R$ be an integral domain, $F = \operatorname{Frac}(R)$, and suppose a polynomial in $F[x]$ has exactly two non-zero coefficients, $a_1/b_1$ and $a_2/b_2$, with $a_i, b_i \in R$ and $b_i \neq 0$. Name a single $d \in R$, $d \neq 0$, such that multiplying that polynomial by $d$ puts both of its coefficients in the image of $R$ inside $F$.
