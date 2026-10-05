---
kind: lesson
title: check 10d-bijection-how
---
---
kind: lesson
title: check 10d-bijection-how
---
How: injective plus finite. Those two facts together give the bijection, and you need nothing else.

The recipe has two steps.
1. **One-to-one.** $\sigma$ is injective on all of $E$, because it is a field homomorphism. So it is injective on the smaller set $R$ too: $\sigma(r_i) = \sigma(r_j)$ forces $r_i = r_j$.
2. **Onto, by counting.** So $\sigma(r_1), \sigma(r_2), \sigma(r_3)$ are three *different* elements. Roots go to roots, so all three lie in $R$. Now count them against the size of $R$.

That counting step is the whole of "onto". There is no separate onto argument to find. It only works because $R$ is finite: on an infinite set, $n \mapsto 2n$ on $\mathbb{Z}$ is injective but not onto.

**10(d), first part.** Let $E = \mathbb{Q}(\sqrt[3]{2}, \zeta_3)$ and $\sigma \in \operatorname{Aut}(E/\mathbb{Q})$. Show $\sigma$ restricted to $R$ is a permutation of $R$.

What you need:
- $R = \{r_1, r_2, r_3\}$, the roots of $x^3 - 2$: $r_1 = \sqrt[3]{2}$, $r_2 = \omega\sqrt[3]{2}$, $r_3 = \omega^2\sqrt[3]{2}$, with $\omega = \zeta_3$. They are pairwise distinct (10(a)), so $|R| = 3$.
- Roots go to roots: $\sigma(r_i) \in R$ for each $i$ (card 0041).
- $\sigma$ is injective, since it is a field homomorphism.
- A permutation of a set is a bijection from the set to itself.

Write the two steps: why $\sigma$ is one-to-one on $R$, and why three distinct images inside $R$ must be all of $R$, so that $\sigma|_R$ is a permutation.
