---
kind: correct
title: (a) and (c), and nothing else. Now the prime half of 3.26.
---

Both of them, and both for the same reason: every coefficient is a multiple of
$3$. In (a) those are $3, 6, -9$; in (c) they are $6$ and $12$, and the four
missing coefficients in between are $0$, which is in $(3)$ like everything else.

(b) fails on one coefficient, the $1$ in front of $x^{2}$. (d) is $x$, which
fails on the $1$ in front of $x$ — a polynomial can be as small as you like and
still miss $J[x]$. Hold onto (d); part 2 is built out of it.

---

## Exercise 3.26

Suppose $J$ is a proper prime ideal in an **integral domain** $R$.

1. Show that $J[x]$ is prime in $R[x]$.
2. Show that $J[x]$ is **not** a maximal proper ideal in $R[x]$.

### Everything the statement uses

- $R$: a commutative ring with identity $1$. An **integral domain**: no zero divisors — $ab = 0$ forces $a = 0$ or $b = 0$.
- $R[x]$: polynomials in $x$ with coefficients in $R$. A polynomial $f$ is its list of coefficients $a_{0}, a_{1}, a_{2}, \dots$, all but finitely many zero.
- *Ideal* $I$: closed under addition, and **absorbing** — $a \in I$, $r \in R$ $\Rightarrow$ $ra \in I$.
- *Proper*: $I \neq R$; equivalently $1 \notin I$.
- *Prime ideal* $J$: proper, and $ab \in J$ $\Rightarrow$ $a \in J$ or $b \in J$.
- *Maximal proper ideal* $M$: proper, and no ideal sits strictly between $M$ and $R$.
- $J[x]$: the polynomials **every one of whose coefficients lies in $J$** — the check you just did.
- $\deg(fg) = \deg f + \deg g$ in a domain (your card 0089 territory).

Part 1 unpacked: take $f, g \in R[x]$ with $fg \in J[x]$, and show $f \in J[x]$
or $g \in J[x]$. It is easier upside down — if **neither** $f$ nor $g$ is in
$J[x]$, produce a coefficient of $fg$ that is not in $J$.

---

**Your move — one multiplication.** Back in $\mathbb{Z}$ with $J = (3)$. Take

$$f = 3x^{2} + x + 3, \qquad g = 6x^{2} + 2x + 3.$$

Neither is in $J[x]$: $f$ has that $1$, $g$ has that $2$.

Multiply them out and tell me, coefficient by coefficient, which coefficients of
$fg$ lie in $(3)$ and which do not.

You should get five coefficients, and exactly one of them should fail.
