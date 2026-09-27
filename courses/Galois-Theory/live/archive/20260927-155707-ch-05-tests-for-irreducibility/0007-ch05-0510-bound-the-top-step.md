---
kind: lesson
title: ch05-0510-bound-the-top-step
---
Yes, that is the right track. Towers give the bound, but you need one more fact about the step from $\mathbb{Q}(i)$ up to $\mathbb{Q}(i,\alpha)$.

Your two towers already give the divisibility. The first says $5 \mid [\mathbb{Q}(i,\alpha):\mathbb{Q}]$. The second says $2 \mid [\mathbb{Q}(i,\alpha):\mathbb{Q}]$. So the degree is a multiple of $10$.

For the bound, use the second tower:
$$[\mathbb{Q}(i,\alpha):\mathbb{Q}] = [\mathbb{Q}(i,\alpha):\mathbb{Q}(i)]\cdot 2.$$
So everything rests on showing $[\mathbb{Q}(i,\alpha):\mathbb{Q}(i)] \le 5$.

What you need:
- $[L:K]$: the dimension of $L$ as a vector space over $K$.
- Tower law: for $K \subseteq L \subseteq M$, $[M:K] = [M:L]\,[L:K]$.
- $[K(\alpha):K]$ equals the degree of the minimal polynomial of $\alpha$ over $K$.
- The minimal polynomial of $\alpha$ over $K$ divides every polynomial in $K[x]$ that has $\alpha$ as a root.
- $\mathbb{Q}(i)(\alpha) = \mathbb{Q}(i,\alpha)$.

**The check.** The polynomial $x^5 - 4x + 2$ has rational coefficients, so it also lies in $\mathbb{Q}(i)[x]$, and $\alpha$ is a root of it. Why does that force $[\mathbb{Q}(i,\alpha):\mathbb{Q}(i)] \le 5$?
