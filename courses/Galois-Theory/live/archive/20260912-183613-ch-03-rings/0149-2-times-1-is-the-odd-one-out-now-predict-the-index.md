---
kind: correct
title: $2 \cdot 1$ is the odd one out. Now predict the index without multiplying.
---

$29 = 2 \cdot 1 + 3 \cdot 6 + 3 \cdot 3$, and $2 \cdot 1$ is the term outside
$(3)$. Right, and it is right for the reason that generalises: $2 = b_{1}$ and
$1 = a_{1}$, and neither of those is in $(3)$.

One thing you left unnamed, so I will name it. In $3 \cdot 6 = a_{0}b_{2}$ the
factor doing the work is $a_{0} = 3$ — a coefficient of $f$. In
$3 \cdot 3 = a_{2}b_{0}$ it is $b_{0} = 3$ — a coefficient of $g$. Different
sides. ($6$ happens to be in $(3)$ too, but that is luck, and the proof must not
lean on it.)

Now look at *why* those two are the ones that got caught. Index $1$ is the
**least** index at which $f$ escapes $(3)$: $a_{0} = 3$ is in, $a_{1} = 1$ is
out. Same for $g$: $b_{0} = 3$ is in, $b_{1} = 2$ is out. The three ways to
split $2$ are $0+2$, $1+1$, $2+0$ — and the first drops $f$'s index below $1$,
the last drops $g$'s index below $1$. Only the middle one keeps both at or above
the threshold.

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

---

**Your move — a second pair, and no multiplying out this time.** Still over
$\mathbb{Z}$ with $J = (3)$, take

$$f = x^{3} + 3x^{2} + 6x + 9, \qquad g = 2x + 3.$$

Neither is in $(3)[x]$. Find the least index $i$ with $a_{i} \notin (3)$, and the
least index $j$ with $b_{j} \notin (3)$. Then tell me which single coefficient of
$fg$ you expect to be outside $(3)$ — name the power of $x$, and write that
coefficient as its sum of products, unmultiplied.

The thresholds are not both $1$ this time. That is the point of the example.
