---
kind: correct
title: All three terms
---

$A(2) = E(2) + E(4) + E(6) = 5 + 1 + 1 = 7$. Correct, and the two ones are the right ones: $[4]$ alone has GCD $4$, $[6]$ alone has GCD $6$, and nothing else in the seven has GCD other than $2$.

One repair to your written definitions before it costs you later. You wrote $E(n)$ as "up to index $n$". There is no index in either of these — $n$ is a **value**, a candidate GCD, not a position in `nums`. What you actually used is the right one:

- $A(g)$ — strictly increasing subsequences whose every element is divisible by $g$.
- $E(g)$ — strictly increasing subsequences whose GCD is exactly $g$.

Every subsequence counted by $A(2)$ has *some* GCD, that GCD is divisible by $2$, and it lands in exactly one $E$ bucket. That is why the seven split cleanly into $5+1+1$ and why nothing is double-counted.

Now say which buckets in general.

## Your move

Take a different array: `nums = [1,2,3,4,5,6,7,8,9,10,11,12]`.

**Write $A(2)$ as a sum of $E$ values for this array.** Which $g$ appear in the sum?

You do not need to count anything — no enumeration, no numbers. I want the list of $g$'s and nothing else.
