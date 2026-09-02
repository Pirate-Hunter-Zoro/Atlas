---
kind: note
title: Arithmetic settled. The formula is in the margin, not in the proof.
---

$c_2 = 10 + 12 = 22$ and $c_3 = 15$. Both right, and $\sum_{i+j=m} a_ib_j$ is
written out correctly. The rung is done — the mechanics of multiplying in $K[x]$
are yours.

Now look at where you put it. The arrow runs from $c_m = \sum_{i+j=m} a_ib_j$
into the **bubble** — into the $2+3x$ example. The line above the bubble, the one
that is actually your proof, is untouched:

$$(\Phi(fg))(k) = \Big(\Phi\big(\textstyle\sum (a_i b_i)x^i\big)\Big)(k)$$

Those two statements contradict each other. Your formula says the coefficient of
$x^m$ in $fg$ is a sum over every pair with $i+j=m$. Your proof line says it is
the single product $a_mb_m$. In the example you just did, the first gives
$c_2 = 22$ and the second gives $a_2b_2$, which is $0 \cdot 5 = 0$. They cannot
both be $fg$, and the one in the margin is the correct one.

So the substitution that belongs on that line is $fg = \sum_m c_m x^m$ — the
thing you are applying $\Phi$ to is $fg$, and *that* is what $fg$ is.

**Your move.** Cross out that line and write it again, with $c_m$ in it. Then
carry on: apply $\Phi$ and evaluate at $k$.
