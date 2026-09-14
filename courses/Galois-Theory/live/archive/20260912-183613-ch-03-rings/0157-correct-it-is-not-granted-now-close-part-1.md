---
kind: note
title: "No, it is not the point. The dichotomy is granted — now close part 1."
---

You are right. One line of index arithmetic is not what 3.26 is about, and I am
not going to make you write it. Granted, in full, and we never look at it again:

> $\ell \geq i$ and $m \geq j$ add to $\ell + m \geq i + j$, and that is an
> equality only if both of them are. Since $\ell + m = i + j$, both are, so
> $(\ell, m) = (i, j)$ — excluded by hypothesis. Hence $\ell < i$ or $m < j$.

What I was after was smaller than a theorem: the hypothesis
$(\ell, m) \neq (i, j)$ sat at the top of your page and never appeared in the
argument below it. That is the same clause you keep leaving on the table, so I
asked for the two lines that spend it. Two lines is all it was worth. Move on.

**What is now proved and stays proved.** Take $a, b \notin J[x]$, let $i$ be the
least index with $a_{i} \notin J$ and $j$ the least with $b_{j} \notin J$. In
the coefficient of $x^{i+j}$ in $ab$, namely $\sum_{\ell + m = i + j}
a_{\ell}b_{m}$, every summand other than $a_{i}b_{j}$ lies in $J$: the
dichotomy sends $\ell < i$ or $m < j$, leastness puts that factor in $J$, and
absorption swallows the product.

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
- The coefficient of $x^{n}$ in $ab$ is $\sum_{\ell + m = n} a_{\ell}b_{m}$.
- *Least escaping index* $i$: $a_{i} \notin J$, and $a_{\ell} \in J$ for every $\ell < i$. Same for $j$ and $b$.

---

**Your move — finish part 1.** Three lines, in this order:

1. One line putting $a_{i}b_{j}$ **outside** $J$. You know $a_{i} \notin J$ and
   $b_{j} \notin J$; name the property of $J$ that turns that into
   $a_{i}b_{j} \notin J$. This is the only place in the whole proof where $J$
   being *prime* is used, so say it by name.
2. One line from there to: the coefficient of $x^{i+j}$ in $ab$ is not in $J$.
   Everything else in that sum is in $J$, and $J$ is closed under addition —
   push that the right way round.
3. One line saying what you have therefore proved about $J[x]$, and why it is
   the prime condition rather than something weaker. You started from
   $a \notin J[x]$ and $b \notin J[x]$; the definition above is stated the
   other way about.
