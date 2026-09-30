---
kind: lesson
title: check 7c-coprime-n6
---
Right: $\sigma(i)$ can be neither $1$ nor $-1$. Your reason needs one more link, and it is injectivity.

"$\sigma$ fixes $\mathbb{Q}$" says $\sigma(1)=1$ and $\sigma(-1)=-1$. It says nothing yet about $i$. The contradiction comes next: if $\sigma(i)=1=\sigma(1)$, injectivity forces $i=1$. The same for $-1$. So $\sigma(i)\in\{i,-i\}$, which is $k=1$ or $k=3$, exactly the $k$ coprime to $4$.

**Problem 7(c).** Let $K=\mathbb{Q}(\zeta_n)$. Show every $\sigma\in\operatorname{Aut}(K/\mathbb{Q})$ has $\sigma(\zeta_n)=\zeta_n^{\,k}$ for some $k$ with $\gcd(k,n)=1$, and that $\sigma\mapsto k \bmod n$ is an injective group homomorphism $\operatorname{Aut}(K/\mathbb{Q})\hookrightarrow(\mathbb{Z}/n\mathbb{Z})^\times$. So $|\operatorname{Aut}(K/\mathbb{Q})|\le\varphi(n)$.

Next check, with $n=6$. Suppose some $\sigma$ had $\sigma(\zeta_6)=\zeta_6^{\,2}$. Here $\gcd(2,6)=2$, so this should be impossible.

What it uses:

- $\zeta_6=e^{2\pi i/6}$, a primitive $6$-th root of unity: $\zeta_6^m=1$ exactly when $6\mid m$.
- $\sigma$ is multiplicative: $\sigma(a^m)=\sigma(a)^m$.
- $\sigma$ fixes $\mathbb{Q}$, so $\sigma(1)=1$.
- An isomorphism is injective: $\sigma(a)=\sigma(b)$ forces $a=b$.

Your move: if $\sigma(\zeta_6)=\zeta_6^{\,2}$, compute $\sigma(\zeta_6^{\,3})$. Then say in one line why that value is impossible.
