---
kind: lesson
title: the-union-lands-except-f-equals-zero-now-the-real-half
---
**The union is right and the first half of 4.7 is yours.** $L = \bigcup R_f$,
indexed by $K[x]$, a countable union of finite sets, hence countable. That is
the proof.

One repair, and it is the same one that bit you on 4.8. Take $f = 0$. Every
$\ell \in L$ satisfies $0(\ell) = 0$, so $R_0 = L$, which is not finite. Index
the union over non-zero $f$ instead. Then $R_f$ is finite because a non-zero
polynomial of degree $n$ has at most $n$ roots, and the union still covers $L$
because $L : K$ algebraic gives every $\ell$ a non-zero $f$ killing it. That
hypothesis is where your line "$L = \bigcup R_f$" actually comes from.

**Exercise 4.7, second half.** Show that there exist real numbers which are
transcendental over $\mathbb{Q}$.

What it uses:

- Transcendental over $K$ --- an element that is *not* algebraic over $K$, i.e.
  a root of no non-zero polynomial in $K[x]$.
- Algebraic over $K$ --- a root of some non-zero polynomial in $K[x]$.
- Countable --- in bijection with a subset of $\mathbb{N}$; finite counts.
- A countable union of countable sets is countable.
- A non-zero polynomial of degree $n$ has at most $n$ roots in any field.
- $\mathbb{Q}[x]$ is countable --- your own result.
- $\mathbb{Q}$ is countable; $\mathbb{R}$ is not.
- Your first half: if $L : K$ is algebraic and $K$ is countable, $L$ is
  countable.

You cannot feed $L = \mathbb{R}$, $K = \mathbb{Q}$ into your first half. If you
could, $\mathbb{R}$ would be countable and it is not. So the first half is not
being applied to $\mathbb{R}$; it is being applied to something sitting inside
$\mathbb{R}$.

**Your move.** Name the set your counting argument applies to --- one set of
real numbers, described in words --- and say what fact about $\mathbb{R}$ then
forces a transcendental real to exist.
