---
kind: lesson
title: check 8b-divide-by-x
---
Your right-hand side is correct: $(x+1)^p - 1 = \sum_{i=1}^{p} \binom{p}{i} x^i$. And yes, it is reducible. It is supposed to be. That common $x$ is the factor $x-1$ from the left-hand side, shifted.

You substituted into the right side only. Do the left side too:

$$\big((x+1)-1\big)\,\Phi_p(x+1) = \sum_{i=1}^{p} \binom{p}{i} x^i.$$

The left side is $x \cdot \Phi_p(x+1)$. So the $x$ you found on the right is exactly this $x$, and cancelling it leaves $\Phi_p(x+1)$ alone. That is the polynomial we test, not $(x+1)^p - 1$.

**Problem 8(b).** Let $p$ be prime and $\Phi_p(x) = x^{p-1} + \cdots + x + 1$. Show that $\Phi_p$ is irreducible over $\mathbb{Q}$.

What you need:
- $(x-1)\,\Phi_p(x) = x^p - 1$.
- Binomial theorem: $(x+1)^p = \sum_{k=0}^{p} \binom{p}{k} x^k$.
- Eisenstein at $q$: $q$ divides every coefficient but the leading one, and $q^2$ does not divide the constant term, so the polynomial is irreducible over $\mathbb{Q}$.
- If $f(x+1)$ is irreducible, so is $f(x)$.

Divide both sides by $x$. Write $\Phi_p(x+1)$ as a sum of binomial coefficients times powers of $x$, with the index range correct, and name its constant term and its leading coefficient.
