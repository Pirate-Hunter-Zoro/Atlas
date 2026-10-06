---
kind: lesson
title: check 11a-roots-of-unity
---
Problem 11 is next, then Problem 12. Both are already on the worksheet you uploaded, page 2, so no new sheet is needed.

The plan: 11(a), 11(b), 11(c) in order, then 12(a) to 12(d). Problem 11 proves that $\mathbb{F}_q^\times$ is cyclic. Problem 12 builds $\mathbb{F}_q$ as a splitting field and finds its automorphism group. 11(b) is the real work. 11(a) is the two facts it runs on.

**Problem 11(a).** Let $K$ be a field and let $G \subseteq K^\times$ be a finite subgroup of order $n$. Show that every element of $G$ is an $n$-th root of unity, and that for each $d \geq 1$ there are at most $d$ elements $g \in K$ with $g^d = 1$.

What the problem uses:

- $K^\times$: the nonzero elements of $K$, a group under multiplication.
- $n$-th root of unity: an element $g$ with $g^n = 1$.
- Order of an element $g$: the least $m \geq 1$ with $g^m = 1$.
- Lagrange's theorem: in a finite group, the order of each element divides the order of the group.
- Root bound: a nonzero polynomial of degree $d$ over a field has at most $d$ roots in that field.

The second half asks about all of $K$, not only $G$.

Prove 11(a): every $g \in G$ satisfies $g^n = 1$, and for each $d \geq 1$ at most $d$ elements $g \in K$ satisfy $g^d = 1$.
