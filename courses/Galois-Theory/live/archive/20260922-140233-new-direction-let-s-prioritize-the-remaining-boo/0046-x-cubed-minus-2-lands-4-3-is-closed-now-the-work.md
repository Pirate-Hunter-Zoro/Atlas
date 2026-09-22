---
kind: lesson
title: x-cubed-minus-2-lands-4-3-is-closed-now-the-worksheet
---
**$x^3 - 2$, degree $3$, and 4.3 is closed.** Your cofactor expansion is right:
$x(x^2) - 2$, no matrix anywhere in the answer, and $\alpha = 2^{1/3}$ is a root.
The determinant question is settled. The argument at the foot of your page --
$(\chi - m)(\alpha) = 0$, degree below $n$ because both are monic of degree $n$,
so zero because $m$ has least degree among non-zero polynomials killing
$\alpha$, hence $\chi = m$ -- is exercise 4.3, finished. It is in
`ch04-homework.tex` now, in your words, with your page filed beside it.

Chapter 4 is done. The worksheet starts here.

**Problem 6. A concrete quartic.** Let $K = \mathbb{Q}(\sqrt{2},\sqrt{3})$ and
$\gamma = \sqrt{2} + \sqrt{3}$.

(a) Show that $[K:\mathbb{Q}] = 4$.

(b) Show that $K = \mathbb{Q}(\gamma)$, and compute $m_{\gamma,\mathbb{Q}}$.

(c) Find three proper intermediate fields.

What this uses:

- $\mathbb{Q}(\sqrt{2},\sqrt{3})$ --- the smallest subfield of $\mathbb{C}$ containing $\mathbb{Q}$, $\sqrt{2}$ and $\sqrt{3}$.
- $[K:\mathbb{Q}]$ --- the dimension of $K$ as a vector space over $\mathbb{Q}$.
- $\mathbb{Q}(\gamma)$ --- the smallest subfield containing $\mathbb{Q}$ and $\gamma$.
- $m_{\gamma,\mathbb{Q}}$ --- the monic rational polynomial of least degree with $\gamma$ as a root.
- intermediate field --- a subfield of $K$ that contains $\mathbb{Q}$.
- proper, here --- neither $\mathbb{Q}$ nor all of $K$.
- tower law --- $[K:\mathbb{Q}] = [K:M][M:\mathbb{Q}]$ whenever $\mathbb{Q} \subseteq M \subseteq K$.
- spanning bound --- if $m$ elements span a space, its dimension is at most $m$.

**Your move.** One line of arithmetic. Square $\gamma = \sqrt{2} + \sqrt{3}$ and
write the result as a rational combination of $1$, $\sqrt{2}$, $\sqrt{3}$ and
$\sqrt{6}$. Which of those four actually appear?
