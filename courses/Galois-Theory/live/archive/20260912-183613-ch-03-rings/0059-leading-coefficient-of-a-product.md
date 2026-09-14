---
kind: correct
title: $5x+1$, degree $1$. Correct — now the coefficient that cannot die.
---

Correct. Two polynomials of degree $1$, product of degree $1$. The step that
did it is the one to hold on to: the $x^{2}$ coefficient was $2 \cdot 3$, and
$2 \cdot 3 = 0$ in $\mathbb{Z}_{6}$, so the top term vanished and the degree
fell.

Now the other side of it, which is where $R$ an integral domain earns its
keep.

---

**Your move.** Let $R$ be an integral domain and let $f, g \in R[x]$ both be
non-zero, with
$$\deg f = n, \quad \deg g = m,$$
so $f = a_{0} + \cdots + a_{n}x^{n}$ with $a_{n} \neq 0$, and
$g = b_{0} + \cdots + b_{m}x^{m}$ with $b_{m} \neq 0$.

Write down the coefficient of $x^{n+m}$ in $fg$, and say in one line why it is
not $0$.

(You already have the formula: the coefficient of $x^{d}$ in $fg$ is
$\sum_{i+j=d} a_{i}b_{j}$. The question is what that sum reduces to when
$d = n+m$, and what stops the survivor from being zero.)
