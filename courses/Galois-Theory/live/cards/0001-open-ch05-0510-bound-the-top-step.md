---
kind: lesson
title: open ch05-0510-bound-the-top-step
---
Welcome back: one exercise is left in chapter 5, Garling 05.10, and the quintic half of it is one step from done. 05.4, 05.6, 05.7 and 05.8 are already typeset, so this sitting finishes 05.10 and then moves to the worksheet you uploaded.

**Exercise 05.10.** Show that $x^5 - 4x + 2$ and $x^4 - 4x + 2$ are both irreducible over $\mathbb{Q}(i)$.

Last time you set up the quintic. Let $\alpha$ be a root of $f(x) = x^5 - 4x + 2$. You found $[\mathbb{Q}(\alpha):\mathbb{Q}] = 5$ by Eisenstein at $p = 2$, and you drew both towers:

$$\mathbb{Q} \subset \mathbb{Q}(\alpha) \subset \mathbb{Q}(i,\alpha), \qquad \mathbb{Q} \subset \mathbb{Q}(i) \subset \mathbb{Q}(i,\alpha).$$

So $2$ and $5$ both divide $[\mathbb{Q}(i,\alpha):\mathbb{Q}]$, which makes it a multiple of $10$. What is missing is an upper bound of $10$. That comes from the top step of the second tower.

What you need:
- $[L:K]$ is the degree of $L$ over $K$: its dimension as a vector space over $K$.
- Tower law: for $K \subset M \subset L$, $[L:K] = [L:M]\,[M:K]$.
- $[K(\alpha):K]$ equals the degree of the minimal polynomial of $\alpha$ over $K$.
- The minimal polynomial of $\alpha$ over $K$ is the monic polynomial of least degree in $K[x]$ with $\alpha$ as a root. It divides every polynomial in $K[x]$ that has $\alpha$ as a root.
- $[\mathbb{Q}(i):\mathbb{Q}] = 2$, since $x^2 + 1$ is the minimal polynomial of $i$.

Here is the one question for this turn. Why is $[\mathbb{Q}(i,\alpha):\mathbb{Q}(i)] \le 5$, where $\alpha$ is a root of $x^5 - 4x + 2$?
