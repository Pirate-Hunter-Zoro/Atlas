---
kind: wrong
title: "\"Will not happen\" is where it breaks — it does happen"
---

The break is this line:

> $R_{1}(x)R_{2}(x) = 1$ — this will not happen because no nonzero
> coefficients can multiply to $0$.

It does happen. $1 \cdot 1 = 1$, and you said so yourself one line above, so
your own two lines contradict each other: the first says the identity is a
unit, the second says nothing multiplies to $1$.

What the degree fact gives you is not *impossible*. It is a **restriction**:
$\deg(fg) = \deg f + \deg g$, and $fg = 1$, so $\deg f + \deg g = \deg 1 = 0$.
Two non-negative integers summing to $0$. That pins the shape of $f$ and $g$
completely — and then there is a second condition on top of it, which is where
your other claim, *the only unit is the identity*, goes wrong.

(Your $\mathbb{Z}_{4}$ line is also not right — one of $1, 2, 3$ is not a unit
there, and the interesting units are not among those three at all. It comes
back once this half is settled.)

---

**Your move.** One concrete instance, to kill *only the identity*. Take
$R = \mathbb{Z}$, an integral domain, so $R[x] = \mathbb{Z}[x]$.

Write down a unit of $\mathbb{Z}[x]$ that is **not** $1$, and give its inverse.
