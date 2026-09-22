---
kind: lesson
title: k-over-f-is-notation-not-a-quotient
---
**$K/F$ is just notation for "$K$ is a field containing $F$" --- there is no
quotient anywhere.** The slash is read "over": $K$ over $F$. It names the pair,
not an operation on it, and it is called an *extension*. $F$ sits inside $K$ as
a subfield, and $K$ is a vector space over $F$, so the pair has a dimension:
that is $[K:F]$, the degree.

The clash with quotient rings is real and everyone meets it once. $R/I$ needs
$I$ to be an ideal of $R$; $F$ is a subfield of $K$, and a subfield is never an
ideal of $K$ except $\{0\}$. So the two notations never collide on the same
symbols. You have already used the extension slash without it being written:
$\mathbb{Q}(\sqrt2)/\mathbb{Q}$ is what "degree $2$ over $\mathbb{Q}$" meant on
your last card.

**Problem 3. Degrees.** Let $K/F$ be a finite extension of degree $n$. Show
that for any $\alpha \in K$, the degree of $m_{\alpha,F}$ divides $n$.

What this uses:

- $K/F$ --- $K$ is a field with $F$ as a subfield.
- $[K:F] = n$ --- the dimension of $K$ as a vector space over $F$.
- $m_{\alpha,F}$ --- the monic polynomial with coefficients in $F$, of least degree, with $\alpha$ as a root.
- $F(\alpha)$ --- the smallest subfield of $K$ containing $F$ and $\alpha$.
- $\deg m_{\alpha,F} = [F(\alpha):F]$ --- the degree of the minimal polynomial *is* the degree of the simple extension it generates.
- Tower law --- $[K:F] = [K:M]\,[M:F]$ for any field $M$ with $F \subseteq M \subseteq K$.
- divides --- $d \mid n$ means $n = dk$ for some positive integer $k$.

**Your move.** Prove it: for any $\alpha \in K$, $\deg m_{\alpha,F}$ divides
$n$.
