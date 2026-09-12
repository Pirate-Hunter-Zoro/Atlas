---
kind: note
title: Nearly. Classes of $2$-tuples, not $2$-tuples.
---

Answering the pencilled question: **yes, that is the right shape**, with one correction to the word.

An element of $F(x_1,\ldots,x_n)$ is not a $2$-tuple of polynomials. It is an *equivalence class* of them. Concretely: take ordered pairs $(a,b)$ with $a,b \in F[x_1,\ldots,x_n]$ and $b \neq 0$, and declare

$$(a,b) \sim (c,d) \iff ad = bc.$$

An element of $F(x_1,\ldots,x_n)$ is one whole class under $\sim$, and $a/b$ is just how that class is written.

Why the distinction is not pedantry — you met it already, at $4/2 = 2/1$. Here it is with polynomials, $R = \mathbb{Z}$, $n = 2$:

$$(x_1,\; x_2) \quad\text{and}\quad (x_1^2,\; x_1x_2)$$

are different pairs, and $x_1 \cdot x_1 x_2 = x_2 \cdot x_1^2$, so they are the **same element**. One element, infinitely many pairs naming it. A map defined on pairs has to agree on all of them or it is not defined on $F(x_1,\ldots,x_n)$ at all.

And the embedding you have been using reads, in this language: the polynomial $p$ goes to the class of $(p,\, 1_F)$. Polynomials in, classes of pairs out — so the two ends of your arrow are objects of different kinds, which is exactly the thing you were poking at with the question mark.

**Your move.** For $\phi$ to be a bijection, an element of its domain must be the same kind of object as an element of its target: a class of pairs of polynomials. Say which ring those polynomials must come from — and then write the domain that results.
