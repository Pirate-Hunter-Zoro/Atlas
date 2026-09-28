---
kind: lesson
title: check 7b-sqrt2
---
Problem 7(a) is right, and it is now yours. There is no question on the page, so this is grading only.

Every line holds. The step $c_j\sigma(\alpha^j)=\sigma(c_j\alpha^j)$ is where "fixes $F$" gets spent, on $c_j$, exactly as it should. Your $\sigma(0)=0$ "since $0\in F$" is a valid reason too: $\sigma$ fixes all of $F$, and $0$ is in it.

Next is 7(b).

**Problem 7(b).** Let $K/F$ be an extension and $\sigma\in\operatorname{Aut}(K/F)$. If $K=F(\alpha_1,\dots,\alpha_r)$, then $\sigma$ is determined by $\sigma(\alpha_1),\dots,\sigma(\alpha_r)$.

One small case first. Take $F=\mathbb{Q}$, $K=\mathbb{Q}(\sqrt2)$, and suppose $\sigma(\sqrt2)=-\sqrt2$.

What it uses:

- $\operatorname{Aut}(K/F)$: isomorphisms $\sigma:K\to K$ with $\sigma(c)=c$ for all $c\in F$.
- $\mathbb{Q}(\sqrt2)=\{a+b\sqrt2 : a,b\in\mathbb{Q}\}$.
- Adds: $\sigma(x+y)=\sigma(x)+\sigma(y)$.
- Multiplies: $\sigma(xy)=\sigma(x)\sigma(y)$.

Your move: compute $\sigma(3+5\sqrt2)$, one equality per line, and label each line adds, multiplies or fixes $\mathbb{Q}$.
