---
kind: note
title: What $x_1,\ldots,x_n$ is, and one of each creature
---

Fair question. The notation is doing nothing clever.

**$x_1, \ldots, x_n$ is just $n$ different variables.** The subscript is a label — not a power, not a value. $n$ is any fixed positive integer, and nothing in 3.2 depends on which one, so take $n = 2$ for the whole problem and write $x_1, x_2$. Read them as $x$ and $y$ if that is easier.

For concrete creatures, take $R = \mathbb{Z}$. Then $F = \mathbb{Q}$.

**The left-hand one: $\mathbb{Z}[x_1, x_2]$.** Polynomials in two variables with integer coefficients. For instance

$$3x_1^2x_2 - 5x_2 + 7.$$

Your brace is right — every element is a polynomial. Note what that *excludes*: $\tfrac{1}{2}x_1$ is not in it, because $\tfrac{1}{2} \notin \mathbb{Z}$.

**The right-hand one: $\mathbb{Q}(x_1, x_2)$.** Quotients of polynomials with rational coefficients. For instance

$$\frac{x_1^2 + \tfrac{1}{2}x_2}{x_1x_2 - 3}.$$

Your other brace is right too, and here is the equivalence actually biting:

$$\frac{x_1x_2}{x_1} = \frac{x_2}{1}, \qquad \text{because } x_1x_2 \cdot 1 = x_1 \cdot x_2.$$

One element, two names. That is what "equivalence class $a/b$" buys you.

**Your move.** Three expressions. For each one, say whether it lies in $\mathbb{Z}[x_1,x_2]$, in $\mathbb{Q}(x_1,x_2)$, or in both:

1. $4x_1^3 - x_1x_2 + 2$
2. $\tfrac{1}{3}x_2 + 5$
3. $\dfrac{1}{x_1 + x_2}$
