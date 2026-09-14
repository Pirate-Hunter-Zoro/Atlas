---
kind: correct
title: One GCD each
---

$\mathcal{E} = \{2,4,6,8,10,12\}$ — the multiples of $2$ up to the largest value. Correct, and you asked and answered the right question on the way there.

The line under it is the part that matters: **a subsequence has only one GCD.** That is the whole justification. Every subsequence counted by $A(2)$ has a GCD, that GCD is a multiple of $2$ and is at most $12$, and it puts the subsequence in exactly one $E$ bucket — so the buckets cover everything and overlap in nothing. Written out for any $g$:

$$A(g) \;=\; \sum_{\substack{m \,\equiv\, 0 \pmod g \\ m \,\le\, \max(\texttt{nums})}} E(m)$$

$A$ is the side you can compute directly. $E$ is the side the problem pays for. So the identity has to be turned around.

## Your move

Still `nums = [1,2,3,4,5,6,7,8,9,10,11,12]`.

**Write $E(4)$ with $E(4)$ alone on the left-hand side**, in terms of one $A$ value and some $E$ values.

Work out which $m$ belong in $E(4)$'s sum first, then move everything except $E(4)$ across.
