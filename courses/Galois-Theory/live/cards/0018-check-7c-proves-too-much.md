---
kind: lesson
title: check 7c-proves-too-much
---
Your chain proves too much, so one of its equalities is false. It never uses $\sigma(\zeta_n)=\zeta_n^{\,k}$: the letter $k$ does not appear. So it would work for *every* $\sigma$, including the identity, and there it gives nonsense.

Run it with $\sigma=\mathrm{id}$ (the identity map) and $d=2$. The left end is $\mathrm{id}(e^{2\pi i/2})=e^{\pi i}=-1$. Your right end is $1$. Yet $-1\neq 1$.

**Problem 7(c), first claim.** Let $K=\mathbb{Q}(\zeta_n)$ and $\sigma\in\operatorname{Aut}(K/\mathbb{Q})$ with $\sigma(\zeta_n)=\zeta_n^{\,k}$. Show $\gcd(k,n)=1$. Suppose instead $d=\gcd(k,n)>1$.

What it uses:

- $\zeta_n=e^{2\pi i/n}$: $\zeta_n^{\,m}=1$ exactly when $n\mid m$.
- $d$ divides both $k$ and $n$, so $k/d$ and $n/d$ are integers.
- $\sigma$ is multiplicative for **integer** powers: $\sigma(a^m)=\sigma(a)^m$, $m\in\mathbb{Z}$.
- $\sigma(1)=1$, and $\sigma$ is injective.
- Shown by you: $\zeta_n^{\,n/d}\neq 1$.

Your move, one thing only: in your chain with $\sigma=\mathrm{id}$, $d=2$, which single equality is false, and what rule does it pretend $\sigma$ (or exponents) obey?
