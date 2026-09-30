---
kind: lesson
title: check 7c-apply-sigma
---
Half of it is right: $\zeta_n^{\,n/d}=e^{2\pi i/d}\neq 1$, because $d>1$ puts the angle $2\pi/d$ strictly between $0$ and $2\pi$. That is the "why it is not $1$" part, done properly.

What is missing is $\sigma$ itself. You rewrote the input but never pushed $\sigma$ through it. The whole trick is that $\sigma$ sends this element *to* $1$.

**Problem 7(c).** Let $K=\mathbb{Q}(\zeta_n)$. Show every $\sigma\in\operatorname{Aut}(K/\mathbb{Q})$ has $\sigma(\zeta_n)=\zeta_n^{\,k}$ for some $k$ with $\gcd(k,n)=1$, and that $\sigma\mapsto k \bmod n$ is an injective group homomorphism $\operatorname{Aut}(K/\mathbb{Q})\hookrightarrow(\mathbb{Z}/n\mathbb{Z})^\times$. So $|\operatorname{Aut}(K/\mathbb{Q})|\le\varphi(n)$.

We are on the first claim. Suppose $\sigma(\zeta_n)=\zeta_n^{\,k}$ and $d=\gcd(k,n)>1$.

What it uses:

- $\zeta_n=e^{2\pi i/n}$, a primitive $n$-th root of unity: $\zeta_n^{\,m}=1$ exactly when $n\mid m$.
- $d=\gcd(k,n)$ divides both $k$ and $n$, so $k/d$ and $n/d$ are integers.
- $\sigma$ is multiplicative: $\sigma(a^m)=\sigma(a)^m$.
- $\sigma$ fixes $\mathbb{Q}$, so $\sigma(1)=1$.
- An isomorphism is injective: $\sigma(a)=\sigma(b)$ forces $a=b$.
- Already shown by you: $\zeta_n^{\,n/d}\neq 1$.

Your move: use multiplicativity and $\sigma(\zeta_n)=\zeta_n^{\,k}$ to compute $\sigma(\zeta_n^{\,n/d})$, one equality per line, until you reach $1$. Then use injectivity to conclude $\gcd(k,n)=1$.
