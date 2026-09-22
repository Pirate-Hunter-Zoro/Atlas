---
kind: lesson
title: both-facts-land-now-get-from-kx-to-l
---
**That is the step, and both facts are now named correctly.** Degree exactly $n$
is a finite product, all of $K[x]$ is a countable union of those, and a
countable union of countable sets is countable. The fact you called spare one
card ago is the one that finished the line.

Two small repairs, neither of which touches the argument. Say "polynomials with
coefficients in $K$" rather than "polynomials in $K$" --- the polynomials live
in $K[x]$, not in $K$. And the zero polynomial has no degree, so it is in none
of your $K_i[x]$; write $K[x]$ as $\{0\}$ together with that union, since adding
one element to a countable set leaves it countable.

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

**Your move.** $K[x]$ is countable and every element of $L$ is a root of
something in it. Fix one non-zero $f \in K[x]$, of degree $n$. How many elements
of $L$ can that single $f$ account for --- give the bound and name the fact
above that gives it.
