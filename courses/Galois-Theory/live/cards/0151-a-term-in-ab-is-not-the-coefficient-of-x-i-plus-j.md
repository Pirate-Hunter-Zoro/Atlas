---
kind: wrong
title: "\"a term in $ab$\" is not \"the coefficient of $x^{i+j}$\"."
---

You skipped the four-term drill and went straight at the general proof. The
architecture is right, and two of its moves are exactly the ones I wanted:

- **Upside down.** Assume $a \notin J[x]$ and $b \notin J[x]$, and hunt for a
  coefficient of $ab$ outside $J$. That is the contrapositive, and it is the
  only sane way in.
- **$a_{i}b_{j} \notin J$ because $J$ is prime.** Correct, and correctly
  reasoned: if $a_{i}b_{j}$ *were* in $J$, primality would put $a_{i}$ or
  $b_{j}$ in $J$, and neither is.

One clause is missing, and it is the clause the whole $x^{4}$ exercise existed
to teach.

You wrote: *$a_{i}b_{j}x^{i+j}$ is a term in $ab$.* True. But a term is not a
coefficient. The coefficient of $x^{i+j}$ in $ab$ is the **whole sum**

$$\sum_{k+\ell \,=\, i+j} a_{k}b_{\ell},$$

and $a_{i}b_{j}$ is only one summand of it. The other summands can drag the
total back into $J$. So "$a_{i}b_{j} \notin J$" does not by itself give you a
coefficient of $ab$ outside $J$.

And you chose $i$ and $j$ by *existence* — "$\exists$ coefficients $a_{i}, b_{j}$
such that..." — any escaping indices at all. That is the second half of the same
hole. In the $f = x^{3} + 3x^{2} + 6x + 9$, $g = 2x + 3$ instance, $i = 3$ and
$j = 1$ were not just *some* escaping indices. They were the **least** ones, and
that is what emptied the rest of the sum.

Here is the gap made visible. Take $R = \mathbb{Z}$, $J = (3)$, and

$$f = 1 + x, \qquad g = 2 + x.$$

Neither is in $(3)[x]$. Pick the escaping indices $i = 1$ (since $a_{1} = 1$)
and $j = 0$ (since $b_{0} = 2$). Then $a_{1}b_{0} = 2 \notin (3)$, so your
sentence fires — and it points at $x^{1+0} = x$.

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
- $(3)$ in $\mathbb{Z}$: the multiples of $3$. It is a prime ideal.

---

**Your move — one multiplication.** With $f = 1 + x$ and $g = 2 + x$ over
$\mathbb{Z}$: work out the coefficient of $x^{1}$ in $fg$. Write out both
splittings of $1$, add them, and tell me whether that number lies in $(3)$.

One number, and a yes or no.
