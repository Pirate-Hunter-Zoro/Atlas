---
kind: lesson
title: 7b-inverses
---
Right: $\sigma(3+5\sqrt2)=3-5\sqrt2$, and nothing else was possible. There is no question on the page, so this is grading only.

Your first line did three things at once. Spelled out:

$$\sigma(3+5\sqrt2)=\sigma(3)+\sigma(5\sqrt2)\ \text{(adds)}=\sigma(3)+\sigma(5)\,\sigma(\sqrt2)\ \text{(multiplies)}=3+5\,\sigma(\sqrt2)\ \text{(fixes }\mathbb{Q}\text{)}.$$

That chain is the whole idea of 7(b). Once $\sigma(\sqrt2)$ is known, every step is forced.

**Problem 7(b).** Let $K/F$ be an extension and $\sigma\in\operatorname{Aut}(K/F)$. If $K=F(\alpha_1,\dots,\alpha_r)$, then $\sigma$ is determined by $\sigma(\alpha_1),\dots,\sigma(\alpha_r)$.

One gap remains before the general case. A general $F(\alpha_1,\dots,\alpha_r)$ contains quotients, such as $1/(1+\sqrt2)$. Adds and multiplies alone do not say where a quotient goes.

What it uses:

- $\operatorname{Aut}(K/F)$: isomorphisms $\sigma:K\to K$ with $\sigma(c)=c$ for all $c\in F$.
- Adds: $\sigma(x+y)=\sigma(x)+\sigma(y)$.
- Multiplies: $\sigma(xy)=\sigma(x)\sigma(y)$.
- $\sigma(1)=1$, since $1\in F$.
- Determined: $\sigma(\alpha_i)=\tau(\alpha_i)$ for all $i$ forces $\sigma=\tau$.

Your move: let $y\in K$ with $y\neq0$. Show $\sigma(y^{-1})=\sigma(y)^{-1}$, one equality per line, each labelled.
