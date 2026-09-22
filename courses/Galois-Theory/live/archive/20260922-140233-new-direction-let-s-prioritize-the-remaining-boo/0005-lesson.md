---
kind: lesson
title: you-wrote-alpha-i-read-beta-and-the-line-still-wants-a-root
---
No — you wrote $\alpha$ and I read $\beta$. The page says $h(f(\alpha))$, so my
last card corrected a line you never wrote. That one is mine.

Read as written, the line still wants something it has not got. $h(f(\alpha)) = 0$
says $f(\alpha)$ is a root of $h$. The only root of $h$ you have is $\beta$, out
of the supposition $h(\beta) = 0$. So that step needs $f(\alpha) = \beta$. The
hypothesis hands you $f(\beta) = \alpha$, the other way round.

The rest of the block is sound. $h \ne 0$ with $f$ non-constant does give
$h \circ f \ne 0$, and a non-zero polynomial over $K$ with $\alpha$ as a root is
exactly what would finish the exercise. There is just no way to make $\alpha$ be
its root. Composition was the instrument for the first half; for this half it is
degrees.

**Second half of 4.8.** *$L\!:\!K$ is an extension, $\alpha \in L$ is
transcendental over $K$, $f \in K[x]$ is non-constant. If $\beta \in L$ satisfies
$f(\beta) = \alpha$, show $\beta$ is transcendental over $K$.*

What that uses:

- $K(\beta)$ — the smallest subfield of $L$ containing $K$ and $\beta$.
- $[K(\beta):K]$ — the degree: the dimension of $K(\beta)$ as a vector space over $K$.
- $\beta$ algebraic over $K$ $\iff$ $[K(\beta):K]$ is finite.
- Every element of a finite extension of $K$ is algebraic over $K$.
- $f(\beta) = \alpha$, with every coefficient of $f$ lying in $K$.

**Your move.** Suppose $\beta$ is algebraic over $K$, so $[K(\beta):K]$ is finite.
Why must $\alpha$ lie in $K(\beta)$?
