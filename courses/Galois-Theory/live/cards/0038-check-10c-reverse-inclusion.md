---
kind: lesson
title: check 10c-reverse-inclusion
---
You do not check elements one at a time. $\mathbb{Q}(\alpha, \zeta_n)$ is the smallest field containing $\mathbb{Q}$, $\alpha$ and $\zeta_n$. Call the splitting field $L$. It is a field and it contains $\mathbb{Q}$. So once $\alpha \in L$ and $\zeta_n \in L$, you get $\mathbb{Q}(\alpha, \zeta_n) \subseteq L$ for free.

That turns "every element" into two elements. $\alpha$ is free: it is a root of $x^n - a$, and $L$ contains every root. Only $\zeta_n$ is left.

Your first inclusion is correct. The jump from $(\beta\alpha^{-1})^n = 1$ to $\beta\alpha^{-1} = \zeta_n^k$ is right. The write-up will give it its one-line reason: the $n$ powers of $\zeta_n$ are $n$ distinct roots of $x^n - 1$, and that polynomial has no others.

The exercise is 10(c). Let $a \in \mathbb{Q}^\times$ and let $\alpha$ be any complex root of $x^n - a$. Show the splitting field of $x^n - a$ over $\mathbb{Q}$ is $\mathbb{Q}(\alpha, \zeta_n)$. Done: $L \subseteq \mathbb{Q}(\alpha, \zeta_n)$. Remaining: $\mathbb{Q}(\alpha, \zeta_n) \subseteq L$.

What you need:
- $a \in \mathbb{Q}^\times$ means $a$ is a nonzero rational.
- $L$ is the splitting field: the field generated over $\mathbb{Q}$ by all complex roots of $x^n - a$.
- $\alpha^n = a$, so $\alpha \ne 0$.
- $\zeta_n = e^{2\pi i/n}$, so $\zeta_n^n = 1$.
- $\mathbb{Q}(\alpha, \zeta_n)$ is the smallest subfield of $\mathbb{C}$ containing $\alpha$ and $\zeta_n$.
- A field is closed under products and quotients by nonzero elements.

Show $\zeta_n \in L$. Find two roots of $x^n - a$ whose quotient is $\zeta_n$, and say why each one is a root.
