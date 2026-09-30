---
kind: lesson
title: 7b-quotient-step
---
Not yet: "the previous argument works over the numerator and denominator" gets you $\sigma(p(\alpha))=\tau(p(\alpha))$ and $\sigma(q(\alpha))=\tau(q(\alpha))$. It does not get you $\sigma(x)=\tau(x)$. The step from the two pieces to the quotient is the one this card is about, and it is missing.

One fix first. You wrote $p,q\in K[\alpha_1,\dots,\alpha_n]$. It must be $p,q\in F[x_1,\dots,x_n]$. With coefficients in $K$, "fixes $F$" no longer applies to them, and the numerator argument breaks.

**Problem 7(b).** Let $K=F(\alpha_1,\dots,\alpha_n)$ and $\sigma,\tau\in\operatorname{Aut}(K/F)$ with $\sigma(\alpha_i)=\tau(\alpha_i)$ for every $i$. Prove $\sigma=\tau$.

What it uses:

- $\operatorname{Aut}(K/F)$: isomorphisms $K\to K$ fixing every $c\in F$.
- Multiplies: $\sigma(xy)=\sigma(x)\sigma(y)$.
- Inverses: $\sigma(y^{-1})=\sigma(y)^{-1}$ for $y\neq0$ (card 0007).
- Every $x\in K$ is $p(\alpha)/q(\alpha)$ with $p,q\in F[x_1,\dots,x_n]$ and $q(\alpha)\neq0$.
- Stage one, granted: $\sigma(p(\alpha))=\tau(p(\alpha))$ and $\sigma(q(\alpha))=\tau(q(\alpha))$.

Your move: take $x=p(\alpha)/q(\alpha)$ and grant stage one. Write $\sigma(x)=\tau(x)$ as one chain of equalities, each labelled multiplies, inverses or stage one. No "so".
