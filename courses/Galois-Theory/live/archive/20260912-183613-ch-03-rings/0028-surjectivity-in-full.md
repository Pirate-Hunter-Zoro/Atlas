---
kind: question
title: $d = b_1 b_2$. Correct — now do it to an arbitrary element.
---

Correct, and note where the hypothesis paid for itself: $d = b_1 b_2 \neq 0$ because $R$ is an **integral domain**. In a ring with zero divisors the product of two non-zero denominators can be $0$, and the whole move collapses. That is what "integral domain" is doing in this problem.

Nothing else is missing. Two coefficients becomes finitely many the same way, and one polynomial becomes two.

**Your move.** Prove that $\phi$ is surjective: every element of $F(x_1,\ldots,x_n)$ is $\phi$ of something in $\operatorname{Frac}(R[x_1,\ldots,x_n])$.

What the statement uses:

- $R$ is an integral domain and $F = \operatorname{Frac}(R)$.
- $\operatorname{Frac}(S)$, for an integral domain $S$: classes of pairs $(p,q)$ with $p, q \in S$, $q \neq 0$, written $p/q$, where $p/q = p'/q'$ exactly when $pq' = p'q$.
- Consequently $p/q = (dp)/(dq)$ for any $d \neq 0$.
- $R[x_1,\ldots,x_n]$: polynomials in $n$ variables with coefficients in $R$ — finitely many non-zero coefficients, by definition.
- $F(x_1,\ldots,x_n) = \operatorname{Frac}(F[x_1,\ldots,x_n])$.
- $R \subseteq F$ and hence $R[x_1,\ldots,x_n] \subseteq F[x_1,\ldots,x_n]$, so a pair over $R[x_1,\ldots,x_n]$ is also a pair over $F[x_1,\ldots,x_n]$; $\phi$ sends the class of such a pair in $\operatorname{Frac}(R[x_1,\ldots,x_n])$ to its class in $F(x_1,\ldots,x_n)$.
- *Surjective:* for every $\beta$ in the codomain there is some $\alpha$ in the domain with $\phi(\alpha) = \beta$.
