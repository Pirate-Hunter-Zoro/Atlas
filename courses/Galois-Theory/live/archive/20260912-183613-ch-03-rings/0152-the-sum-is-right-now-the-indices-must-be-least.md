---
kind: wrong
title: "The coefficient is right now. $a_{i}b_{j} \\notin J$ still does not put the *sum* outside $J$."
---

The misreading is fixed. You wrote the coefficient of $x^{i+j}$ in $ab$ as the
whole sum $\sum_{\ell+m=i+j} a_{\ell}b_{m}$, not as the single term
$a_{i}b_{j}x^{i+j}$. That was the point of the last card and it has landed.

Two pen slips I will repair in the write-up — no redo:

- The exponent is $x^{i+j}$. You wrote $x^{j+k}$, and $k$ is never defined.
- The last line should read $\sum_{\ell+m=i+j} a_{\ell}b_{m} \notin J$. You wrote
  $\in$, and then concluded $ab \notin J[x]$ from it — which is what $\notin$
  gives you, not $\in$.

## The clause that is still missing

Your proof goes: $a_{i}b_{j} \notin J$, **and so**
$\sum_{\ell+m=i+j} a_{\ell}b_{m} \notin J$.

Nothing sits under that arrow, and the arrow is false as written. Here it is
failing — the instance from the last card, worked out:

Over $\mathbb{Z}$ with $J = (3)$, take $f = 1 + x$ and $g = 2 + x$. The
coefficients are $a_{0} = 1$, $a_{1} = 1$, $b_{0} = 2$, $b_{1} = 1$, and not one
of them is in $(3)$. Your $\exists$ lets you pick $i = 1$ and $j = 0$. Then
$a_{1}b_{0} = 2 \notin (3)$, your arrow fires, and it announces that the
coefficient of $x$ in $fg$ is outside $(3)$. But that coefficient is

$$a_{0}b_{1} + a_{1}b_{0} \;=\; 1 + 2 \;=\; 3,$$

and $3 \in (3)$. One summand escaped; the sum came straight back in.

So the other summands are the entire problem. What you need is a choice of $i$
and $j$ for which **every other summand of that sum lies in $J$** — then the
sum is (one element outside $J$) plus (elements of $J$), and *that* is outside
$J$. Bare existence will not do it. **Least** will: let $i$ be the smallest
index with $a_{i} \notin J$, and $j$ the smallest with $b_{j} \notin J$. In the
$f = x^{3}+3x^{2}+6x+9$, $g = 2x+3$ instance, $i = 3$ and $j = 1$ were the least
such indices, and that is exactly why the rest of the sum vanished into $(3)$.

---

## Exercise 3.26

Suppose $J$ is a proper prime ideal in an **integral domain** $R$.

1. Show that $J[x]$ is prime in $R[x]$.
2. Show that $J[x]$ is **not** a maximal proper ideal in $R[x]$.

### Everything the statement uses

- $R$: a commutative ring with identity $1$. An **integral domain**: no zero divisors — $ab = 0$ forces $a = 0$ or $b = 0$.
- $R[x]$: polynomials in $x$ with coefficients in $R$. A polynomial $a$ is its list of coefficients $a_{0}, a_{1}, a_{2}, \dots$, all but finitely many zero; $a_{i}$ is the coefficient of $x^{i}$.
- *Ideal* $I$: closed under addition, and **absorbing** — $c \in I$, $r \in R$ $\Rightarrow$ $rc \in I$.
- *Proper*: $I \neq R$; equivalently $1 \notin I$.
- *Prime ideal* $J$: proper, and $cd \in J$ $\Rightarrow$ $c \in J$ or $d \in J$.
- *Maximal proper ideal* $M$: proper, and no ideal sits strictly between $M$ and $R$.
- $J[x]$: the polynomials **every one of whose coefficients lies in $J$**.
- The coefficient of $x^{n}$ in $ab$ is $\sum_{\ell + m = n} a_{\ell}b_{m}$ — every way of splitting $n$ into two indices.
- *Least escaping index* $i$: $a_{i} \notin J$, and $a_{\ell} \in J$ for every $\ell < i$. Same for $j$ and $b$.
- $(3)$ in $\mathbb{Z}$: the multiples of $3$. It is a prime ideal.

---

**Your move — one summand.** Fix $i$ as the least index with $a_{i} \notin J$
and $j$ as the least with $b_{j} \notin J$. Now take any *other* summand of the
coefficient of $x^{i+j}$: indices $\ell, m$ with $\ell + m = i + j$ and
$\ell \neq i$.

Show that $a_{\ell}b_{m} \in J$.

Start by comparing $\ell$ with $i$ — there are two cases, and they need
different halves of what you have. One line each.
