---
kind: lesson
title: contradiction-is-the-route-4-7-closed-now-4-11
---
**Right, and 4.7 is closed.** Suppose no real is transcendental over
$\mathbb{Q}$. Then every real is algebraic over $\mathbb{Q}$, which is exactly
the statement that $\mathbb{R} : \mathbb{Q}$ is algebraic. Your first half,
with $K = \mathbb{Q}$ countable, then makes $\mathbb{R}$ countable. It is not.
So the supposition fails and a transcendental real exists.

Last card I told you that you cannot feed $L = \mathbb{R}$ into your first
half. You just did, and correctly: inside a proof by contradiction the absurd
conclusion is the point. Your route is shorter than the one I was steering you
towards, and it is the one that is now in the write-up.

**Exercise 4.11.** Show that the condition that $L : K$ is algebraic cannot be
dropped from Theorem 4.8.

What it uses:

- Theorem 4.8 --- if $L : K$ is algebraic and $\tau : L \to L$ is a
  monomorphism fixing $K$, then $\tau$ maps $L$ onto $L$.
- Monomorphism --- an injective ring homomorphism.
- Fixes $K$ --- $\tau(k) = k$ for every $k \in K$.
- $L : K$ algebraic --- every element of $L$ is a root of some non-zero
  polynomial in $K[x]$.
- $t$ transcendental over $K$ --- a root of no non-zero polynomial in $K[x]$.
- $K(t)$ --- the field of rational functions in $t$: everything of the form
  $f(t)/g(t)$ with $f, g \in K[x]$ and $g \neq 0$.
- "Cannot be dropped" --- exhibit one extension $L : K$ that is *not*
  algebraic, together with one monomorphism $\tau : L \to L$ fixing $K$ which
  does *not* map $L$ onto $L$.

Take $L = K(t)$ with $t$ transcendental over $K$. That extension is not
algebraic, since $t$ is a root of nothing. Define $\tau$ by substituting $t^2$
for $t$ throughout: $f(t)/g(t) \mapsto f(t^2)/g(t^2)$. It fixes $K$ and it is
injective; take both of those on trust for now.

**Your move.** Is $t$ itself in the image of that $\tau$ --- is there a
rational function $h$ in $K(t)$ with $\tau(h) = t$? Yes or no, and one sentence
for why.
