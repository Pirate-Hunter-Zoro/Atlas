---
kind: lesson
title: check 11a-from-divides-to-power
---
You are one line from the first half. You already have $\operatorname{ord}(g) \mid n$, and that is all you need to know about $n$.

"Divides" is the fact to unpack. Write $m = \operatorname{ord}(g)$. Then $m \mid n$ means $n = mk$ for some integer $k \geq 1$. And $g^m = 1$ by the definition of order. Rewrite $g^n$ using those two facts and it collapses.

Your right-hand idea is a good start. Assuming $d+1$ elements satisfy $g^d = 1$ is the right setup. The subgroup is a detour, though: the root bound finishes it directly. That is the next card.

**Problem 11(a), first half.** Let $K$ be a field and $G \subseteq K^\times$ a finite subgroup of order $n$. Show that every $g \in G$ satisfies $g^n = 1$.

What it uses:

- $K^\times$: the nonzero elements of $K$, a group under multiplication.
- Order of $g$, written $\operatorname{ord}(g)$: the least $m \geq 1$ with $g^m = 1$.
- Lagrange's theorem: in a finite group, the order of each element divides the order of the group.
- $m \mid n$: there is an integer $k$ with $n = mk$.

With $m = \operatorname{ord}(g)$ and $n = mk$, show $g^n = 1$.
