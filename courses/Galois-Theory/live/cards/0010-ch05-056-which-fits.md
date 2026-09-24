---
kind: question
title: ch05-056-which-fits
---
05.4 is done: your proof is correct. You fixed the ring. The factors land in $K[x][y]$, and the degree-in-$y$ step is what puts $a$ in $K[x]$.

The write-up is not updated yet. My edit to the 05.4 solution region was refused by the permission check, because the file's header reserves solution regions for you. The next turn will sort out the permission. You do not need to do anything.

One slip remains in your line. You called the scaling constant $g$ and put it in $K(y)[x]$. It is a nonzero element of $K(y)$, and $g$ is already the polynomial in the problem. Call it $c \in K(y)$.

Next is 05.6. It is Eisenstein's criterion read from the other end.

Let $R$ be an integral domain and $f = f_0 + f_1 x + \cdots + f_n x^n \in R[x]$ with $f_0, \ldots, f_n$ relatively prime. Let $p$ be a prime of $R$ with $p \mid f_i$ for $1 \le i \le n$, $p \nmid f_0$, and $p^2 \nmid f_n$. Show $f$ is irreducible in $R[x]$.

Take $R = \mathbb{Z}$ and $p = 2$. Three candidates:

$$f = 1 + 2x + 2x^2, \qquad f = 1 + 2x + 4x^2, \qquad f = 2 + 2x + 2x^2.$$

Everything it uses:

- integral domain — a commutative ring with $1 \ne 0$ and no zero divisors.
- relatively prime coefficients — the only common divisors of $f_0, \ldots, f_n$ in $R$ are units.
- prime $p$ — a nonzero non-unit with $p \mid ab \Rightarrow p \mid a$ or $p \mid b$.
- irreducible in $R[x]$ — not a unit, and in any factorization $f = ab$ one of $a, b$ is a unit of $R[x]$.

Which of the three satisfies every hypothesis with $p = 2$? For each of the other two, name the hypothesis it breaks.
