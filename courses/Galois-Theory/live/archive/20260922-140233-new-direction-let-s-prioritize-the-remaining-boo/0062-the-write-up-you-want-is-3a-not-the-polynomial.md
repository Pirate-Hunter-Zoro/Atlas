---
kind: lesson
title: the-write-up-you-want-is-3a-not-the-polynomial
---
**The best way to write it up is 3(a), which you proved an hour ago.** Your
instinct is right and the polynomial route is the long way round to the same
fact.

Where your line stops being a proof. $\sum_{i=0}^{n} a_i (\sqrt[3]{2})^i$ is
$a_0 + a_1\sqrt[3]{2} + a_2\sqrt[3]{4} + \cdots$, and the next line keeps only
$a_i 2^{1/3}$ --- one term where there were several. So "that can't happen" is
being said about an equation in one unknown, when the real equation has three.
And with three, it is not obvious: $a_0 + a_1\sqrt[3]{2} + a_2\sqrt[3]{4} =
\sqrt2$ is refused only because $1, \sqrt[3]{2}, \sqrt[3]{4}$ are linearly
independent over $\mathbb{Q}$.

That independence is exactly $[\mathbb{Q}(\sqrt[3]{2}):\mathbb{Q}] = 3$. Which
is why the degree argument is not a different proof from yours --- it is yours,
with the hard step done by 3(a) instead of by hand.

**Problem 3(c).** Show that $\sqrt2 \notin \mathbb{Q}(\sqrt[3]{2})$.

What this uses:

- $\mathbb{Q}(\sqrt[3]{2})$ --- the smallest subfield of $\mathbb{R}$ containing $\mathbb{Q}$ and the real cube root of $2$.
- $[K:F]$ --- the dimension of $K$ as a vector space over $F$.
- $m_{\alpha,F}$ --- the monic polynomial over $F$ of least degree with $\alpha$ as a root.
- $\deg m_{\alpha,F} = [F(\alpha):F]$.
- irreducible and monic with $\alpha$ as a root $\Rightarrow$ it is $m_{\alpha,\mathbb{Q}}$.
- $x^2 - 2$ is irreducible over $\mathbb{Q}$ --- $\sqrt2$ is irrational.
- 3(a), yours --- if $[K:F] = n$ then $\deg m_{\alpha,F}$ divides $n$ for every $\alpha \in K$.

**Your move, one line only.** What is $\deg m_{\sqrt2,\mathbb{Q}}$, and what
makes it that? Not the whole proof yet --- just that number with its reason.
