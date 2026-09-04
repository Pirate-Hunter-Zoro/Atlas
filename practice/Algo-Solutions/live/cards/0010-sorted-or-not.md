---
kind: note
title: No — but something on that page does
---

Your bubble at the bottom: *relies on `nums` being sorted*. Answering that before anything else on the page.

**The identity does not.** $A(g) = \sum_{g \mid m,\; m \le \max} E(m)$ is pure arithmetic: every subsequence has exactly one GCD, that GCD is a multiple of $g$ whenever all its elements are, and it is at most the smallest element it came from. Not one word of that mentions position, so it holds for `nums` in any order.

**What relies on sorted is your numbers.** On $[1,\dots,12]$ you read $A(12)=1$ and $A(6)=3$ straight off, because when the multiples of $g$ already sit in increasing order *every* non-empty subset of them is an increasing subsequence — so $A(g) = 2^k - 1$ for $k$ multiples. That shortcut is the thing sortedness bought, and the real `nums` will not pay for it.

## Your move

`nums = [12, 6, 3, 2, 1, 4, 5, 7, 8, 9, 10, 11]` — the same twelve values, `12` now first and `6` second.

**Write $A(6)$ and $E(6)$ for this array.** Two numbers, and one line saying which subsequences of the multiples of $6$ you kept and which you threw out.

- *$A(g)$:* increasing subsequences (strictly, non-empty) of `nums` with every element divisible by $g$.
- *$E(g)$:* those whose GCD is exactly $g$.
- *increasing subsequence:* elements taken left to right in `nums`, each strictly greater than the last.
- Multiples of $6$ in range: $6$ and $12$.
