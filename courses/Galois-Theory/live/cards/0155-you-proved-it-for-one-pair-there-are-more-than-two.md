---
kind: wrong
title: "Everything you wrote about $(\\ell, m) = (j, i)$ is right. That is one pair, and there are more than two."
---

Read your own third line back: *if $\ell = j$, $m = i$*. You did not take an
arbitrary pair — you took **the** swapped pair, the one whose product is
$a_{j}b_{i}$, which is the summand you had already dealt with last turn. For
that pair your reasoning is correct: $(j,i) \neq (i,j)$ forces $i \neq j$, so
either $i < j$ and $b_{m} = b_{i} \in J$, or $j < i$ and $a_{\ell} = a_{j} \in
J$; absorption finishes it either way.

But the coefficient of $x^{i+j}$ is not a sum of two terms. If $i = 2$ and
$j = 3$, the splittings of $5$ are $(0,5), (1,4), (2,3), (3,2), (4,1), (5,0)$ —
six of them, and your argument has covered exactly one of the five that are not
$(i,j)$. The dichotomy you want cannot be got by naming a pair. It has to come
out of the arithmetic of $\ell + m = i + j$ itself.

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

---

**Your move — tag the five.** Fix $i = 2$ and $j = 3$. So $a_{0}, a_{1} \in J$
and $a_{2} \notin J$; $b_{0}, b_{1}, b_{2} \in J$ and $b_{3} \notin J$. Here are
the splittings of $5$ other than $(2,3)$:

$$(0,5) \qquad (1,4) \qquad (3,2) \qquad (4,1) \qquad (5,0)$$

For each one, name the **single** coefficient that leastness puts inside $J$ —
either $a_{\ell}$ or $b_{m}$, and say which of the two it is.

Five short lines. Nothing to prove yet; I want to see which side each pair falls
on.
