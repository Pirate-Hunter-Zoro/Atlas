---
kind: wrong
title: $x^{4}$ is right. But $a_{0} = 9$, and $9 \in (3)$.
---

$2x^{4}$ is the escaping term. That is the right answer, and it was not luck.

The indices are not $0$ and $0$, though. Read them off $f = x^{3} + 3x^{2} + 6x + 9$:

| | $a_{0}$ | $a_{1}$ | $a_{2}$ | $a_{3}$ |
|---|---|---|---|---|
| value | $9$ | $6$ | $3$ | $1$ |
| in $(3)$? | yes | yes | yes | **no** |

So the least $i$ with $a_{i} \notin (3)$ is $i = 3$. For $g = 2x + 3$: $b_{0} = 3$
is in, $b_{1} = 2$ is out, so $j = 1$. And $3 + 1 = 4$ — the $x^{4}$ you named.

You counted from the wrong end: position on the page, not power of $x$. $f$ is
written leading term first, so the coefficient you called index $0$ was really
$a_{3}$, and for $g$ it was $b_{1}$. That is why the answer still came out right.
The *greatest*-index argument works too, by the exact mirror of the reasoning —
keep it in your pocket, it is a real proof. But in this exercise $a_{i}$ means
the coefficient of $x^{i}$, and the bottom end is the one you will write up.

---

## Exercise 3.26

Suppose $J$ is a proper prime ideal in an **integral domain** $R$.

1. Show that $J[x]$ is prime in $R[x]$.
2. Show that $J[x]$ is **not** a maximal proper ideal in $R[x]$.

### Everything the statement uses

- $R$: a commutative ring with identity $1$. An **integral domain**: no zero divisors — $ab = 0$ forces $a = 0$ or $b = 0$.
- $R[x]$: polynomials in $x$ with coefficients in $R$. A polynomial $f$ is its list of coefficients $a_{0}, a_{1}, a_{2}, \dots$, all but finitely many zero; $a_{i}$ is the coefficient of $x^{i}$.
- *Ideal* $I$: closed under addition, and **absorbing** — $a \in I$, $r \in R$ $\Rightarrow$ $ra \in I$.
- *Proper*: $I \neq R$; equivalently $1 \notin I$.
- *Prime ideal* $J$: proper, and $ab \in J$ $\Rightarrow$ $a \in J$ or $b \in J$.
- *Maximal proper ideal* $M$: proper, and no ideal sits strictly between $M$ and $R$.
- $J[x]$: the polynomials **every one of whose coefficients lies in $J$**.
- The coefficient of $x^{n}$ in $fg$ is $\sum_{k + \ell = n} a_{k}b_{\ell}$ — every way of splitting $n$ into two indices.

Part 1 upside down: assume **neither** $f$ nor $g$ lies in $J[x]$, and produce
one coefficient of $fg$ that is not in $J$.

Where we are: $i = 3$ and $j = 1$ for this pair, so $x^{4}$ is the coefficient to
look at. Its full expansion, over every splitting $4 = k + \ell$, is

$$a_{0}b_{4} \;+\; a_{1}b_{3} \;+\; a_{2}b_{2} \;+\; a_{3}b_{1} \;+\; a_{4}b_{0}.$$

---

**Your move — four terms, one factor each.** Leave $a_{3}b_{1}$ alone; that is
the one that escapes. For each of the other four terms, name the single factor
that is *forced* into $(3)$, and say which of these two rules forced it:

- $k < 3$, so $a_{k} \in (3)$ — because $3$ is the least index where $f$ escapes;
- $\ell < 1$, so $b_{\ell} \in (3)$ — because $1$ is the least index where $g$ escapes.

Four answers, one line each. Some of those coefficients happen to be $0$ — ignore
that. I want the reason that would still hold if they weren't.
