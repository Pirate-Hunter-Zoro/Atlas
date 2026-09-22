---
kind: question
title: ch04-2-products-span
---
Problem 04.2 is the one empty solution slot left in the ch04 write-up, so that is this sitting's work. If 04.2 is the problem you meant to skip, say so and I will move to the worksheet instead. You are not answering it yet.

**04.2.** Suppose that $L/K$ is a field extension, and that $K_1$ and $K_2$ are two intermediate fields such that $L = K(K_1, K_2)$. Show that
$$[L:K] \;\le\; [K_1:K]\,[K_2:K].$$

The whole proof is one spanning set. If $e_1,\dots,e_m$ is a $K$-basis of $K_1$ and $f_1,\dots,f_n$ is a $K$-basis of $K_2$, then the $mn$ products $e_i f_j$ are the candidates for spanning $L$ over $K$. Everything hangs on showing their $K$-span really is all of $L$.

Start in one concrete case. Take $K = \mathbb{Q}$, $K_1 = \mathbb{Q}(\sqrt{2})$, $K_2 = \mathbb{Q}(\sqrt{3})$, and $L = \mathbb{Q}(\sqrt{2},\sqrt{3})$. The bases are $\{1,\sqrt{2}\}$ and $\{1,\sqrt{3}\}$, so the four products are $1$, $\sqrt{2}$, $\sqrt{3}$, $\sqrt{6}$. Write $S$ for their $\mathbb{Q}$-span.

Everything the statement uses:

- $L/K$: $K$ is a subfield of $L$, so $L$ is a vector space over $K$.
- $[L:K]$: the dimension of $L$ as a vector space over $K$.
- Intermediate field: a field $M$ with $K \subseteq M \subseteq L$.
- $K(K_1,K_2)$: the smallest subfield of $L$ containing $K$, $K_1$ and $K_2$.
- $K$-basis of $K_1$: a list of elements of $K_1$, independent over $K$ and spanning $K_1$ over $K$; its length is $[K_1:K]$.
- $K$-span of a set: every sum of (something in $K$) times (something in the set).

Your one step: $\sqrt{2} + \sqrt{6}$ and $1 + \sqrt{3}$ both lie in $S$. Multiply those two together, and tell me whether the result is again in $S$ — if it is, give it as a $\mathbb{Q}$-combination of $1$, $\sqrt{2}$, $\sqrt{3}$, $\sqrt{6}$.
