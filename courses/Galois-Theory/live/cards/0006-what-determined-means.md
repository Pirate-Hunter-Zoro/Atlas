---
kind: lesson
title: what-determined-means
---
"Determined" means there is only one possibility. Yes, that is exactly what you are proving about $\sigma$ in 7(b).

Precisely: once you are told the $r$ values $\sigma(\alpha_1),\dots,\sigma(\alpha_r)$, the value $\sigma(x)$ is forced for every $x\in K$. You have no freedom left anywhere.

The same thing, said about two maps: if $\sigma,\tau\in\operatorname{Aut}(K/F)$ satisfy $\sigma(\alpha_i)=\tau(\alpha_i)$ for every $i$, then $\sigma(x)=\tau(x)$ for every $x\in K$, so $\sigma=\tau$.

It does not say such a $\sigma$ exists for every choice of values. That is a different question, and 7(b) does not ask it.

The small case shows what "forced" looks like. In $\mathbb{Q}(\sqrt2)$ you are told only where $\sqrt2$ goes. The rules of $\sigma$ then leave exactly one possible value for $\sigma(3+5\sqrt2)$.

What it uses:

- $\operatorname{Aut}(K/F)$: isomorphisms $\sigma:K\to K$ with $\sigma(c)=c$ for all $c\in F$.
- $\mathbb{Q}(\sqrt2)=\{a+b\sqrt2 : a,b\in\mathbb{Q}\}$.
- Adds: $\sigma(x+y)=\sigma(x)+\sigma(y)$.
- Multiplies: $\sigma(xy)=\sigma(x)\sigma(y)$.

Your move: take $\sigma\in\operatorname{Aut}(\mathbb{Q}(\sqrt2)/\mathbb{Q})$ with $\sigma(\sqrt2)=-\sqrt2$. Compute $\sigma(3+5\sqrt2)$, one equality per line, and label each line adds, multiplies or fixes $\mathbb{Q}$.
