---
kind: question
title: ch05-054-degree-one-in-y
---
Correct, both of them. Sorted by $y$, the polynomial $x^3+1-y(x+2)$ has $y^0$ coefficient $x^3+1$ and $y^1$ coefficient $-(x+2)$, and their greatest common divisor in $\mathbb{Q}[x]$ is $1$.

The word "clearly" is standing in for one line, so here it is: $x+2$ is irreducible, so the only common divisor to rule out is $x+2$ itself, and $(-2)^3+1=-7\neq 0$ says $x+2$ does not divide $x^3+1$.

Nothing in that used $\mathbb{Q}$, or those two particular polynomials, beyond coprimality. In general $f-yg = f + (-g)\,y$, a polynomial in $y$ of degree $1$ whose two coefficients are $f$ and $-g$ in $K[x]$, and $\gcd(f,-g)=1$ is exactly the hypothesis. That is the whole input to the proof.

**Problem 05.4.** $K$ is a field and $f, g \in K[x]$ are relatively prime. Show that $f-yg$ is irreducible in $K(y)[x]$.

The next rung is one step, and it happens in $K[x][y]$, not in $K(y)[x]$. Suppose $f - yg = ab$ with $a, b \in K[x][y]$, neither one a unit. Say what the degrees of $a$ and $b$ in $y$ must be, and then say what the degree-$0$ factor has to be.

Everything that rung uses:

- $K[x][y]$ — polynomials in $y$ whose coefficients are polynomials in $x$ over $K$.
- degree in $y$ — the highest power of $y$ appearing, coefficients in $K[x]$ ignored.
- degrees in $y$ add across a product, because $K[x]$ is an integral domain.
- unit of $K[x][y]$ — a nonzero constant in $K$, nothing more.
- a factor of degree $0$ in $y$ — an element of $K[x]$, which therefore divides every $y$-coefficient of the product.
- relatively prime — the only common divisors of $f$ and $g$ in $K[x]$ are the nonzero constants.

So: with $f - yg = ab$ in $K[x][y]$ and neither factor a unit, what are the degrees of $a$ and $b$ in $y$, and what does the degree-$0$ one have to be?
