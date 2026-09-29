---
kind: lesson
title: check 7c-arbitrary-x
---
Yes, that is the question. Injective means $\sigma(\zeta_n)=\tau(\zeta_n)$ forces $\sigma=\tau$, and $\sigma=\tau$ means $\sigma(x)=\tau(x)$ for every $x\in K$.

The route is the one your specific $x$ already took, done for a general $x$. Every $x\in K=\mathbb{Q}(\zeta_n)$ can be written as
$$x=\sum_{j=0}^{m} a_j\,\zeta_n^{\,j},\qquad a_j\in\mathbb{Q}.$$
That is the 7(b) fact: $\zeta_n$ is algebraic, so $\mathbb{Q}(\zeta_n)=\mathbb{Q}[\zeta_n]$, polynomials in $\zeta_n$ with rational coefficients.

The one thing to do now: apply $\sigma$ to that sum and push it inside until only $\sigma(\zeta_n)$ is left. Your last line should be $\sigma(x)=\sum_j a_j\,\sigma(\zeta_n)^{j}$. Then the same line for $\tau$ finishes it, since $\sigma(\zeta_n)=\tau(\zeta_n)$.

What it uses:

- $\zeta_n=e^{2\pi i/n}$ and $K=\mathbb{Q}(\zeta_n)$.
- $\sigma,\tau$ are automorphisms of $K$ fixing $\mathbb{Q}$, with $\sigma(\zeta_n)=\tau(\zeta_n)$.
- $\sigma(a+b)=\sigma(a)+\sigma(b)$ (additive).
- $\sigma(ab)=\sigma(a)\sigma(b)$ (multiplicative).
- $\sigma(q)=q$ for $q\in\mathbb{Q}$ (fixes $\mathbb{Q}$).
- $\sigma(\zeta_n^{\,j})=\sigma(\zeta_n)^{j}$, which is multiplicativity used $j-1$ times.

So: for $x=\sum_{j=0}^{m} a_j\zeta_n^{\,j}$ with $a_j\in\mathbb{Q}$, show $\sigma(x)=\sum_j a_j\,\sigma(\zeta_n)^{j}$, naming which rule each line uses, and conclude $\sigma(x)=\tau(x)$.
