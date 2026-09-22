---
kind: lesson
title: right-answer-wrong-fact-it-is-a-product-not-a-union
---
**Countable is right; the fact you named is the wrong one.** A polynomial of
degree exactly $n$ is a list of $n+1$ coefficients $k_0, k_1, \dots, k_n$ drawn
from $K$, with $k_n \neq 0$. A list is a product, not a union. So the fact that
carries this step is: for each $n$, the set of $n$-tuples drawn from a countable
set is countable.

Your $\mathbb{N}$ should be $K$. The coefficients live in $K$, and $K$ is the
set you are told is countable. Nothing here is indexed by $\mathbb{N}$ --- the
index $i$ only runs from $0$ to $n$, which is what makes the tuple finite.

The countable union you waved away is not spare. One line from now it is the
only fact that works.

**Exercise 4.7.** Show that if $L : K$ is algebraic and $K$ is countable, then
$L$ is countable. Then show that there exist real numbers which are
transcendental over the rationals.

What it uses:

- Algebraic extension --- $L : K$ is algebraic if every element of $L$ is
  algebraic over $K$.
- Algebraic over $K$ --- a root of some non-zero polynomial in $K[x]$.
- Countable --- in bijection with a subset of $\mathbb{N}$; finite sets count as
  countable.
- A countable union of countable sets is countable.
- For each $n$, the set of $n$-tuples drawn from a countable set is countable.
- A non-zero polynomial of degree $n$ has at most $n$ roots in any field.
- $\mathbb{Q}$ is countable; $\mathbb{R}$ is not.

**Your move.** You have proved: for each fixed $n$, the polynomials in $K[x]$ of
degree exactly $n$ form a countable set. Now say how big all of $K[x]$ is, and
name which fact above takes you from the one to the other.
