---
kind: lesson
title: check 7c-general-gcd
---
Right, and this time the reason is complete. $\sigma(\zeta_6^{\,3})=1=\sigma(1)$, so injectivity would force $\zeta_6^{\,3}=1$. But $\zeta_6^{\,3}=e^{\pi i}=-1$. So no $\sigma$ sends $\zeta_6$ to $\zeta_6^{\,2}$.

Now the same trick for any $n$ and any bad $k$.

**Problem 7(c).** Let $K=\mathbb{Q}(\zeta_n)$. Show every $\sigma\in\operatorname{Aut}(K/\mathbb{Q})$ has $\sigma(\zeta_n)=\zeta_n^{\,k}$ for some $k$ with $\gcd(k,n)=1$, and that $\sigma\mapsto k \bmod n$ is an injective group homomorphism $\operatorname{Aut}(K/\mathbb{Q})\hookrightarrow(\mathbb{Z}/n\mathbb{Z})^\times$. So $|\operatorname{Aut}(K/\mathbb{Q})|\le\varphi(n)$.

Suppose $\sigma(\zeta_n)=\zeta_n^{\,k}$ and $d=\gcd(k,n)>1$. For $n=6$, $k=2$ you used the exponent $3$. That is $n/d=6/2$.

What it uses:

- $\zeta_n=e^{2\pi i/n}$, a primitive $n$-th root of unity: $\zeta_n^{\,m}=1$ exactly when $n\mid m$.
- $d=\gcd(k,n)$ divides both $k$ and $n$, so $k/d$ and $n/d$ are integers.
- $\sigma$ is multiplicative: $\sigma(a^m)=\sigma(a)^m$.
- $\sigma$ fixes $\mathbb{Q}$, so $\sigma(1)=1$.
- An isomorphism is injective: $\sigma(a)=\sigma(b)$ forces $a=b$.

Your move: with $d=\gcd(k,n)>1$, compute $\sigma(\zeta_n^{\,n/d})$, and say why $\zeta_n^{\,n/d}\neq 1$. Then conclude that $\gcd(k,n)=1$.
