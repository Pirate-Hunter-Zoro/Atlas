---
kind: question
title: ch05-054-degree-zero-factor
---
Degrees $1$ and $0$ is right, and it is right for the reason you gave: degrees in $y$ add, the product has degree $1$, so one factor has degree $1$ and the other degree $0$.

One line above that needs pulling out. You wrote that $a,b \in K[x][y]$ because $f-yg \in K[x][y]$, starting from a factorisation in $K(y)[x]$. That is not free — it is Gauss's lemma, and it is the whole second half of this problem. So set it aside and suppose the factorisation happens in $K[x][y]$ from the start; the passage back to $K(y)[x]$ comes after.

Now the degree-$0$ factor. Say $a$ has degree $0$ in $y$, so $a \in K[x]$, and write the other as $b = b_1 y + b_0$ with $b_1, b_0 \in K[x]$. Then
$$ab = (ab_1)\,y + ab_0,$$
and comparing that with $f - yg = f + (-g)y$ gives $ab_1 = -g$ and $ab_0 = f$.

So $a$ divides both $f$ and $-g$ in $K[x]$. That is the rung: say what $a$ must therefore be, and say why that kills the assumption you started from.

Everything it uses:

- $K[x][y]$ — polynomials in $y$ with coefficients in $K[x]$.
- $f - yg$ in that ring — degree $1$ in $y$, with $y^1$ coefficient $-g$ and $y^0$ coefficient $f$.
- relatively prime — the only common divisors of $f$ and $g$ in $K[x]$ are the nonzero constants of $K$.
- unit of $K[x][y]$ — a nonzero constant of $K$, nothing else.
- your standing assumption — $f - yg = ab$ with neither $a$ nor $b$ a unit.

So: $a \in K[x]$ divides both $f$ and $-g$. What must $a$ be, and why does that contradict $a$ not being a unit?
