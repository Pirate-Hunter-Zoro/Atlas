---
kind: note
title: The value lives in $K$. The function lives in $K^K$.
---

The page shows exactly where you are lost, and it is one thing.

You wrote $(\Phi(f))(0) = 0 \in K^K$. That $0$ is **not** in $K^K$. It is in $K$.

- $\Phi(f)$ — on its own, with nothing fed to it — is the element of $K^K$. It is a *function*.
- $(\Phi(f))(0)$ — that function handed the input $0$ — is a single element of $K$.

$K = \mathbb{F}_2$ has two elements, so the function $\Phi(f)$ is completely described by two entries:

| $k$ | $(\Phi(f))(k)$ |
| --- | --- |
| $0$ | $0$ |
| $1$ | ? |

Your first line filled the top row and filled it correctly: $0^2 + 0 = 0$. Nothing else about that line was wrong except where you said the answer lived.

Arithmetic you may want, and it is not what this exercise is about: in $\mathbb{F}_2$, $1 \cdot 1 = 1$ and $1 + 1 = 0$.

**Your move.** Fill the bottom row: compute $(\Phi(f))(1) = 1^2 + 1$, as an element of $K$.

Once that row is filled you will be able to read the whole function off the table, and one half of 3.8 falls straight out of it.
