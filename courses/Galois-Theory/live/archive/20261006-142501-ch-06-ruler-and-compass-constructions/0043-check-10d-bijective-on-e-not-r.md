---
kind: lesson
title: check 10d-bijective-on-E-not-R
---
Bijective on $E$ gives you one-to-one on $R$ for free. It does not give you onto $R$.

Onto $E$ says every $r_j$ has *some* preimage in $E$. Nothing yet says that preimage is in $R$. A bijection can map a subset into itself without filling it: $n \mapsto n+1$ is a bijection of $\mathbb{Z}$ that sends $\mathbb{N}$ into $\mathbb{N}$, and nothing in $\mathbb{N}$ maps to $0$.

So your route needs one more fact. Either of these closes it:
- **Count.** Three distinct images inside a 3-element set are all of it.
- **Use the inverse.** $\sigma^{-1}$ is also in $\operatorname{Aut}(E/\mathbb{Q})$, so it also sends roots to roots. Then the preimage $\sigma^{-1}(r_j)$ lies in $R$.

Pick one.

**10(d), first part.** Let $E = \mathbb{Q}(\sqrt[3]{2}, \zeta_3)$ and $\sigma \in \operatorname{Aut}(E/\mathbb{Q})$. Show $\sigma$ restricted to $R$ is a permutation of $R$.

What you need:
- $R = \{r_1, r_2, r_3\}$, the roots of $x^3 - 2$: $r_1 = \sqrt[3]{2}$, $r_2 = \omega\sqrt[3]{2}$, $r_3 = \omega^2\sqrt[3]{2}$, with $\omega = \zeta_3$. Pairwise distinct (10(a)), so $|R| = 3$.
- Roots go to roots: any $\tau \in \operatorname{Aut}(E/\mathbb{Q})$ has $\tau(r_i) \in R$ (card 0041).
- $\sigma$ is a bijection $E \to E$, and $\sigma^{-1} \in \operatorname{Aut}(E/\mathbb{Q})$.
- A permutation of a set is a bijection from the set to itself.

Show $\sigma|_R$ is a permutation of $R$: one-to-one from $\sigma$ being injective, and onto $R$ by counting or by applying roots-to-roots to $\sigma^{-1}$.
