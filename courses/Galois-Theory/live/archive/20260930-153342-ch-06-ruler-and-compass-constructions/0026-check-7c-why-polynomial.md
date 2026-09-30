---
kind: lesson
title: check 7c-why-polynomial
---
Because I built it that way: $x = p(\zeta_n)$ where $p(t) = 3 - t + 5t^{2}$. That symbol is $\zeta_n$ ("zeta n"), the root of unity $e^{2\pi i/n}$, not a $C$. I picked $x$ as a polynomial in $\zeta_n$ on purpose, so you could watch $\sigma$ move through a sum, a product and a power.

The deeper fact is that every element of $K=\mathbb{Q}(\zeta_n)$ has this shape. $\mathbb{Q}(\zeta_n)$ is built from $\mathbb{Q}$ and $\zeta_n$ by $+,-,\times,\div$. Sums, differences and products of polynomials in $\zeta_n$ are again polynomials in $\zeta_n$. Quotients are too, because $\zeta_n$ is a root of $t^n-1$: that is the quotient step you already proved in 7(b). So a general element of $K$ looks just like $x$, only longer.

The exercise, restated in full:
$$x = 3-\zeta_n+5\zeta_n^{2}.$$

What it uses:

- $\zeta_n = e^{2\pi i/n}$, and $K=\mathbb{Q}(\zeta_n)$.
- Every element of $K$ is a polynomial in $\zeta_n$ with rational coefficients.
- $\sigma,\tau$ are automorphisms of $K$ fixing $\mathbb{Q}$: $\sigma(a+b)=\sigma(a)+\sigma(b)$, $\sigma(ab)=\sigma(a)\sigma(b)$, and $\sigma(q)=q$ for $q\in\mathbb{Q}$.
- You have shown $\sigma(\zeta_n)=\tau(\zeta_n)=\zeta_n^{\,k}$.
- 7(b): an automorphism of $F(\alpha_1,\dots,\alpha_r)$ fixing $F$ is determined by $\sigma(\alpha_1),\dots,\sigma(\alpha_r)$.

So: for $x=3-\zeta_n+5\zeta_n^{2}$, compute $\sigma(x)$ and $\tau(x)$ with the rule named on each line, show they are equal, and name the fact from the list that makes $\sigma=\tau$ on all of $K$.
