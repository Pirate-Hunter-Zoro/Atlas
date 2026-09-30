---
kind: lesson
title: check 7c-agree-everywhere
---
Your computation is right: $k\equiv k'\pmod n$ gives $\sigma(\zeta_n)=\tau(\zeta_n)$. The last line is the gap. Agreeing at one point does not yet say $\sigma$ and $\tau$ agree on all of $K$, and "clearly" is carrying that whole step.

One small fix first: $n$ is fixed throughout, so drop the $\forall n$. You mean just $\sigma(\zeta_n)=\tau(\zeta_n)$.

Here is a concrete element of $K$ to test it on:
$$x = 3-\zeta_n+5\zeta_n^{2}.$$

What it uses:

- $K=\mathbb{Q}(\zeta_n)$, and every element of $K$ is a polynomial in $\zeta_n$ with rational coefficients.
- $\sigma,\tau$ are automorphisms of $K$ fixing $\mathbb{Q}$: they respect $+$ and $\times$, and $\sigma(q)=q$ for $q\in\mathbb{Q}$.
- You have shown $\sigma(\zeta_n)=\tau(\zeta_n)=\zeta_n^{\,k}$.
- 7(b): an automorphism of $F(\alpha_1,\dots,\alpha_r)$ fixing $F$ is determined by $\sigma(\alpha_1),\dots,\sigma(\alpha_r)$.

Your move: compute $\sigma(x)$ and $\tau(x)$ line by line, naming the rule used on each line. Then say which fact in the list turns this one example into $\sigma=\tau$ on all of $K$.

So: for $x=3-\zeta_n+5\zeta_n^{2}$, show $\sigma(x)=\tau(x)$ with a rule named on each line, and name the fact that makes $\sigma=\tau$ everywhere.
