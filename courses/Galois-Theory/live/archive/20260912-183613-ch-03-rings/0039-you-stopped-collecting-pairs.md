---
kind: wrong
title: $c_0$ and $c_1$ are right. You stopped collecting pairs after $c_1$.
---

$c_0 = 2$. Correct.

$c_1 = 3 + 8 = 11$. Correct, and it is the important one: you took **both**
ways of making an $x^1$, $a_0b_1$ and $a_1b_0$, and added them.

Then you stopped doing that.

**$c_2 = 10$.** List the pairs $(i,j)$ with $i + j = 2$, where $i$ ranges over
$f$'s indices $\{0,1\}$ and $j$ over $g$'s indices $\{0,1,2\}$. There are two of
them. You have used one.

**$c_3 = 0$.** Same question for $i + j = 3$. There is a pair. Find it, and
then $c_3$ is not $0$.

---

And the line above your bubble, which is the same error one level up:

$$(\Phi(fg))(k) = \Big(\Phi\big(\textstyle\sum (a_i b_i)x^i\big)\Big)(k)$$

$\sum (a_ib_i)x^i$ is **not** $fg$. Your own $c_1$ says so: you computed
$a_0b_1 + a_1b_0$, not $a_1b_1$. The coefficient of $x^m$ in $fg$ is
$c_m = \sum_{i+j=m} a_ib_j$ — the whole sum, not the single term with $i = j = m$.
Rewrite that first line with $c_m$ in it.

One notation point while you are there: in $K^K$ the product $\Phi(f)\Phi(g)$ is
the **pointwise** product, $(\Phi(f)\Phi(g))(k) = \Phi(f)(k)\cdot\Phi(g)(k)$ —
multiply the two values in $K$. It is not composition, so do not write $\circ$
for it; that would be a different claim.

**Your move.** Fix $c_2$ and $c_3$, then rewrite that first line.
