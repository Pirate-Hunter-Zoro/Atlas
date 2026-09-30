---
kind: lesson
title: check 8b-shift-p3
---
Your uniqueness argument is right, and 8(a) is done. $\tau$ and $\sigma$ both fix each $a_i$, both respect sums and powers, and both send $\alpha \mapsto \beta$, so they agree on every $\sum a_i\alpha^i$. That is every element of $F(\alpha)$. The worksheet file now has all of 8(a) typeset: existence, then uniqueness.

Next is 8(b). It is the step 8(c) needs to get $[\mathbb{Q}(\zeta_p):\mathbb{Q}] = p-1$.

**Problem 8(b).** Let $p$ be prime and $\Phi_p(x) = x^{p-1} + x^{p-2} + \cdots + x + 1$. Show that $\Phi_p$ is irreducible over $\mathbb{Q}$.

Eisenstein does not apply to $\Phi_p$ as it stands, because every coefficient is $1$. The standard move is to substitute $x \mapsto x+1$ first. Try it on the smallest case before the general one.

What you need:
- $\Phi_3(x) = x^2 + x + 1$.
- Eisenstein at a prime $q$ (yours from Chapter 5): if $q$ divides every coefficient except the leading one, and $q^2$ does not divide the constant term, the polynomial is irreducible over $\mathbb{Q}$.

Expand $\Phi_3(x+1)$. Does Eisenstein at $q = 3$ apply to the result?
