---
kind: correct
title: Correct — the additive half is done. Now the product.
---

That is the proof. Every equality is an application of exactly one definition,
in the right order: $\Phi$ applied to the coefficientwise sum, then $\Phi$'s own
formula, then the identity in $K$, then back out again. And $k$ was arbitrary,
so the two functions agree everywhere and are equal in $K^K$.

The step you did not label — line 3 to line 4 — is **distributivity** in $K$,
$(a_i + b_i)k^i = a_ik^i + b_ik^i$ termwise, then commutativity and
associativity of $+$ to regroup the finite sum into two. Write the word next
time; it is the only axiom the additive half uses.

Now the other half, and this one has real arithmetic in it.

**Show that $\Phi(fg) = \Phi(f)\Phi(g)$.**

What it leans on:

- *Product in $K[x]$:* $fg$ is the polynomial whose $m$-th coefficient is
  $\sum_{i+j=m} a_ib_j$ — that is, $c_m = a_0b_m + a_1b_{m-1} + \cdots + a_mb_0$.
- *Product in $K^K$:* pointwise, $(uv)(k) = u(k)\,v(k)$.
- *$\Phi$:* $(\Phi(f))(k) = \sum_i a_ik^i$.
- *Equal functions:* they agree at every $k \in K$.

**Your move.** Same shape as what you just wrote. Fix an arbitrary $k \in K$,
expand $(\Phi(fg))(k)$ using the two definitions above, expand
$(\Phi(f)\Phi(g))(k)$ using its two, and get from one to the other.

If you want the arithmetic in your hand before the general case, do it first for
$f = a_0 + a_1x$ and $g = b_0 + b_1x$: multiply them out in $K[x]$, evaluate at
$k$, and multiply $(a_0 + a_1k)(b_0 + b_1k)$ out separately. Compare. Your
choice — the general statement is what is being asked for.
