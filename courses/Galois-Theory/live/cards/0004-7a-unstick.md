---
kind: lesson
title: 7a-unstick
---
Run "multiplies" backwards: $\sigma(\alpha)^j=\sigma(\alpha^j)$. The power is not in your way; it is something $\sigma$ already swallows.

Your start is right: $f(\sigma(\alpha))=\sum_j c_j\,\sigma(\alpha)^j$. You are trying to pull $\sigma$ out. Do it term by term. Two facts do all of it:

- $\sigma(\alpha)^j=\sigma(\alpha^j)$, because $\sigma(ab)=\sigma(a)\sigma(b)$ applied $j$ times.
- $c_j=\sigma(c_j)$, because $c_j\in F$ and $\sigma$ fixes $F$.

Your worry about $\alpha\in K\setminus F$ is unfounded. Nothing above asks where $\alpha$ lives. "Fixes $F$" is spent on the coefficients $c_j$, never on $\alpha$.

**Problem 7(a).** Let $K/F$ be an extension and $\sigma\in\operatorname{Aut}(K/F)$. If $f\in F[x]$ and $f(\alpha)=0$ for some $\alpha\in K$, then $f(\sigma(\alpha))=0$.

What it uses:

- $\operatorname{Aut}(K/F)$: isomorphisms $\sigma:K\to K$ with $\sigma(c)=c$ for all $c\in F$.
- $f(x)=\sum_{j=0}^{n} c_j x^j$, every $c_j\in F$; you know $\sum_j c_j\alpha^j=0$.
- Adds: $\sigma(a+b)=\sigma(a)+\sigma(b)$.
- Multiplies: $\sigma(ab)=\sigma(a)\sigma(b)$.
- $\sigma(0)=0$.

Your move: rewrite one term $c_j\,\sigma(\alpha)^j$ as $\sigma(\text{something})$, then finish the chain from $f(\sigma(\alpha))$ down to $0$.
