---
kind: question
title: ch05-056-constant-divides-all
---
Not yet: the last line is false. With $g = c$ a constant, $\bar{g} = \bar{c}$ is a constant too, always. So "$\bar{g}$ is not constant" never happens, and there is no contradiction.

Your step "$p \nmid g$" is right. After it, nothing goes wrong mod $p$: $p \mid h_i$ for $i \ge 1$, so $\bar{h}$ is constant and $\bar{f} = \bar{c}\,\bar{h}_0$ is fine.

The test case shows why this route must fail. In $f = 3 + 6x = 3(1 + 2x)$ with $p = 2$, all three conditions on $p$ hold. Yet $c = 3$ is not a unit. So no argument that uses only $p$ can finish this case. It needs the one hypothesis you have not used yet.

You already wrote the line that does it: $f_i = g\,h_i$ for every $i$.

Let $R$ be an integral domain and $f = f_0 + f_1 x + \cdots + f_n x^n \in R[x]$ with $f_0, \ldots, f_n$ relatively prime. Let $p$ be a prime of $R$ with $p \mid f_i$ for $1 \le i \le n$, $p \nmid f_0$, and $p^2 \nmid f_n$. Show $f$ is irreducible in $R[x]$.

- integral domain — a commutative ring with $1 \ne 0$ and no zero divisors.
- relatively prime coefficients — the only common divisors of $f_0, \ldots, f_n$ are units.
- prime $p$ — a nonzero non-unit with $p \mid ab \Rightarrow p \mid a$ or $p \mid b$.
- irreducible in $R[x]$ — nonzero, not a unit, and in any factorisation $f = gh$ one of $g, h$ is a unit of $R[x]$.
- units of $R[x]$ — exactly the units of $R$, since $R$ is a domain.
- known so far — if $f = gh$ then $\deg g$ and $\deg h$ cannot both be positive.

The line $f_i = c\,h_i$ for every $i$ says $c$ divides what? Use that to show $c$ is a unit, and say which hypothesis $3 + 6x$ breaks.
