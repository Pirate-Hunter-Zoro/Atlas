---
kind: note
title: Isomorphism, and why a non-field cannot be one with a field
---

**Definition.** A map $\theta : A \to B$ between rings is a *ring isomorphism* if it is

1. a ring homomorphism: $\theta(a + a') = \theta(a) + \theta(a')$, $\theta(aa') = \theta(a)\theta(a')$, and $\theta(1_A) = 1_B$; and
2. a **bijection** — injective *and* surjective.

Clause 2 is the whole of your problem. "Can be identified naturally with" in 3.2 means *there is an isomorphism*, and "naturally" only adds that it is the canonical one rather than some arbitrary choice.

Your impression is half right, and the right half is worth keeping: there **is** a map $R[x_1,\ldots,x_n] \to F(x_1,\ldots,x_n)$, it is a homomorphism, and it is injective. It is the natural place to start building. It is simply not the isomorphism, and it cannot be made into one.

Here is why, and you already have every piece. An isomorphism transports structure in both directions: if $A \cong B$ and $B$ is a field, then $A$ is a field, because you can carry an inverse back along $\theta^{-1}$. Now — $F(x_1,\ldots,x_n)$ is a field. $R[x_1,\ldots,x_n]$ is not: $x_1$ has no inverse in $\mathbb{Z}[x_1,x_2]$, as you established. So no isomorphism between them exists, ever, no matter how the map is defined.

It is precisely $\mathbb{Z} \not\cong \mathbb{Q}$. Injection, yes. Isomorphism, no — and the elements it misses are the ones you just characterised as $b \neq 1$.

**Your move.** Write the corrected arrow for $\phi$, and add one line saying which of the two clauses above the old arrow failed.
