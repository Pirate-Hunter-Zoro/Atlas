---
kind: correct
title: "Primality and the subtraction trick both land. Now name the statement you actually proved."
---

Line 1 is exactly right, and it is the only place in 3.26 where *prime* is used:
$a_{i} \notin J$ and $b_{j} \notin J$, so $a_{i}b_{j} \notin J$ — because a prime
ideal is one whose complement is closed under multiplication.

Line 2 is better than what I asked for. I said "push closure the right way
round"; you pushed it by contradiction instead, and the contradiction is clean:
if the whole coefficient $\sum_{\ell+m=i+j} a_{\ell}b_{m}$ were in $J$, then
subtracting the granted part — every summand with $(\ell,m) \neq (i,j)$ — leaves
$a_{i}b_{j} \in J$, which line 1 forbids.

One repair, and it is mine to make, not yours to redo: that step subtracts, and
you cited closure under addition. An ideal is closed under subtraction too, via
absorption — $-c = (-1)c \in J$. I will write it that way.

So the coefficient of $x^{i+j}$ in $ab$ is not in $J$. Hence $ab$ has a
coefficient outside $J$.

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
- $J[x]$: the polynomials **every one of whose coefficients lies in $J$**. So $a \notin J[x]$ means *some* coefficient of $a$ is outside $J$.
- The coefficient of $x^{n}$ in $ab$ is $\sum_{\ell + m = n} a_{\ell}b_{m}$.
- *Least escaping index* $i$: $a_{i} \notin J$, and $a_{\ell} \in J$ for every $\ell < i$. Same for $j$ and $b$.

---

**Your move — one line, and it is bookkeeping, not mathematics.** Your page
starts at "$a \notin J[x]$ and $b \notin J[x]$" and ends at "$ab \notin J[x]$".
The definition of *prime* above is stated the other way about: it starts at
$ab \in J[x]$. Write the sentence that connects the two — name the logical
relation between the implication you proved and the implication the definition
demands, and say why proving one gives you the other.
