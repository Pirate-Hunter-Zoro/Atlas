---
kind: question
title: Homework — all twelve, in the sheet's order. 3.1 first.
---

Understood. Then nothing is chosen and nothing is dropped: twelve problems, worked in the sheet's order.

**3.1, 3.2, 3.3, 3.8, 3.10, 3.11, 3.12, 3.14, 3.15, 3.17, 3.25, 3.26.**

Skip any one and I leave it and move on, then bring it back at the end — a skipped problem is an empty solution region, not a deleted one. The $\mathbb{Z}_6$ / $\mathbb{Z}_5$ check from the last card is parked; it comes back when we reach 3.3.

---

**Problem 3.1.** *Suppose that $S$ is a set and $R$ is a ring. Let $R^S$ denote the set of all mappings from $S$ to $R$. Show that $R^S$ is a ring, under the operations defined by*
$$(f+g)(s) = f(s) + g(s), \qquad (fg)(s) = f(s)g(s).$$
*Show that if $S$ has more than one element then there exist non-zero elements $f$ and $g$ in $R^S$ for which $fg = 0$.*

- *Ring:* commutative under both operations, associative, distributive, with an identity $1 \neq 0$; abelian group under addition.
- *$R^S$:* its elements are **functions** $S \to R$. Two are equal iff they agree at every $s$.
- *Non-zero in $R^S$:* not the zero element of $R^S$ — so it takes a non-zero value somewhere, not everywhere.
- *Integral domain:* $rs = 0 \Rightarrow r = 0$ or $s = 0$. The second half exhibits $R^S$ failing this.

Not yet. One thing by hand first.

**Your move.** Let $R = \mathbb{Z}$ and $S = \{a, b\}$, and write a function as its pair of values. Take $f(a) = 1$, $f(b) = 0$ and $g(a) = 0$, $g(b) = 1$.

Compute $(fg)(a)$ and $(fg)(b)$, and then say what the zero element of $R^S$ actually is and whether $f$ equals it.
