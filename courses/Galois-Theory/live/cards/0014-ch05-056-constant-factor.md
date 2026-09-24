---
kind: question
title: ch05-056-constant-factor
---
Your conclusion $p^2 \mid f_n$ is right, but two steps under it need fixing.

First, the reason $p \mid g_k$. It does not come from $p \mid f_i$; those are coefficients of $f$, not of $g$. It comes from $\bar{g}$ being a constant. That forces $p$ to divide every coefficient of $g$ in degree $1$ or higher, and $g_k$ is one of them because $k \ge 1$. The same goes for $h_m$.

Second, "not a unit" is not the same as "positive degree". A factor can be a constant that is not a unit, and your argument never touches that case. So the case $k, m \ge 1$ is done, and one case is left: $g = c$ is a constant in $R$.

Test case: in $\mathbb{Z}[x]$ take $f = 3 + 6x$ and $p = 2$. Then $2 \mid 6$, $2 \nmid 3$ and $4 \nmid 6$. Yet $f = 3(1 + 2x)$, and neither factor is a unit.

Let $R$ be an integral domain and $f = f_0 + f_1 x + \cdots + f_n x^n \in R[x]$ with $f_0, \ldots, f_n$ relatively prime. Let $p$ be a prime of $R$ with $p \mid f_i$ for $1 \le i \le n$, $p \nmid f_0$, and $p^2 \nmid f_n$. Show $f$ is irreducible in $R[x]$.

- integral domain — a commutative ring with $1 \ne 0$ and no zero divisors.
- relatively prime coefficients — the only common divisors of $f_0, \ldots, f_n$ are units.
- prime $p$ — a nonzero non-unit with $p \mid ab \Rightarrow p \mid a$ or $p \mid b$.
- irreducible in $R[x]$ — nonzero, not a unit, and in any factorisation $f = gh$ one of $g, h$ is a unit of $R[x]$.
- units of $R[x]$ — exactly the units of $R$, since $R$ is a domain.
- known so far — if $f = gh$ then $\deg g$ and $\deg h$ cannot both be positive.

Which hypothesis does $3 + 6x$ break? In general, if $f = gh$ with $g = c \in R$ a constant, show that $c$ is a unit.
