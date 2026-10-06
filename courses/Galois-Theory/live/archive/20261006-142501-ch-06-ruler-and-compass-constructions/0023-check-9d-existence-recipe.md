---
kind: lesson
title: check 9d-existence-recipe
---
What you noticed is true of the exponents, not of $\zeta^3$ itself, and it is the right instinct. $\zeta^3 \cdot \zeta^3 = \zeta^6 \ne 1$, so $\zeta^3$ is not its own inverse. What is true is $3 \cdot 3 = 9 \equiv 1 \pmod 8$, and likewise $5 \cdot 5 \equiv 1$ and $7 \cdot 7 \equiv 1$. So $(\zeta^k)^k = \zeta^{k^2} = \zeta$ for each $k \in \{3,5,7\}$.

That fact does two jobs. It is the order-2 piece later: $\sigma_k(\sigma_k(\zeta)) = \zeta^{k^2} = \zeta$. And it is half of existence now.

Existence is the 8(c) recipe, in two facts:
1. $\zeta^k$ has the same minimal polynomial as $\zeta$, namely $x^4+1$. Then 8(a) gives an isomorphism $\mathbb{Q}(\zeta) \to \mathbb{Q}(\zeta^k)$ with $\zeta \mapsto \zeta^k$.
2. $\mathbb{Q}(\zeta^k) = \mathbb{Q}(\zeta)$, so that isomorphism lands in $K$ and is an automorphism. Your observation gives this: $\zeta = (\zeta^k)^k \in \mathbb{Q}(\zeta^k)$, and $\zeta^k \in \mathbb{Q}(\zeta)$.

Fact 2 is done. Fact 1 is the only gap.

**Problem 9(d), existence.** With $\zeta = \zeta_8$ and $K = \mathbb{Q}(\zeta)$: for $k \in \{3,5,7\}$, show there is an automorphism $\sigma_k$ of $K$ with $\sigma_k(\zeta) = \zeta^k$.

What you need:
- $\zeta = e^{2\pi i/8}$, so $\zeta^8 = 1$ and $\zeta^4 = -1$.
- $x^4+1$ is irreducible over $\mathbb{Q}$ (9(a)), so it is the minimal polynomial of any root of it.
- 8(a): if $\alpha, \beta$ have the same minimal polynomial over $F$, there is a unique isomorphism $F(\alpha) \to F(\beta)$ fixing $F$ with $\alpha \mapsto \beta$.
- An automorphism of $K$ is an isomorphism $K \to K$.

Show that $\zeta^k$ is a root of $x^4 + 1$ for each $k \in \{3,5,7\}$.
