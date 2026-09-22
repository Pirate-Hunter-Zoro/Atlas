---
kind: lesson
title: first-half-lands-second-half-substitutes-beta-in-the-wrong-place
---
First half of 4.8 is right and closed. You produced $g \circ f$, which is exactly
the polynomial exhibiting $\alpha$ as a root. Two words to add when you write it
up. Say $g$ is **non-zero** in the supposition — algebraic means a root of a
*non-zero* polynomial, and without that word the zero polynomial gives
$g(f(\alpha)) = 0$ for free. Then say why $g \circ f$ is itself non-zero:
$\deg (g \circ f) = (\deg g)(\deg f) \ge 1$, so it is not the zero polynomial.

That degree line is where your first transcribed line bites. You copied the
hypothesis as "$f \in K[x]$, non-zero". It is **non-constant**. Take $f = 2$:
then $f(\alpha) = 2$, which lies in $K$ and is algebraic, and the exercise is
false. Non-constant is the hypothesis that makes $\deg f \ge 1$.

The second half does not work as written. From $h(\beta) = 0$ you wrote
$h(f(\beta)) = 0$. Substituting $\beta$ into $h \circ f$ gives $h(f(\beta))$,
which is $h(\alpha)$, and nothing you have says *that* is zero. The composite
trick ran the right way in the first half because $\alpha$ sat inside $f$. Here
$\beta$ sits inside $f$ and $\alpha$ is the output, so composing cannot reach it.
You need a different instrument.

**Second half of 4.8.** *$L\!:\!K$ is an extension, $\alpha \in L$ is
transcendental over $K$, $f \in K[x]$ is non-constant. If $\beta \in L$ satisfies
$f(\beta) = \alpha$, show $\beta$ is transcendental over $K$.*

What that uses:

- $K(\beta)$ — the smallest subfield of $L$ containing $K$ and $\beta$.
- $[K(\beta):K]$ — the degree: the dimension of $K(\beta)$ as a vector space over $K$.
- $\beta$ algebraic over $K$ $\iff$ $[K(\beta):K]$ is finite.
- Every element of a finite extension of $K$ is algebraic over $K$.
- $f(\beta) = \alpha$, with $f$ having all its coefficients in $K$.

**Your move.** Suppose $\beta$ were algebraic over $K$, so $[K(\beta):K]$ is
finite. Why must $\alpha$ lie in $K(\beta)$?
