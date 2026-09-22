---
kind: lesson
title: three-a-is-proved-now-3c-root-2-outside-q-cbrt-2
---
**3(a) is proved.** $F(\alpha)$ as the middle field, tower law, then
$\deg m_{\alpha,F} = [F(\alpha):F]$ --- that is the argument, and all three
steps are yours.

One reason was thinner than the answer. The tower law does not say *divides*;
it says $n = [K:F(\alpha)]\,[F(\alpha):F]$. Divisibility is that equation plus
the fact that $[K:F(\alpha)]$ is a positive integer, so it is the quotient $q$.
Your line skipped the equation and asserted the conclusion. The write-up now
has the equation, and also the one word you left out: $\alpha$ is algebraic
over $F$ at all because $[K:F]$ is finite, which is what lets $m_{\alpha,F}$
exist to have a degree.

Next, 3(c), and it is 3(a) used once.

**Problem 3(c).** Show that $\sqrt2 \notin \mathbb{Q}(\sqrt[3]{2})$.

What this uses:

- $\mathbb{Q}(\sqrt[3]{2})$ --- the smallest subfield of $\mathbb{R}$ containing $\mathbb{Q}$ and the real cube root of $2$.
- $[K:F]$ --- the dimension of $K$ as a vector space over $F$.
- $m_{\alpha,F}$ --- the monic polynomial over $F$ of least degree with $\alpha$ as a root.
- $\deg m_{\alpha,F} = [F(\alpha):F]$.
- $x^3 - 2$ is irreducible over $\mathbb{Q}$ --- no rational root, and a cubic with no linear factor has no factorisation.
- $x^2 - 2$ is irreducible over $\mathbb{Q}$ --- $\sqrt2$ is irrational.
- irreducible and monic with $\alpha$ as a root $\Rightarrow$ it is $m_{\alpha,\mathbb{Q}}$.
- 3(a), now yours --- if $[K:F] = n$ then $\deg m_{\alpha,F}$ divides $n$ for every $\alpha \in K$.

**Your move.** Prove that $\sqrt2$ is not an element of
$\mathbb{Q}(\sqrt[3]{2})$. Write the whole argument.
