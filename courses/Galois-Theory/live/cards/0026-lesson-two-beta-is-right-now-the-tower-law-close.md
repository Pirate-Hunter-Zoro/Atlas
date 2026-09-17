---
kind: lesson
title: lesson two-beta-is-right-now-the-tower-law-closes-4-10
---
$\beta^4 = 2\beta$ is right, and notice what it did: a fourth power collapsed
back into the same three slots, with $a = 0$, $b = 2$, $c = 0$. That is the
"feel" you asked for last time. No power of $\beta$ ever needs a fourth slot,
because $\beta^3 = 2$ trades every excess power for a rational number.

Back to 4.10, which you are one step from finishing.

**Exercise 4.10.** Suppose $K(\alpha, \beta) : K$ is an extension, that $\alpha$
is algebraic over $K$ but not in $K$, and that $\beta$ is transcendental over
$K$. Show that $K(\alpha, \beta) : K$ is not simple.

Where you are. You assumed a $\gamma$ with $K(\gamma) = K(\alpha, \beta)$ and
split on $\gamma$. The algebraic case you closed. In the transcendental case you
proved $\gamma$ is algebraic over $K(\alpha)$ — that was the graded polynomial
$\alpha g(x) - f(x)$. So you now have two finite degrees stacked on each other,
and one fact turns them into the contradiction.

What it uses:

- $[M:L]$ — the dimension of $M$ as a vector space over $L$; finite means a
  finite basis.
- Degree of an algebraic element — if $\delta$ is algebraic over $L$ with
  minimal polynomial of degree $n$, then $[L(\delta):L] = n$, which is finite.
- Tower law — for fields $L \subseteq M \subseteq N$,
  $[N:L] = [N:M]\,[M:L]$. In particular $[N:L]$ is finite exactly when both
  factors are.
- Finite implies algebraic — if $[M:L]$ is finite, every element of $M$ is
  algebraic over $L$. (The powers $1, \delta, \delta^2, \dots$ cannot all be
  independent.)
- Transcendental over $K$ — not a root of any non-zero polynomial in $K[x]$.

**Your move.** Take the tower $K \subseteq K(\alpha) \subseteq K(\alpha,
\gamma)$. Say why each of the two steps has finite degree, what the tower law
then gives for $[K(\alpha, \gamma) : K]$, and what that forces about $\gamma$.
