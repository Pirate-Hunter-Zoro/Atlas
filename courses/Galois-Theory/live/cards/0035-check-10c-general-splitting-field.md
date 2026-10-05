---
kind: lesson
title: check 10c-general-splitting-field
---
10(b) is correct, and agreed. You took the other tower: $[E:\mathbb{Q}(\omega)] \le 3$ and $[\mathbb{Q}(\omega):\mathbb{Q}] = 2$ give $[E:\mathbb{Q}] \le 6$. With $6 \mid [E:\mathbb{Q}]$ that forces $6$.

One fix to the reason for $\le 3$. Irreducibility over $\mathbb{Q}$ is not what does it. What does it: $x^3 - 2$ has coefficients in $\mathbb{Q} \subseteq \mathbb{Q}(\omega)$ and has $\sqrt[3]{2}$ as a root. So the minimal polynomial of $\sqrt[3]{2}$ over $\mathbb{Q}(\omega)$ divides it, and has degree at most $3$.

The last clause is one line: $[\mathbb{Q}(\sqrt[3]{2}):\mathbb{Q}] = 3 \ne 6$, so $\mathbb{Q}(\sqrt[3]{2}) \ne E$. I have added that line to the write-up.

**Problem 10(c).** Let $a \in \mathbb{Q}^{\times}$ and let $\alpha$ be any complex root of $x^n - a$. Show that the splitting field of $x^n - a$ over $\mathbb{Q}$ is $\mathbb{Q}(\alpha, \zeta_n)$.

This is 10(a) with $3$ replaced by $n$ and $2$ by $a$. The recipe is the same two moves:
1. Write down $n$ distinct roots of $x^n - a$ built from $\alpha$ and $\zeta_n$. A degree-$n$ polynomial has at most $n$ roots, so those are all of them.
2. Show each field contains the other.

What you need:
- $\mathbb{Q}^{\times}$ is the nonzero rationals, so $a \ne 0$.
- $\alpha^n = a$.
- $\zeta_n = e^{2\pi i/n}$. Its powers $1, \zeta_n, \dots, \zeta_n^{n-1}$ are distinct, and $\zeta_n^n = 1$.
- The splitting field of $f$ over $\mathbb{Q}$ is the field generated over $\mathbb{Q}$ by all the complex roots of $f$.
- A nonzero polynomial of degree $n$ has at most $n$ roots in a field.
- A field is closed under products and quotients by nonzero elements.

Show that the splitting field of $x^n - a$ over $\mathbb{Q}$ is $\mathbb{Q}(\alpha, \zeta_n)$, for any complex root $\alpha$ of $x^n - a$ with $a \in \mathbb{Q}^{\times}$.
