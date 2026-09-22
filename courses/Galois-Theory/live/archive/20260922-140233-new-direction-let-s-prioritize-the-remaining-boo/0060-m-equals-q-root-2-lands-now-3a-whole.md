---
kind: lesson
title: m-equals-q-root-2-lands-now-3a-whole
---
**$M = \mathbb{Q}(\sqrt2)$ is right, and $2 \mid 4$ is the entire shape of the
proof.** You found a field sitting between $F$ and $K$ that contains $\alpha$,
and its degree divided $n$ because the tower law left it no choice. Notice what
you did *not* use: nothing about $\sqrt[4]{2}$, nothing about degree $4$.
Replace $\mathbb{Q}(\sqrt2)$ by $F(\alpha)$ and the same three lines run in
general.

So here is 3(a) again, whole.

**Problem 3(a).** Let $K/F$ be a finite extension with $[K:F] = n$. Prove that
for every $\alpha \in K$, $\deg m_{\alpha,F}$ divides $n$.

What this uses:

- $K/F$ --- $K$ is a field containing $F$ as a subfield; a slash, not a quotient.
- $[K:F]$ --- the dimension of $K$ as a vector space over $F$.
- finite extension --- $[K:F]$ is finite.
- $\alpha$ algebraic over $F$ --- some non-zero polynomial with coefficients in $F$ has $\alpha$ as a root.
- every $\alpha \in K$ is algebraic over $F$ when $[K:F] = n$ --- the $n+1$ elements $1, \alpha, \dots, \alpha^n$ cannot be independent in an $n$-dimensional space.
- $m_{\alpha,F}$ --- the monic polynomial over $F$ of least degree with $\alpha$ as a root.
- $F(\alpha)$ --- the smallest subfield of $K$ containing $F$ and $\alpha$.
- $\deg m_{\alpha,F} = [F(\alpha):F]$.
- Tower law --- $[K:F] = [K:M]\,[M:F]$ whenever $F \subseteq M \subseteq K$ are fields.
- $d$ divides $n$ --- $n = dq$ for some positive integer $q$.

**Your move.** Take $K/F$ finite of degree $n$ and any $\alpha \in K$, and
prove that $\deg m_{\alpha,F}$ divides $n$. Write the whole argument.
