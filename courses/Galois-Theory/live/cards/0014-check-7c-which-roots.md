---
kind: lesson
title: check 7c-which-roots
---
7(b) is agreed. Your chain is right, and it is now in the write-up, typeset.

One line was missing, and the file now carries it. Your second equality, $\sigma(q(\alpha)^{-1})=\tau(q(\alpha)^{-1})$, is not a "polynomial reason": $q(\alpha)^{-1}$ is not a polynomial in the $\alpha_i$. It needs inverses first: $\sigma(q^{-1})=\sigma(q)^{-1}=\tau(q)^{-1}=\tau(q^{-1})$, using inverses, then stage one, then inverses. The write-up says exactly that.

**Problem 7(c).** Let $K=\mathbb{Q}(\zeta_n)$. Show every $\sigma\in\operatorname{Aut}(K/\mathbb{Q})$ has $\sigma(\zeta_n)=\zeta_n^{\,k}$ for some $k$ with $\gcd(k,n)=1$, and that $\sigma\mapsto k \bmod n$ is an injective group homomorphism $\operatorname{Aut}(K/\mathbb{Q})\hookrightarrow(\mathbb{Z}/n\mathbb{Z})^\times$. So $|\operatorname{Aut}(K/\mathbb{Q})|\le\varphi(n)$.

First check, with $n=4$, where $\zeta_4=i$. By 7(a), $\sigma(i)$ is a root of $x^4-1$, so it is one of $1,\ i,\ -1,\ -i$, that is $i^k$ for $k=0,1,2,3$.

What it uses:

- $\zeta_n=e^{2\pi i/n}$, a primitive $n$-th root of unity: its powers $\zeta_n^0,\dots,\zeta_n^{n-1}$ are all the roots of $x^n-1$.
- $\operatorname{Aut}(K/\mathbb{Q})$: isomorphisms $K\to K$ fixing every rational number.
- 7(a): $\sigma$ sends a root of $f\in\mathbb{Q}[x]$ to a root of $f$.
- An isomorphism is injective: $\sigma(a)=\sigma(b)$ forces $a=b$.

Your move: of $1,\ i,\ -1,\ -i$, which can $\sigma(i)$ never be? Name them, and say in one line why each is ruled out.
