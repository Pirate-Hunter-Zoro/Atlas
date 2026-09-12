---
kind: correct
title: $29$ fails, and it is the only one. Now say where it came from.
---

$fg = 18x^{4} + 12x^{3} + 29x^{2} + 9x + 9$, and $29$ is the single coefficient
outside $(3)$. Every step of that expansion is right.

Notice what did **not** happen. The leading coefficient is $18 \in (3)$, even
though neither $f$ nor $g$ is in $J[x]$. So the top of the product is no help —
you cannot prove part 1 by looking at leading coefficients. The failure happened
in the *middle*, at $x^{2}$, and part 1 is the business of predicting which
middle.

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
- The coefficient of $x^{n}$ in $fg$ is $\sum_{k+\ell = n} a_{k} b_{\ell}$ — every way of splitting $n$ into two indices.

Part 1 upside down: assume **neither** $f$ nor $g$ lies in $J[x]$, and produce
one coefficient of $fg$ that is not in $J$.

---

**Your move — one coefficient, written as a sum.** Same
$f = 3x^{2} + x + 3$ and $g = 6x^{2} + 2x + 3$ over $\mathbb{Z}$, $J = (3)$.

Write the coefficient $29$ out as the sum of the three products $a_{k} b_{\ell}$
that make it, keeping the products unmultiplied. Then tell me which of those
three terms is not in $(3)$, and for each of the other two, name the factor that
put it in $(3)$.

One term should be the odd one out.
