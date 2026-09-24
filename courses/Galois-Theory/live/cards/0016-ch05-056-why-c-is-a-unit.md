---
kind: question
title: ch05-056-why-c-is-a-unit
---
Because "relatively prime" is exactly that statement: $c$ divides every $f_i$, and the only elements dividing every $f_i$ are units. So $c$ is a unit.

Spelled out:
- You showed $f_i = c\,h_i$ for $0 \le i \le n$, so $c \mid f_0, c \mid f_1, \ldots, c \mid f_n$.
- That makes $c$ a common divisor of $f_0, \ldots, f_n$.
- Relatively prime means every common divisor is a unit.
- So $c$ is a unit of $R$, hence of $R[x]$, and $f = c\,h$ is not a proper factorisation.

That is the whole constant case. The prime $p$ plays no part in it. Its job was only the positive-degree case, which you already closed with $p^2 \mid f_n$.

One slip to fix on your page: with $g = c$ constant, the WLOG line should read $\deg h = \deg f$, not $\deg g = \deg f$.

The test case is the last thing before this exercise is done. Take $f = 3 + 6x$ in $\mathbb{Z}[x]$ with $p = 2$. It satisfies $2 \mid 6$, $2 \nmid 3$, $4 \nmid 6$, yet $f = 3(1 + 2x)$ with neither factor a unit.

- relatively prime coefficients — the only common divisors of $f_0, \ldots, f_n$ are units.
- units of $\mathbb{Z}$ — only $\pm 1$.

Name a common divisor of the coefficients $3$ and $6$ that is not a unit. Which hypothesis of 05.6 does $3 + 6x$ therefore break, and at which line of your proof would the argument stop?
