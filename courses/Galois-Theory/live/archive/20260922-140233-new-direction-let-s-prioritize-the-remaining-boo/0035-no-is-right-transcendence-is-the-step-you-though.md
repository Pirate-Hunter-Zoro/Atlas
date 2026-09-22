---
kind: lesson
title: no-is-right-transcendence-is-the-step-you-thought-you-skipped
---
**No is right, and the fact you thought you skipped is exactly the one that
makes it right.** Your reason is handwavy because it is one line short, not
because it is wrong. Transcendence is that line.

Here is where it enters. Suppose $h = f(t)/g(t)$ satisfies $\tau(h) = t$. Then
$f(t^2)/g(t^2) = t$, so $f(t^2) = t \cdot g(t^2)$. Both sides are polynomial
expressions in $t$. Because $t$ is transcendental over $K$, no non-zero
polynomial in $K[x]$ vanishes at $t$, so two polynomial expressions in $t$ are
equal only when their coefficients agree term by term.

That is the whole use of it. Transcendence turns an equation between elements
of the field $K(t)$ into an equation between coefficient lists. Were $t$
algebraic it would satisfy some relation, and two different coefficient lists
could name the same element --- your argument would have nothing to compare.

What this uses:

- $t$ transcendental over $K$ --- a root of no non-zero polynomial in $K[x]$.
- $K(t)$ --- rational functions $f(t)/g(t)$ with $f, g \in K[x]$, $g \neq 0$.
- $\tau$ --- substitutes $t^2$ for $t$: $f(t)/g(t) \mapsto f(t^2)/g(t^2)$.
- Image $\tau(L)$ --- everything of the form $\tau(h)$ for $h \in L$.
- $f(t^2)$ --- replace $x$ by $t^2$ in $f$: if
  $f = a_0 + a_1 x + a_2 x^2 + \cdots$ then
  $f(t^2) = a_0 + a_1 t^2 + a_2 t^4 + \cdots$.

**Your move.** Look at $f(t^2) = t \cdot g(t^2)$. Every power of $t$ on the
left is even. Say in one word which powers of $t$ appear on the right, and then
say what matching coefficients across that equation forces about $f$ and $g$.
