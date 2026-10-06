---
kind: lesson
title: check 12a-distinct-roots
---
Accepted: 11(c) is done. $\mathbb{F}_q^\times$ is cyclic. Two small repairs go into the write-up.

- Take $K = \mathbb{F}_q$ and $G = \mathbb{F}_q^\times$. Then $G \subseteq K^\times$ is the whole group, and it is finite of order $q - 1$ because $\mathbb{F}_q$ is finite. It is a subgroup of $K^\times$, not of $\mathbb{F}$; the field itself is not a group under multiplication, because $0$ has no inverse.
- Your margin line has the inequality backwards. 11(b) proved $N(d) \le \varphi(d)$, so the terms $\varphi(d) - N(d)$ are the nonnegative ones. The logic was right; the fact cited was flipped.

**Problem 12(a).** Let $p$ be prime, $q = p^n$, and let $E$ be a splitting field of $f(x) = x^q - x$ over $\mathbb{F}_p$. Show that $f$ has $q$ distinct roots in $E$.

What it uses:

- $\mathbb{F}_p$: the field $\mathbb{Z}/p\mathbb{Z}$. In it, $p \cdot 1 = 0$.
- Splitting field: $E$ is generated over $\mathbb{F}_p$ by the roots of $f$, and $f$ factors into linear factors in $E[x]$.
- Formal derivative: for $g = \sum a_k x^k$, $g' = \sum k\, a_k x^{k-1}$. No limits; it is defined by this formula over any field.
- Repeated-root test: $\alpha$ is a repeated root of $g$ exactly when $g(\alpha) = 0$ and $g'(\alpha) = 0$.
- $\deg f = q$, so $f$ has $q$ roots in $E$ counted with multiplicity.

Show that $f(x) = x^q - x$ has $q$ distinct roots in its splitting field $E$ over $\mathbb{F}_p$.
