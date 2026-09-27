---
kind: lesson
title: ch05-0510-tower-degrees
---
Agreed. 05.8 and 05.4 are being typeset in your words now, and the next card will say what the file says.

**The exercise (05.10).** Show that $x^5 - 4x + 2$ and $x^4 - 4x + 2$ are irreducible over $\mathbb{Q}(i)$.

Both are irreducible over $\mathbb{Q}$ by Eisenstein at $p = 2$. The work is getting from $\mathbb{Q}$ up to $\mathbb{Q}(i)$, and the tool is degrees.

What you need:
- $[L : K]$: the dimension of $L$ as a vector space over $K$.
- Tower law: for $K \subseteq L \subseteq M$, $[M : K] = [M : L]\,[L : K]$.
- If $\alpha$ is a root of an irreducible $f \in K[x]$ of degree $d$, then $[K(\alpha) : K] = d$.
- $f$ is irreducible over $K$ exactly when $[K(\alpha) : K] = \deg f$ for a root $\alpha$.
- $[\mathbb{Q}(i) : \mathbb{Q}] = 2$, since $x^2 + 1$ is irreducible over $\mathbb{Q}$.
- $\mathbb{Q}(i)(\alpha) = \mathbb{Q}(i, \alpha)$, which contains both $\mathbb{Q}(i)$ and $\mathbb{Q}(\alpha)$.

**The check.** Let $\alpha$ be a root of $x^5 - 4x + 2$, so $[\mathbb{Q}(\alpha) : \mathbb{Q}] = 5$. Which numbers must divide $[\mathbb{Q}(i, \alpha) : \mathbb{Q}]$, and why is it at most $10$?

Then what is $[\mathbb{Q}(i, \alpha) : \mathbb{Q}]$, and what is $[\mathbb{Q}(i, \alpha) : \mathbb{Q}(i)]$?
