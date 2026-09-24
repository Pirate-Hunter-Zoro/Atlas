---
kind: question
title: ch05-056-reduce-mod-p
---
You cannot reduce $1 + 2x + 4x^2$, because it is irreducible in $\mathbb{Z}[x]$. Failing a hypothesis does not make a polynomial reducible. The test only says "these conditions are enough"; it says nothing when they fail.

Why it is irreducible anyway: its coefficients $1, 2, 4$ have no common factor, so any factorization would be into two linear factors. Its discriminant is $2^2 - 4 \cdot 4 \cdot 1 = -12 < 0$, so it has no real roots, let alone rational ones.

Your sorting is right. $1 + 2x + 2x^2$ fits. $1 + 2x + 4x^2$ breaks $p^2 \nmid f_n$. For $2 + 2x + 2x^2$, the broken hypotheses are $p \nmid f_0$ and relative primality, since $2$ divides every coefficient. And $2(1 + x + x^2)$ really is a factorization in $\mathbb{Z}[x]$, because $2$ is not a unit in $\mathbb{Z}$.

Now the proof. The first move is to reduce modulo $p$.

Let $R$ be an integral domain and $f = f_0 + f_1 x + \cdots + f_n x^n \in R[x]$ with $f_0, \ldots, f_n$ relatively prime. Let $p$ be a prime of $R$ with $p \mid f_i$ for $1 \le i \le n$, $p \nmid f_0$, and $p^2 \nmid f_n$. Show $f$ is irreducible in $R[x]$.

- integral domain — a commutative ring with $1 \ne 0$ and no zero divisors.
- relatively prime coefficients — the only common divisors of $f_0, \ldots, f_n$ are units.
- prime $p$ — a nonzero non-unit with $p \mid ab \Rightarrow p \mid a$ or $p \mid b$.
- $\bar{g}$ — the image of $g \in R[x]$ in $(R/(p))[x]$: reduce every coefficient mod $p$.
- $R/(p)$ is an integral domain, because $p$ is prime.

Take $R = \mathbb{Z}$, $p = 2$, $f = 1 + 2x + 2x^2$. What is $\bar{f}$ in $\mathbb{F}_2[x]$? If $f = gh$ in $\mathbb{Z}[x]$, what are the possible degrees of $\bar{g}$ and $\bar{h}$?
