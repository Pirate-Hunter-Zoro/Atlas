---
kind: correct
title: Two, and the pair is gone
---

$A(6) = 2$ from $[12]$ and $[6]$, $E(6) = 2 - E(12) = 1$ from $[6]$. Correct, and the step that carried it is the one that mattered: $[6,12]$ is not a subsequence of that array at all, so $A$ moved while the identity did not.

Owed from before, since your bubble jumped the queue: your previous page was right too — $E(12)=1$, $E(11)=1$, $E(6)=A(6)-E(12)=2$, and the inverted identity you wrote for it. The fill order is settled. $g$ descending, largest first, subtracting nothing.

So $E(g)$ is finished, and everything now hangs on the one quantity you have been reading off by eye: $A(g)$.

## Your move

Fix $g = 2$ and suppose the multiples of $2$ in `nums`, **kept in the order they appear**, are

$$[\,6,\;2,\;8,\;4\,].$$

$A(2)$ is the number of strictly increasing subsequences of that list. It is not $2^4 - 1$, because most subsets are not increasing.

**Count them by position.** For each of the four entries, write how many increasing subsequences *end* at that entry — four numbers, left to right — and then their sum.

- *increasing subsequence:* entries taken left to right, each strictly greater than the last; non-empty.
- *ends at entry $i$:* $i$ is its last entry, so every other entry it uses sits to the left of $i$ and is smaller.
- A single entry counts as a subsequence ending at itself.
