---
kind: lesson
title: check 12a-distinctness
---
Not yet: you showed $f$ has $q$ roots, but every degree-$q$ polynomial has that many in its splitting field. The problem asks for $q$ *distinct* roots, and that is the part still missing.

Your factoring $f(x) = x\,(x^{q-1} - 1)$ is a good start. It does separate out the root $0$, and $0$ is not a root of $x^{q-1} - 1$. But "$x^{q-1} - 1$ gives $q - 1$ roots" counts with multiplicity. Nothing on the page stops some of those roots from repeating. That is what the repeated-root test is for.

**Problem 12(a).** Let $p$ be prime, $q = p^n$, and let $E$ be a splitting field of $f(x) = x^q - x$ over $\mathbb{F}_p$. Show that $f$ has $q$ distinct roots in $E$.

What it uses:

- $\mathbb{F}_p$: the field $\mathbb{Z}/p\mathbb{Z}$. In it, $p \cdot 1 = 0$.
- Splitting field: $E$ is generated over $\mathbb{F}_p$ by the roots of $f$, and $f$ factors into linear factors in $E[x]$.
- Formal derivative: for $g = \sum a_k x^k$, $g' = \sum k\, a_k x^{k-1}$, defined by this formula over any field.
- Repeated-root test: $\alpha$ is a repeated root of $g$ exactly when $g(\alpha) = 0$ and $g'(\alpha) = 0$.
- $\deg f = q$, so $f$ has $q$ roots in $E$ counted with multiplicity.

Compute $f'(x)$ in $\mathbb{F}_p[x]$, say why $q \cdot 1 = 0$ there, and use the repeated-root test to show that $x^q - x$ has $q$ distinct roots in $E$.
