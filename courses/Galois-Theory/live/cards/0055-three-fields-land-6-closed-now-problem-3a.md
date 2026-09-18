---
kind: lesson
title: three-fields-land-6-closed-now-problem-3a
---
**All three land, and Problem 6 is closed.** $\mathbb{Q}(\sqrt2)$,
$\mathbb{Q}(\sqrt3)$, $\mathbb{Q}(\sqrt6)$, each of degree $2$ over
$\mathbb{Q}$, so none is $\mathbb{Q}$ and none is $K$. Your right-hand column is
the reason they are three *different* fields: $\sqrt3$ and $\sqrt6$ are outside
$\mathbb{Q}(\sqrt2)$, and likewise down the list, so no two of them coincide.
$\sqrt6 \in K$ because $\sqrt2\,\sqrt3 = \sqrt6$ and $K$ is closed under
multiplication. All of 6 is now in the write-up.

Next sheet problem. Part (b) is exercise 4.6, which you proved, so it is not
re-posed.

**Problem 3. Degrees.** Let $K/F$ be a finite extension of degree $n$. Show
that for any $\alpha \in K$, the degree of $m_{\alpha,F}$ divides $n$.

What this uses:

- $[K:F] = n$ --- the dimension of $K$ as a vector space over $F$.
- $m_{\alpha,F}$ --- the monic polynomial with coefficients in $F$, of least degree, with $\alpha$ as a root.
- $F(\alpha)$ --- the smallest subfield of $K$ containing $F$ and $\alpha$.
- $\deg m_{\alpha,F} = [F(\alpha):F]$ --- the degree of the minimal polynomial *is* the degree of the simple extension it generates.
- Tower law --- $[K:F] = [K:M]\,[M:F]$ for any field $M$ with $F \subseteq M \subseteq K$.
- divides --- $d \mid n$ means $n = dk$ for some positive integer $k$.

**Your move.** Prove it: for any $\alpha \in K$, $\deg m_{\alpha,F}$ divides
$n$.
