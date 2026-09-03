---
kind: correct
title: Seven and five
---

All seven listed, and **7 divisible by 2, only 5 with GCD exactly 2**. Correct, and the two you added last — $[4]$ and $[6]$ — are the whole reason the distinction exists.

Two names so we can stop writing sentences:

- $A(g)$ — strictly increasing subsequences in which **every element is divisible by** $g$.
- $E(g)$ — strictly increasing subsequences whose **GCD is exactly** $g$.

You have just computed $A(2) = 7$ and $E(2) = 5$ for $\texttt{nums} = [2,4,6]$.

$A(g)$ is the cheap one: throw away every element not divisible by $g$ and count increasing subsequences of what is left. $E(g)$ is what the problem actually pays for. The solution is a way of getting the second from the first, and you have all the numbers you need to see it right now.

## Your move

**Write $A(2) = 7$ as a sum of $E$ values.**

Which $g$ appear in that sum, and what is each $E(g)$ for this `nums`? Three terms, and they add to seven.
