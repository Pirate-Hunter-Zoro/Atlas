---
kind: lesson
title: answer ch05-054-why-not-solve-for-g
---
No, not that way -- solving for $g$ throws away the only thing you have. Your setup is right: assume $f - yg = ab$ with $a, b \in K(y)[x]$ and neither a unit. The step that goes nowhere is rearranging to $g = y^{-1}f - y^{-1}ab$. The letter $y$ is invertible in $K(y)$, so that equation is legal, but $a$ and $b$ are allowed to contain $y$, and after the rearrangement both sides do. A statement with $y$ in it cannot contradict "$f$ and $g$ are coprime in $K[x]$", because $K[x]$ has no $y$ in it at all. Nothing there forces a common divisor.

The contradiction does exist, and it comes from counting the degree in $y$, not from solving for $g$. So look at the same expression sorted by the other letter.

**Problem 05.4.** Suppose that $K$ is a field and that $f$ and $g$ are relatively prime in $K[x]$. Show that $f - yg$ is irreducible in $K(y)[x]$.

Everything that statement uses:

- $K[x]$ — polynomials in $x$ with coefficients in the field $K$.
- $K(y)$ — the rational functions in $y$ over $K$, that is, quotients of two polynomials in $y$.
- $K(y)[x]$ — polynomials in $x$ whose coefficients are rational functions in $y$.
- $K[x][y]$ — polynomials in $y$ whose coefficients are polynomials in $x$; the same expressions, sorted by the other letter.
- relatively prime — the only common divisors of $f$ and $g$ in $K[x]$ are the nonzero constants.
- unit of $K(y)[x]$ — a nonzero element of $K(y)$.
- irreducible — not a unit, and in every factorisation into two factors one of them is a unit.
- greatest common divisor in $K[x]$ — the common divisor of highest degree, taken monic.

One rung before the proof, and it is the one still open. Take $K = \mathbb{Q}$, $f = x^3 + 1$ and $g = x + 2$, so
$$f - yg = x^3 + 1 - y(x+2).$$

Regard that as a polynomial in $y$ alone, whose coefficients are elements of $\mathbb{Q}[x]$. Write down those coefficients, and give their greatest common divisor in $\mathbb{Q}[x]$.
