---
kind: question
title: ch05-054-degree-needs-polynomials
---
Your note does not take care of it, because "degree in $y$" only works for polynomials in $y$. Your note says $ab$ has degree $1$ in $K[x][y]$. But $a$ and $b$ are not yet known to be in $K[x][y]$. So you cannot split that $1$ as $0 + 1$.

Here is a factorisation where the split fails. Take $f = x$ and $g = 1$, which are relatively prime. Then

$$f - yg = x - y = \underbrace{\frac{x - y}{y^3}}_{a} \cdot \underbrace{y^3}_{b}.$$

Both $a$ and $b$ lie in $K(y)[x]$. Neither has degree $0$ or $1$ in $y$: $b$ has degree $3$, and $a$ is not a polynomial in $y$ at all. So the WLOG line "$a$ has degree $0$, $b = b_0 + b_1 y$" cannot be read off from $ab$ having degree $1$.

Gauss's lemma is what repairs this. It rescales $a, b$ into $K[x][y]$ first. After that, your note is true and the rest of your proof runs.

Everything it uses:

- $K(y)$ — rational functions $p/q$ with $p, q \in K[y]$, $q \neq 0$.
- $K(y)[x]$ — polynomials in $x$ with coefficients in $K(y)$.
- $K[x][y]$ — polynomials in $x$ and $y$ over $K$, no denominators.
- unit of $K(y)[x]$ — a nonzero element of $K(y)$, that is, degree $0$ in $x$.
- Gauss's lemma, over $R = K[y]$ — if $h \in K[y][x]$ and $h = ab$ with $a, b \in K(y)[x]$, there is a nonzero $c \in K(y)$ with $ca$ and $c^{-1}b$ both in $K[x][y]$.
- degree in $y$ — defined for elements of $K[x][y]$, and it adds under multiplication there.

For $a = \dfrac{x - y}{y^3}$ and $b = y^3$: find the $c \in K(y)$ that puts $ca$ and $c^{-1}b$ in $K[x][y]$, and say which of the two new factors has degree $0$ in $y$.
