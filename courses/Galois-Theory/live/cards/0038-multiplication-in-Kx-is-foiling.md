---
kind: note
title: FOILing is exactly what it is — collected by power
---

Your question first.

**Multiplication in $K[x]$ is FOILing.** That is not a shortcut or a trick; it
*is* the definition, written out. You multiply every term of $f$ by every term
of $g$, and then collect the ones that carry the same power of $x$.

Do it for $f = a_0 + a_1x$ and $g = b_0 + b_1x$ and watch it happen:

$$(a_0 + a_1x)(b_0 + b_1x) = \underbrace{a_0b_0}_{x^0} + \underbrace{(a_0b_1 + a_1b_0)}_{x^1}x + \underbrace{a_1b_1}_{x^2}x^2$$

The middle coefficient is a *sum of two products*, because there were two ways
to make an $x^1$: take the $x^0$ from $f$ and the $x^1$ from $g$, or the other
way round. That is the whole content of the general formula:

$$fg = \sum_m c_m x^m, \qquad c_m = \sum_{i+j=m} a_ib_j.$$

The $m$-th coefficient of $fg$ collects every pair of indices that adds to $m$.
So $c_2 = a_0b_2 + a_1b_1 + a_2b_0$ — three terms, not one.

What it is **not**: the $m$-th coefficient of $fg$ is not $a_mb_m$. Coefficients
do not multiply in place the way they add in place. Addition is index-by-index;
multiplication is not, and that asymmetry is the only genuinely new thing in
this half of 3.8.

**Your move** — thirty seconds, so the arithmetic is in your hand before the
general case. In $\mathbb{Z}[x]$ take

$$f = 2 + 3x, \qquad g = 1 + 4x + 5x^2.$$

Write down $c_0$, $c_1$, $c_2$, $c_3$ — the four coefficients of $fg$ — using
$c_m = \sum_{i+j=m} a_ib_j$. Four numbers, that is all.
