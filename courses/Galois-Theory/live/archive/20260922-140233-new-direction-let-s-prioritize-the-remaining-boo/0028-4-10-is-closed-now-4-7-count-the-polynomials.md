---
kind: lesson
title: 4-10-is-closed-now-4-7-count-the-polynomials
---
**4.10 is closed.** Finite degree forces $\gamma$ algebraic over $K$, and that
collides with $\gamma$ transcendental, which is the case you were standing in.
Every line of that proof is yours. It is now typeset in
`ch04-homework.tex` -- the chapter's write-up file -- with your tower argument
and that closing line, and page r21 is filed beside it.

One remark, in your favour. You passed through "$[K(\gamma):K]$ is finite" on
the way. That line is already absurd by itself: $\gamma$ transcendental over
$K$ means no non-zero polynomial in $K[x]$ kills it, so $1, \gamma, \gamma^2,
\dots$ are linearly independent over $K$ and $[K(\gamma):K]$ is infinite. You
could have stopped one step earlier than you did.

Wording only: a finite degree hands you a non-zero polynomial with $\gamma$ as
a root, and the minimal polynomial is what you extract from that one. Not the
other way round.

**Exercise 4.7.** Show that if $L : K$ is algebraic and $K$ is countable, then
$L$ is countable. Then show that there exist real numbers which are
transcendental over the rationals.

What it uses:

- Algebraic extension --- $L : K$ is algebraic if every element of $L$ is
  algebraic over $K$.
- Algebraic over $K$ --- a root of some non-zero polynomial in $K[x]$.
- Countable --- in bijection with a subset of $\mathbb{N}$; finite sets count
  as countable.
- A countable union of countable sets is countable.
- For each $n$, the set of $n$-tuples drawn from a countable set is countable.
- A non-zero polynomial of degree $n$ has at most $n$ roots in any field.
- $\mathbb{Q}$ is countable; $\mathbb{R}$ is not.

**Your move.** One piece, not the whole problem. Take $K$ countable. Say how
big the set of polynomials in $K[x]$ of degree exactly $n$ is, and then how big
all of $K[x]$ is, naming which fact above you used at each of the two steps.
