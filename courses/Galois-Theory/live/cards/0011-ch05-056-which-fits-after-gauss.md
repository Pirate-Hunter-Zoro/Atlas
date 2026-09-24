---
kind: question
title: ch05-056-which-fits-after-gauss
---
Yes, degree 1 in $y$ is necessary, but Gauss's lemma does not use it. Your step after Gauss does.

Gauss's lemma, in the form your proof uses:

> Let $R$ be a UFD (unique factorization domain) with fraction field $F$. If $h \in R[x]$ and $h = ab$ with $a, b \in F[x]$, then there is a nonzero $c \in F$ with $ca \in R[x]$ and $c^{-1}b \in R[x]$.

Here $R = K[y]$ and $F = K(y)$. So $R[x] = K[y][x] = K[x][y]$. Nothing about degree appears. It only moves the denominators from one factor to the other.

Your example is exactly this. With $a = y^{-3}x^3$ and $b = y^3(1+x)$, taking $c = y^3$ gives $ca = x^3$ and $c^{-1}b = 1 + x$. Both are in $K[x][y]$, and their product is unchanged.

Degree 1 enters next. Degrees in $y$ add, because $K[x]$ is an integral domain. The product has $y$-degree 1, since $g \neq 0$. So one factor has $y$-degree 0 and the other $y$-degree 1. Without that, you could not say $a \in K[x]$.

Back to 05.6, still open.

Let $R$ be an integral domain and $f = f_0 + f_1 x + \cdots + f_n x^n \in R[x]$ with $f_0, \ldots, f_n$ relatively prime. Let $p$ be a prime of $R$ with $p \mid f_i$ for $1 \le i \le n$, $p \nmid f_0$, and $p^2 \nmid f_n$. Show $f$ is irreducible in $R[x]$.

Take $R = \mathbb{Z}$ and $p = 2$:

$$f = 1 + 2x + 2x^2, \qquad f = 1 + 2x + 4x^2, \qquad f = 2 + 2x + 2x^2.$$

- integral domain — a commutative ring with $1 \ne 0$ and no zero divisors.
- relatively prime coefficients — the only common divisors of $f_0, \ldots, f_n$ are units.
- prime $p$ — a nonzero non-unit with $p \mid ab \Rightarrow p \mid a$ or $p \mid b$.

Which of the three satisfies every hypothesis with $p = 2$? For each of the other two, name the hypothesis it breaks.
