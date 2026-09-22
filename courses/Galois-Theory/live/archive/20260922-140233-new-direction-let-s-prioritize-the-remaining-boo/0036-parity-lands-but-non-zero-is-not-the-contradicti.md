---
kind: lesson
title: parity-lands-but-non-zero-is-not-the-contradiction
---
**Odd is right, and the parity split is the whole engine.** One clause is doing
the wrong job: "both polynomials are non-zero since $t$ is transcendental."
Transcendence does not make a polynomial non-zero. It does something else, and
you need that other thing.

And non-zero is not yet a contradiction. Two non-zero things can be equal.
What you have is sharper: the left side uses only even powers of $t$, the right
side only odd ones. Nothing on one side can be matched by anything on the
other. So matching coefficients does not say "these differ" --- it says every
coefficient on both sides is $0$.

Transcendence is what licenses the matching at all. Because no non-zero
polynomial in $K[x]$ kills $t$, two polynomial expressions in $t$ are equal
only when their coefficient lists agree term by term.

Take these concrete ones. Let $f = a_0 + a_1 x + a_2 x^2$ and
$g = b_0 + b_1 x$. Then
$$f(t^2) = a_0 + a_1 t^2 + a_2 t^4, \qquad t\,g(t^2) = b_0 t + b_1 t^3.$$

What this uses:

- $t$ transcendental over $K$ --- a root of no non-zero polynomial in $K[x]$.
- $L = K(t)$ --- rational functions $f(t)/g(t)$, $f, g \in K[x]$, $g \neq 0$.
- $\tau$ --- substitutes $t^2$ for $t$: $f(t)/g(t) \mapsto f(t^2)/g(t^2)$.
- $f(t^2)$ --- replace $x$ by $t^2$: $a_0 + a_1 t^2 + a_2 t^4 + \cdots$, even
  powers only.
- Matching coefficients --- for each power of $t$ separately, the number in
  front of it on the left equals the number in front of it on the right.

**Your move.** Set those two displayed expressions equal. Go through the powers
$t^0, t^1, t^2, t^3, t^4$ one at a time and say what each comparison forces
about $a_0, a_1, a_2, b_0, b_1$. Five short verdicts, nothing else.
