---
kind: note
title: Both values right. But $\mathbb{F}_2[x] \not\subset K^K$.
---

Both values are correct, and the working you showed is the right working: $1 \cdot 1 + 1 = 1 + 1 = 0$. So the table is

| $k$ | $(\Phi(f))(k)$ |
| --- | --- |
| $0$ | $0$ |
| $1$ | $0$ |

and $\Phi(f)$ is the **zero function** — the additive identity of $K^K$.

One line on the page is false, and it is the first: you wrote $f = x^2 + x \in \mathbb{F}_2[x] \subset K^K$. That containment does not hold. A polynomial is not a function — you established that yourself earlier today — and $\Phi$ is a *map from* $K[x]$ *to* $K^K$, not an inclusion of one inside the other. The whole of 3.8 is a measurement of how badly $\Phi$ fails to be an inclusion.

And your own table is the evidence.

**Your move.** Name a polynomial $g \in \mathbb{F}_2[x]$, different from $f$, with $\Phi(g) = \Phi(f)$ — the same function, both values agreeing. The table you just filled hands you one immediately.
