---
kind: question
title: ch05-054-clear-denominators
---
The last line is right and the contradiction is closed. $a \mid f$ and $a \mid g$ with $f, g$ coprime forces $a$ to be a unit of $K[x]$, i.e. a nonzero constant, and a nonzero constant is a unit of $K(y)[x]$ as well. The hypothesis now reads "not a unit" and $K[x]$ has replaced $\mathbb{Q}[x]$.

One earlier line is not yet earned. Line 3 is where it happens: you are handed $f - yg = ab$ with $a, b \in K(y)[x]$, and two lines later you are writing $b = b_0 + b_1 y$ with $a, b_0, b_1 \in K[x]$. The coefficients you were given are rational functions of $y$. Nothing so far says they are polynomials, so "in $K[x][y]$, $ab$ must be degree $1$" is about a factorisation you have not been given.

The repair is rescaling, and here is a case of it. In $\mathbb{Q}(y)[x]$,
$$x^2 + x = \left(\tfrac{1}{y}\,x\right)\left(y x + y\right).$$
That is a genuine factorisation in $\mathbb{Q}(y)[x]$, and the first factor has a $y$ in a denominator, so it is not in $\mathbb{Q}[x][y]$.

Everything it uses:

- $K(y)$ — the field of rational functions in $y$ over $K$, i.e. ratios $p/q$ with $p, q \in K[y]$, $q \neq 0$.
- $K(y)[x]$ — polynomials in $x$ whose coefficients are elements of $K(y)$.
- $K[x][y]$ — polynomials in $y$ whose coefficients are elements of $K[x]$; the same ring as $K[x,y]$, coefficients in $K$ only, no denominators.
- unit of $K(y)[x]$ — a nonzero element of $K(y)$, i.e. anything of degree $0$ in $x$. Note this is a much larger set than the units of $K[x][y]$, which are just $K^\times$.
- $\mathbb{Q}(y)^\times$ — the nonzero elements of $\mathbb{Q}(y)$, every one of which is invertible.

So: find one nonzero $c \in \mathbb{Q}(y)$ for which $c \cdot \tfrac{1}{y}x$ and $c^{-1} \cdot (yx + y)$ both lie in $\mathbb{Q}[x][y]$, and say whether either of the two rescaled factors has turned into a unit.
