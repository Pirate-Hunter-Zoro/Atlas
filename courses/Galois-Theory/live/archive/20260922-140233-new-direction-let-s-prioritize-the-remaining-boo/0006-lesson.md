---
kind: lesson
title: f-alpha-equals-beta-is-not-given-the-skeleton-around-it-is-right
---
"Since $f(\alpha) = \beta$" is not given. The hypothesis is $f(\beta) = \alpha$.
Writing the reverse is the one thing the exercise will not let you have, so the
new annotation patches the gap by assuming it away.

Everything around that line is right, and worth saying out loud. Your skeleton
is: suppose $\beta$ algebraic, get $h \ne 0$ in $K[x]$ with $h(\beta) = 0$,
derive that $\alpha$ is algebraic over $K$, contradict the hypothesis that
$\alpha$ is transcendental. That is the correct contradiction to aim at. The
first half is closed too — $g \circ f \ne 0$ with $\alpha$ as a root is exactly
the argument.

Only the middle link fails, and no composition will fix it. To compose you would
need $\alpha$ to be a root of something built from $h$, and $h$'s root is
$\beta$. The direction of $f$ is fixed and it points the wrong way.

The link that does work does not use $h$ at all. It uses where $\alpha$ lives:
$\alpha = f(\beta)$, and $f(\beta)$ is assembled out of $\beta$ and the
coefficients of $f$.

**Second half of 4.8, restated.** *$L\!:\!K$ is an extension, $\alpha \in L$ is
transcendental over $K$, $f \in K[x]$ is non-constant. If $\beta \in L$ satisfies
$f(\beta) = \alpha$, show $\beta$ is transcendental over $K$.*

What it uses:

- $K(\beta)$ — the smallest subfield of $L$ containing $K$ and $\beta$.
- A subfield is closed under addition and multiplication.
- $[K(\beta):K]$ — the dimension of $K(\beta)$ as a vector space over $K$.
- $\beta$ algebraic over $K$ $\iff$ $[K(\beta):K]$ is finite.
- Every element of a finite extension of $K$ is algebraic over $K$.
- $f = c_n x^n + \dots + c_1 x + c_0$ with every $c_i \in K$.

**Your move.** Still the question from the last card, asked concretely. Take
$f = c_2 x^2 + c_1 x + c_0$. Write out $f(\beta)$. Which of the pieces you have
just written down are in $K(\beta)$, and why does that put $f(\beta)$ itself in
$K(\beta)$?
