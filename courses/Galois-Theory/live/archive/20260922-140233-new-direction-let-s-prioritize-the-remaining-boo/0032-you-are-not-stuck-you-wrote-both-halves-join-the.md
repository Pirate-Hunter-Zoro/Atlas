---
kind: lesson
title: you-are-not-stuck-you-wrote-both-halves-join-them
---
**You are one sentence from finished, and both halves of that sentence are
already on your page.** You wrote that every $\ell \in L$ is a root of some
polynomial in $K[x]$, and that each $f \in K[x]$ has only finitely many roots.
Those are the two facts the proof runs on. What is missing is the set that holds
them together.

Your bound is right, and it can be sharper. "Finitely many" is what you need;
the named fact gives at most $n$ for $f$ of degree $n$.

Here is the object to work with. For each non-zero $f \in K[x]$, let $R_f$ be
the set of elements of $L$ that are roots of $f$. Your first line says every
$\ell$ lands in at least one $R_f$. Your second says every $R_f$ is small.

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
- A non-zero polynomial of degree $n$ has at most $n$ roots in any field.
- $K[x]$ is countable --- your own result, one card ago.
- $\mathbb{Q}$ is countable; $\mathbb{R}$ is not.

**Your move.** Write $L$ as a union of the sets $R_f$. Say what the union is
indexed by, and name which fact in the list above turns that union into "$L$ is
countable".
