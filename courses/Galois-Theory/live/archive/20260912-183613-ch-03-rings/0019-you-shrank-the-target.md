---
kind: wrong
title: You shrank the target. Both ends of 3.2 are fixed.
---

You wrote

$$\phi : R[x_1,\ldots,x_n] \longrightarrow \{\, a/b \in F(x_1,\ldots,x_n) \;:\; b = 1_F \,\}.$$

That is a real technique — cut the codomain down to the image and a non-surjective map becomes surjective. Two things are wrong with it here.

**It is not the image.** Take $R = \mathbb{Z}$, so $F = \mathbb{Q}$. The element $\tfrac{1}{2}x_1$ can be written with denominator $1_F$, so it is in your set. Nothing in $\mathbb{Z}[x_1,x_2]$ maps to it — the coefficient is not an integer. Your set is a copy of $F[x_1,\ldots,x_n]$, not of $R[x_1,\ldots,x_n]$.

**And the repair is pointed the wrong way.** 3.2 names *both* objects and asserts they are identified:

> the field of fractions of $R[x_1,\ldots,x_n]$ can be identified naturally with $F(x_1,\ldots,x_n)$.

$F(x_1,\ldots,x_n)$ is the target, all of it. It is not yours to trim — trimming it proves something else, and something much smaller: that a ring is isomorphic to a copy of itself. Nobody needed that.

So the end that has to move is the **domain**, and it has to become a field, because you established last card that a non-field is never isomorphic to a field.

**Your move.** You already wrote, on this same page, the construction that turns an integral domain into a field: $F = \{r_1/r_2 : r_1, r_2 \in R\}$. $R[x_1,\ldots,x_n]$ is also an integral domain. Apply that same construction to it, and write the resulting domain of $\phi$.
