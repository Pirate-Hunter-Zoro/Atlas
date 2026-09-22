---
kind: lesson
title: membership-lands-now-write-the-whole-of-4-8-second-half
---
Right. $c_2\beta^2$, $c_1\beta$ and $c_0$ all lie in $K(\beta)$, and the sum of
them does too, so $\alpha = f(\beta) \in K(\beta)$. One refinement: closure under
addition is what finishes it, but closure under *multiplication* is what got the
first two pieces in. $\beta \in K(\beta)$, so $\beta^2 \in K(\beta)$; $c_2 \in K
\subseteq K(\beta)$, so $c_2\beta^2 \in K(\beta)$. Nothing about the argument
cares that $n = 2$.

That was the missing link. You now have every part of the proof, so write it.

**Exercise 4.8, second half.** *$L\!:\!K$ is a field extension. $\alpha \in L$ is
transcendental over $K$, and $f \in K[x]$ is non-constant. Suppose $\beta \in L$
satisfies $f(\beta) = \alpha$. Show that $\beta$ is transcendental over $K$.*

What it uses:

- Transcendental over $K$ — not a root of any non-zero polynomial in $K[x]$.
- Algebraic over $K$ — a root of some non-zero polynomial in $K[x]$.
- $K(\beta)$ — the smallest subfield of $L$ containing $K$ and $\beta$.
- A subfield is closed under addition and multiplication, and contains $K$.
- $[K(\beta):K]$ — the dimension of $K(\beta)$ as a vector space over $K$.
- $\beta$ algebraic over $K$ $\iff$ $[K(\beta):K]$ is finite.
- Every element of a finite extension of $K$ is algebraic over $K$.
- $f = c_n x^n + \dots + c_1 x + c_0$, every $c_i \in K$, $n \ge 1$.

**Your move.** The full proof, on paper. Your own skeleton, with the link you
just supplied in the middle: assume $\beta$ is algebraic, use that to reach
"$\alpha$ is algebraic over $K$", and hit the hypothesis. Four or five lines.
Photograph it.
