---
kind: lesson
title: ch05-0510-the-quartic
---
Correct: the top step is $5$, so $x^5 - 4x + 2$ is irreducible over $\mathbb{Q}(i)$. Top $\le 5$ times $2$ must be a multiple of $10$, and only $5$ does it. The quintic half is done.

**Exercise 05.10, second half.** Show that $g(x) = x^4 - 4x + 2$ is irreducible over $\mathbb{Q}(i)$.

The same argument stalls here. Let $\beta$ be a root of $g$. Eisenstein at $2$ gives $[\mathbb{Q}(\beta):\mathbb{Q}] = 4$. The two towers now only say that $\mathrm{lcm}(2,4) = 4$ divides $[\mathbb{Q}(i,\beta):\mathbb{Q}]$. That degree is also at most $2 \cdot 4 = 8$. So it is $4$ or $8$, and you need to rule out $4$.

What you have:
- $\beta$ is a root of $g$, and $[\mathbb{Q}(\beta):\mathbb{Q}] = 4$ by Eisenstein at $p = 2$.
- $[\mathbb{Q}(i):\mathbb{Q}] = 2$, since $x^2 + 1$ is the minimal polynomial of $i$.
- Tower law: for $K \subset M \subset L$, $[L:K] = [L:M]\,[M:K]$.
- $[M:K] = 1$ exactly when $M = K$.

The question for this turn: suppose $[\mathbb{Q}(i,\beta):\mathbb{Q}] = 4$. What is $[\mathbb{Q}(i,\beta):\mathbb{Q}(\beta)]$, and what does that say about whether $i$ lies in $\mathbb{Q}(\beta)$?
