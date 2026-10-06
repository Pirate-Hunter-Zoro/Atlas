---
kind: lesson
title: check 8b-general-shift
---
Your instinct is right: the answer is $x^2+3x+3$, and Eisenstein at $3$ does apply. The $+4$ came from one slip. You shifted the constant term: $\Phi_3(x+1) = (x+1)^2 + (x+1) + 1$, and that last $1$ stays $1$, not $2$.

$$\Phi_3(x+1) = x^2 + 2x + 1 + x + 1 + 1 = x^2 + 3x + 3.$$

$3$ divides $3$ and $3$, and $9$ does not divide $3$. So $\Phi_3$ is irreducible.

Now the general prime. Expanding $\Phi_p(x+1)$ term by term is hopeless, so use a closed form instead.

**Problem 8(b).** Let $p$ be prime and $\Phi_p(x) = x^{p-1} + \cdots + x + 1$. Show that $\Phi_p$ is irreducible over $\mathbb{Q}$.

What you need:
- $(x-1)\,\Phi_p(x) = x^p - 1$ (multiply it out: everything telescopes).
- The binomial theorem: $(x+1)^p = \sum_{k=0}^{p} \binom{p}{k} x^k$.
- Eisenstein at $q$: $q$ divides every coefficient but the leading one, and $q^2$ does not divide the constant term, so the polynomial is irreducible over $\mathbb{Q}$.
- If $f(x+1)$ is irreducible, so is $f(x)$ (a factorisation of one shifts to a factorisation of the other).

Put $x+1$ into $(x-1)\,\Phi_p(x) = x^p - 1$. Write $\Phi_p(x+1)$ as a polynomial whose coefficients are binomial coefficients $\binom{p}{k}$.
