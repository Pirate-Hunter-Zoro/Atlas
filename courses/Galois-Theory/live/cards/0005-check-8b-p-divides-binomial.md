---
kind: lesson
title: check 8b-p-divides-binomial
---
Your expansion is right: leading coefficient $1$, constant term $\binom{p}{1} = p$, and the index shift $x^{i-1}$ is correct. One label is wrong. After dividing by $x$ you wrote $\Phi_p(x)$ on the left. It is $\Phi_p(x+1)$, because you substituted $x+1$ on the left as well. The polynomial Eisenstein is applied to is $\Phi_p(x+1)$.

"Irreducible by Eisenstein" still skips the actual check. The prime is $p$. The constant term is $p$, so $p^2$ does not divide it. What remains is the middle coefficients.

For $p = 5$: $\binom{5}{1}, \binom{5}{2}, \binom{5}{3}, \binom{5}{4} = 5, 10, 10, 5$. All are divisible by $5$. For $p=4$, which is not prime, $\binom{4}{2} = 6$ is not divisible by $4$.

**Problem 8(b).** Let $p$ be prime and $\Phi_p(x) = x^{p-1} + \cdots + x + 1$. Show that $\Phi_p$ is irreducible over $\mathbb{Q}$.

What you need:
- Your line: $\Phi_p(x+1) = \sum_{i=1}^{p} \binom{p}{i} x^{i-1}$.
- $\binom{p}{k} = \dfrac{p!}{k!\,(p-k)!}$, an integer.
- Eisenstein at $q$: $q$ divides every coefficient except the leading one, and $q^2$ does not divide the constant term. Then the polynomial is irreducible over $\mathbb{Q}$.
- If $f(x+1)$ is irreducible, so is $f(x)$.

Show that $p$ divides $\binom{p}{k}$ for every $0 < k < p$, and say where you used that $p$ is prime.
