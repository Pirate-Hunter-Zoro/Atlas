---
kind: lesson
title: check 10c-alpha-zeta-root
---
Stop solving for $\zeta_n$. Test a candidate root instead: is $\alpha\zeta_n$ a root of $x^n - a$?

Your chain is correct algebra. Its last line, $a(\alpha^{-1}\zeta_n)^n = 1$, says $\alpha^{-1}\zeta_n$ is a root of $x^n - a^{-1}$. That is a different polynomial, so it tells you nothing about $L$. That is why you stalled.

The recipe has three moves:
1. $\alpha\zeta_n$ is a root of $x^n - a$. This is the missing fact.
2. So $\alpha\zeta_n \in L$, because $L$ contains every root. And $\alpha \in L$, which you already have.
3. So $\zeta_n = (\alpha\zeta_n)/\alpha \in L$, because a field is closed under quotients and $\alpha \ne 0$.

The exercise is 10(c). Let $a \in \mathbb{Q}^\times$ and let $\alpha$ be any complex root of $x^n - a$. Show the splitting field of $x^n - a$ over $\mathbb{Q}$ is $\mathbb{Q}(\alpha, \zeta_n)$. Done: $L \subseteq \mathbb{Q}(\alpha, \zeta_n)$, and $\alpha \in L$. Remaining: $\zeta_n \in L$.

What you need:
- $a \in \mathbb{Q}^\times$ means $a$ is a nonzero rational.
- $L$ is the splitting field: the field generated over $\mathbb{Q}$ by all complex roots of $x^n - a$.
- $\alpha^n = a$, so $\alpha \ne 0$.
- $\zeta_n = e^{2\pi i/n}$, so $\zeta_n^n = 1$.
- In any field, $(xy)^n = x^n y^n$.
- A field is closed under products and quotients by nonzero elements.

Compute $(\alpha\zeta_n)^n$ and show it equals $a$. Then finish: conclude $\zeta_n \in L$.
