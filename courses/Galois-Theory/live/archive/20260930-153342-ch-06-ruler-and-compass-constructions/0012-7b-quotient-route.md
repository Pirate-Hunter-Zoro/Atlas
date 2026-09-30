---
kind: lesson
title: 7b-quotient-route
---
You never ask whether $x$ is transcendental. You write $x$ as a quotient of two polynomials in the $\alpha_i$, and that works for every $x\in K$ at once.

Here is why. The set of all $p(\alpha_1,\dots,\alpha_n)/q(\alpha_1,\dots,\alpha_n)$, with $p,q\in F[x_1,\dots,x_n]$ and $q(\alpha)\neq0$, is a field. It contains $F$ and every $\alpha_i$. So it is all of $F(\alpha_1,\dots,\alpha_n)$, the smallest such field. Your $1/t$ is just $p=1$, $q=t$.

So the proof has two stages. First, $\sigma$ and $\tau$ agree on every polynomial $p(\alpha)$: your adds, multiplies, fixes-$F$ chain. Second, they agree on $p(\alpha)/q(\alpha)$, using $\sigma(y^{-1})=\sigma(y)^{-1}$ from card 0007.

Your check is right: $t f(t)-1$ is a polynomial over $F$ with root $t$. Two fixes. Write $f\in F[x]$, not $K[x]$: over $K$ the constant $f=1/t$ works. And say why $t f(t)-1$ is nonzero: its constant term is $-1$.

**Problem 7(b).** Let $K=F(\alpha_1,\dots,\alpha_n)$ and $\sigma,\tau\in\operatorname{Aut}(K/F)$ with $\sigma(\alpha_i)=\tau(\alpha_i)$ for every $i$. Prove $\sigma=\tau$.

What it uses:

- $\operatorname{Aut}(K/F)$: isomorphisms $K\to K$ fixing every $c\in F$.
- Adds: $\sigma(x+y)=\sigma(x)+\sigma(y)$.
- Multiplies: $\sigma(xy)=\sigma(x)\sigma(y)$.
- Inverses: $\sigma(y^{-1})=\sigma(y)^{-1}$ for $y\neq0$ (card 0007).
- Every $x\in K$ is $p(\alpha)/q(\alpha)$ with $p,q$ polynomials over $F$ and $q(\alpha)\neq0$.
- $p(\alpha)=\sum c_{i_1\cdots i_n}\alpha_1^{i_1}\cdots\alpha_n^{i_n}$ with each $c\in F$.

Your move: let $\sigma(\alpha_i)=\tau(\alpha_i)$ for all $i$, and take $x=p(\alpha)/q(\alpha)\in K$. Prove $\sigma(x)=\tau(x)$ as one written chain, each equality labelled adds, multiplies, inverses, fixes $F$ or hypothesis. No "clearly".
