---
kind: question
title: ch05-054-gauss-lands-where
---
Putting Gauss's lemma before the degree note is the right repair, but the lemma lands the factors in $K[x][y]$, not in $K[x]$. Your line says $ga,\ bg^{-1} \in K[x]$. Your very next line says $b = b_0 + b_1 y$, which has a $y$ in it. Both cannot hold.

The example from the last card shows it. There $a = \dfrac{x-y}{y^3}$, $b = y^3$, and the scaling constant is $c = y^3$. Then $ca = x - y$ and $c^{-1}b = 1$. The factor $x - y$ is not in $K[x]$.

The statement you are proving:

Let $K$ be a field and $f, g \in K[x]$ relatively prime. Show $f - yg$ is irreducible in $K(y)[x]$.

Everything it uses:

- relatively prime — the only common divisors of $f$ and $g$ in $K[x]$ are units.
- $K(y)$ — rational functions $p/q$ with $p, q \in K[y]$, $q \neq 0$.
- $K(y)[x]$ — polynomials in $x$ with coefficients in $K(y)$.
- $K[x][y]$ — polynomials in $x$ and $y$ over $K$, no denominators.
- $K[x]$ — polynomials in $x$ alone; degree $0$ in $y$.
- unit of $K(y)[x]$ — a nonzero element of $K(y)$.
- Gauss's lemma, over $R = K[y]$ — if $h \in K[y][x]$ and $h = ab$ with $a, b \in K(y)[x]$, there is a nonzero $c \in K(y)$ with $ca$ and $c^{-1}b$ both in $K[x][y]$.
- degree in $y$ — defined on $K[x][y]$, and it adds under multiplication there.

Rewrite your Gauss's-lemma sentence so it names the ring $ca$ and $c^{-1}b$ actually land in. Then say which step of your proof puts one of them in $K[x]$.
