---
kind: correct
title: "$b_{i} \\in J$, and *least* is finally doing work. Now every other summand."
---

That line is right, and it is the first line in this proof that actually spends
the word *least*: $j$ is the least index with $b_{j} \notin J$, so every earlier
index has its coefficient in $J$, and $i < j$ is an earlier index. Hence
$b_{i} \in J$, and absorption gives $a_{j}b_{i} \in J$. You asked *what about
$a_{j}b_{i}$* — that is the answer: it is inside $J$, so it does no harm.

One remark on the **WLOG**. It does survive here, but not for the reason you
probably meant. The two cases are *not* the same line: $j > i$ uses leastness of
$j$ and concludes from $b_{i} \in J$, while $j < i$ uses leastness of $i$ and
concludes from $a_{j} \in J$. The symmetry that rescues the WLOG is the swap of
$a$ with $b$ *together with* $i$ with $j$ — under which $a_{j}b_{i}$ becomes
$b_{i}a_{j}$, the same element only because $R$ is commutative. Rather than have
you write that out, the next step swallows both cases whole.

Because $a_{j}b_{i}$ was never the point. The coefficient of $x^{i+j}$ has one
summand for *every* splitting $\ell + m = i + j$, not just two, and the middle
sentence your proof is missing has to handle all of them at once.

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

**Your move — every summand but one.** Keep $i$ least with $a_{i} \notin J$ and
$j$ least with $b_{j} \notin J$. Take any pair $\ell, m$ of indices with
$\ell + m = i + j$ and $(\ell, m) \neq (i, j)$.

Show that $a_{\ell}b_{m} \in J$.

Two steps and no cleverness. First: from $\ell + m = i + j$ and $\ell \neq i$,
argue that either $\ell < i$ or $m < j$ — say which one each way round forces.
Then in each of those two cases, name the coefficient that leastness puts inside
$J$, and finish with absorption.
