---
kind: note
title: Not by definition — those are two *different* definitions
---

Right question, and you are not underthinking it. But look at what you wrote:
the line

$$(\Phi(f+g))(k) = (\Phi(f))(k) + (\Phi(g))(k)$$

*is* the thing to be proved, at the point $k$. Writing it down asserts it.

It is not immediate, because the two sides are reached by two different
definitions and neither one mentions the other.

**Left side.** $f+g$ is a single polynomial in $K[x]$, whose $i$-th coefficient
is $a_i + b_i$. Apply the definition of $\Phi$ to *that* polynomial:
$$(\Phi(f+g))(k) = \sum_i (a_i + b_i)k^i.$$

**Right side.** $\Phi(f) + \Phi(g)$ is a sum in $K^K$, and addition there is
pointwise — the definition from 3.1. So
$$(\Phi(f) + \Phi(g))(k) = (\Phi(f))(k) + (\Phi(g))(k) = \sum_i a_ik^i + \sum_i b_ik^i.$$

So everything the proof has to do is:
$$\sum_i (a_i + b_i)k^i = \sum_i a_ik^i + \sum_i b_ik^i,$$
an identity in $K$. Small — one axiom of $K$ applied to each term, then
regrouping a finite sum. Small is not the same as free. That is the only place
in the additive half where anything is actually shown.

(If $f$ and $g$ have different degrees, run both sums to the same $n$ and pad
the shorter one with zero coefficients. That is what $f+g$ means anyway.)

**Your move.** Rewrite it as three lines: left side expanded by the definition
of $\Phi$; right side expanded by pointwise addition and then the definition of
$\Phi$; and the equality joining them. Name the axiom of $K$ that turns
$(a_i + b_i)k^i$ into $a_ik^i + b_ik^i$.
