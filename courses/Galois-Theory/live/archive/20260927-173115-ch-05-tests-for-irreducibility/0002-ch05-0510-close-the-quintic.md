---
kind: lesson
title: ch05-0510-close-the-quintic
---
Right. The minimal polynomial of $\alpha$ over $\mathbb{Q}(i)$ is $x^5 - 4x + 2$ itself or a proper factor of it, so $[\mathbb{Q}(i,\alpha):\mathbb{Q}(i)] \le 5$. Your case split says exactly that: reducible gives less than $5$, irreducible gives $5$.

Now put the two facts together and the quintic is finished.

**Exercise 05.10, first half.** Show that $f(x) = x^5 - 4x + 2$ is irreducible over $\mathbb{Q}(i)$.

What you have:
- $\alpha$ is a root of $f$, and $[\mathbb{Q}(\alpha):\mathbb{Q}] = 5$ by Eisenstein at $p = 2$.
- $10$ divides $[\mathbb{Q}(i,\alpha):\mathbb{Q}]$, from the two towers $\mathbb{Q} \subset \mathbb{Q}(\alpha) \subset \mathbb{Q}(i,\alpha)$ and $\mathbb{Q} \subset \mathbb{Q}(i) \subset \mathbb{Q}(i,\alpha)$.
- $[\mathbb{Q}(i,\alpha):\mathbb{Q}(i)] \le 5$, which you just showed.
- $[\mathbb{Q}(i):\mathbb{Q}] = 2$, since $x^2 + 1$ is the minimal polynomial of $i$.
- Tower law: for $K \subset M \subset L$, $[L:K] = [L:M]\,[M:K]$.
- $[K(\alpha):K]$ is the degree of the minimal polynomial of $\alpha$ over $K$.

The question for this turn: using these, find $[\mathbb{Q}(i,\alpha):\mathbb{Q}(i)]$ exactly, and conclude that $x^5 - 4x + 2$ is irreducible over $\mathbb{Q}(i)$.
