---
kind: lesson
title: What the vector space is, and where the 7 comes from
---
Nothing new is built. The vector space *is* $L$, with two of its own
operations relabelled: the vectors are the elements of $L$, the scalars
are the elements of $K$, vector addition is addition in $L$, and scaling
a vector $x$ by a scalar $\lambda$ is just the product $\lambda x$ taken
inside $L$. Every vector space axiom is then a field axiom of $L$ you
already have. That is the whole content of Theorem 4.1.

The second half of your question has a blunter answer: in 4.1 you do not
work the degree out, you are *given* it. "$[L:K]$ is prime" is the
hypothesis. Nobody hands you $L$ and $K$ concretely, so there is nothing
to compute — you reason from the number alone.

Outside that exercise the degree is found the usual way: name a spanning
set, check it is linearly independent over $K$, count it. Two examples,
both worth knowing:

- $\mathbb{C}$ over $\mathbb{R}$: the set $\{1, i\}$ works, so the degree is $2$.
- $\mathbb{Q}(\alpha)$ over $\mathbb{Q}$ where $\alpha = 2^{1/7}$: the set $\{1, \alpha, \alpha^2, \ldots, \alpha^6\}$ works, so the degree is $7$. That is a real extension of prime degree — 4.1 says it has no intermediate fields at all.

Words used above:

- **Spanning set** — every element of $L$ is a sum of scalar multiples of its members, scalars from $K$.
- **Linearly independent over $K$** — no such sum equals $0$ unless every scalar is $0$.
- **Basis** — a spanning set that is linearly independent. $[L:K]$ is how many elements it has.

**Your move.** Take $L = \mathbb{C}$ and $K = \mathbb{R}$, with the
claimed basis $\{1, i\}$.

Show the spanning half only: given an arbitrary complex number, write it
as a scalar multiple of $1$ plus a scalar multiple of $i$, and say
explicitly which two *real* numbers you used as the scalars.

One line. Then we go back to your two pairs and finish 4.1.
