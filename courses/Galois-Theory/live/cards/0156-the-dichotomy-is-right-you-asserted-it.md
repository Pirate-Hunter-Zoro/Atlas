---
kind: note
title: "That is the general dichotomy, and absorption finishes it. You asserted the dichotomy rather than proving it."
---

You dropped the pair-naming and went at $\ell + m = i + j$ itself, which is
exactly the right move. Everything after the dichotomy is correct and general:
$\ell < i$ puts $a_{\ell} \in J$ by leastness, $m < j$ puts $b_{m} \in J$ by
leastness, and absorption sends $a_{\ell}b_{m}$ into $J$ either way. That is the
whole of the "every other summand" step, and it now covers all five splittings
at once, not one.

The unearned clause is the dichotomy itself:

> If $\ell + m = i + j$, then either $\ell < i$ or $m < j$.

You wrote it as an observation. It is true, but it is the one arithmetic fact
the proof rests on, and nothing on the page establishes it. Note also that it is
**false** without the standing hypothesis $(\ell, m) \neq (i, j)$ — the pair
$(i, j)$ itself satisfies $\ell + m = i + j$ and neither inequality. So that
hypothesis has to appear inside the argument, not just above it.

(*Least* is about the index, not the size of the coefficient — $a_{i} \notin J$
with every earlier $a_{\ell} \in J$. Your proof uses it correctly; the wording
is a pen fix and I will make it in the write-up.)

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

**Your move — earn the dichotomy.** Prove the contrapositive instead. Take
non-negative integers $\ell, m, i, j$ with $\ell + m = i + j$, and **suppose
both inequalities fail**: $\ell \geq i$ and $m \geq j$.

Add those two inequalities together, compare what you get with $\ell + m = i +
j$, and finish the sentence: therefore $\ell = i$ and $m = j$, i.e. $(\ell, m) =
(i, j)$ — which the hypothesis forbids.

Two or three lines. I want to see where the "and" in $\ell \geq i$ **and**
$m \geq j$ collapses to equality.
