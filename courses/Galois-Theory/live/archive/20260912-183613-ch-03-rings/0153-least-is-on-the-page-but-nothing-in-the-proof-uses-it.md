---
kind: question
title: "The word *least* is on the page. The sentence that uses it is not."
---

Fair question, and the answer is short: nothing is wrong with the pair
$a_{j}b_{i}$, and nothing is wrong with choosing $i$ and $j$ least. What is
wrong is that your proof does not *say* anything about the other summands.

Read your own two lines back:

> $a_{i}b_{j} \notin J$ since $J$ is a prime ideal of $R$. And so
> $\sum_{\ell+m=i+j} a_{\ell}b_{m} \notin J$.

Between those there is still nothing but the word *so*. You inserted *least*
into the line above, which is the right fix — but the fix has to be **used**,
and a proof only uses a hypothesis where it mentions it. As written, that arrow
is the same arrow the last card broke with $f = 1+x$, $g = 2+x$: it argues from
one summand being outside $J$ to the whole sum being outside $J$, and that
implication is false. Making $i$ and $j$ least does not repair the arrow. It
supplies the *missing premise* — that every other summand is in $J$ — and that
premise has to appear on the page before the arrow can fire.

So: you are not there because the middle sentence is not written yet. It is one
sentence, and you are being asked for the first half of it now.

On the pen slip in the middle line — the exponent should be $x^{i+j}$, and you
still have $x^{j+k}$ with $k$ undefined. I will repair that in the write-up. The
final $\notin$ is right now.

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

**Your move — the pair you named.** Let $i$ be the least index with
$a_{i} \notin J$ and $j$ the least with $b_{j} \notin J$. You pointed at the
summand $a_{j}b_{i}$: it does sit in the coefficient of $x^{i+j}$, since
$j + i = i + j$.

Show that $a_{j}b_{i} \in J$.

Take $i \neq j$, so that this really is a different summand from $a_{i}b_{j}$.
Then there are two cases, $j < i$ and $j > i$, and each needs a different one of
your two leastness hypotheses. One line each.
