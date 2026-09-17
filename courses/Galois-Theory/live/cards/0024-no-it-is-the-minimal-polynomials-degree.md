---
kind: lesson
title: no-it-is-the-minimal-polynomials-degree
---
No, it will not always be $2$. Two was the answer for $\sqrt2$ and for nothing
else in particular. The degree $[K(\beta):K]$ is the degree of the minimal
polynomial of $\beta$ over $K$ — that number and no other. For $\sqrt2$ the
minimal polynomial over $\mathbb{Q}$ is $x^2 - 2$, degree $2$, so the degree is
$2$ and the basis $\{1, \sqrt2\}$ has two entries.

So the count is not a constant, it is read off the polynomial. If $\beta$ has
minimal polynomial of degree $n$, then $[K(\beta):K] = n$ and the basis is
$1, \beta, \beta^2, \dots, \beta^{n-1}$ — exactly $n$ elements, the powers
stopping one short of $n$. Nothing in that depends on which field or which
$\beta$; feed it a degree, it gives back that degree.

Your margin note "just for this example" is the right instinct about $\beta =
\sqrt[3]{2}$ being specific. But the degree is not specific in that way. It is
determined, and the thing that determines it is sitting in the first line you
wrote.

What it uses:

- $[M:L]$ — the dimension of $M$ as a vector space over $L$.
- Basis — a linearly independent spanning list; the number of entries in it is
  the dimension.
- Algebraic over $K$ — some non-zero polynomial in $K[x]$ has it as a root.
- Minimal polynomial of $\beta$ over $K$ — the monic polynomial in $K[x]$ of
  least degree with $\beta$ as a root.
- $\beta$ algebraic over $K$ with minimal polynomial of degree $n$ gives
  $[K(\beta):K] = n$, with basis $1, \beta, \dots, \beta^{n-1}$.
- $x^3 - 2$ is irreducible over $\mathbb{Q}$, so it is the minimal polynomial of
  any of its roots.

**Your move.** Same case, run through that fact rather than through $\sqrt2$.
Let $\beta$ be a root of $x^3 - 2$ over $\mathbb{Q}$. Its minimal polynomial
over $\mathbb{Q}$ is $x^3 - 2$, of degree $3$. Using the fact above and only
that: what is $[\mathbb{Q}(\beta):\mathbb{Q}]$, and write out the basis in full.
