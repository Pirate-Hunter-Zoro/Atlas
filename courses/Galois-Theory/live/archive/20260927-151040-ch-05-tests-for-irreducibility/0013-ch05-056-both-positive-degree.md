---
kind: question
title: ch05-056-both-positive-degree
---
Right: $\bar{f} = \bar{f_0}$ has degree $0$, so $\bar{g}$ and $\bar{h}$ both have degree $0$. One correction to the reason. Degrees add in $(R/(p))[x]$ because $R/(p)$ is an integral domain. That $R$ is one is not what you need here.

Degree $0$ in $(R/(p))[x]$ says something about $g$ itself. Every coefficient of $g$ in degree $1$ or higher is divisible by $p$. The same goes for $h$.

Now suppose both factors have positive degree. Write $g = g_0 + \cdots + g_k x^k$ and $h = h_0 + \cdots + h_m x^m$ with $k, m \ge 1$ and $g_k, h_m \ne 0$. Take $\mathbb{Z}$, $p = 2$, and $g = h = 1 + 2x$ as a test case. Their product is $1 + 4x + 4x^2$.

Let $R$ be an integral domain and $f = f_0 + f_1 x + \cdots + f_n x^n \in R[x]$ with $f_0, \ldots, f_n$ relatively prime. Let $p$ be a prime of $R$ with $p \mid f_i$ for $1 \le i \le n$, $p \nmid f_0$, and $p^2 \nmid f_n$. Show $f$ is irreducible in $R[x]$.

- integral domain — a commutative ring with $1 \ne 0$ and no zero divisors.
- relatively prime coefficients — the only common divisors of $f_0, \ldots, f_n$ are units.
- prime $p$ — a nonzero non-unit with $p \mid ab \Rightarrow p \mid a$ or $p \mid b$.
- $\bar{g}$ — the image of $g$ in $(R/(p))[x]$: reduce every coefficient mod $p$.
- known so far — $\bar{g}$ and $\bar{h}$ are nonzero constants, so $p \mid g_i$ for $i \ge 1$ and $p \mid h_j$ for $j \ge 1$.

In the test case, which hypothesis on $1 + 4x + 4x^2$ fails? In general, if $k, m \ge 1$, what does $f_n = g_k h_m$ force, and which hypothesis does it break?
