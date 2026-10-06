---
kind: lesson
title: check 10d-determined-by-permutation
---
Correct. $R$ is finite, $\sigma|_R$ is one-to-one into $R$, so pigeonhole makes it onto. That is the first part of 10(d), and the write-up now has it.

Next is the middle clause of the sheet: $\sigma$ is *determined by* that permutation. Concretely, two automorphisms that shuffle the roots the same way are the same automorphism.

The recipe is two facts you already have. $E$ is generated over $\mathbb{Q}$ by the roots themselves (10(a)). An automorphism fixing $\mathbb{Q}$ is determined by where it sends a set of generators. The missing piece is putting them together.

**10(d), second part.** Let $E = \mathbb{Q}(\sqrt[3]{2}, \zeta_3)$ and $\sigma, \tau \in \operatorname{Aut}(E/\mathbb{Q})$. Show that if $\sigma|_R = \tau|_R$, then $\sigma = \tau$.

What you need:
- $R = \{r_1, r_2, r_3\}$, the roots of $x^3 - 2$: $r_1 = \sqrt[3]{2}$, $r_2 = \omega\sqrt[3]{2}$, $r_3 = \omega^2\sqrt[3]{2}$, with $\omega = \zeta_3$.
- $E = \mathbb{Q}(r_1, r_2, r_3)$: $E$ is the splitting field of $x^3 - 2$ (10(a)).
- Determined by generators: if $E = \mathbb{Q}(a_1, \dots, a_m)$ and $\sigma, \tau \in \operatorname{Aut}(E/\mathbb{Q})$ agree on every $a_i$, then $\sigma = \tau$.
- $\sigma|_R$ is the permutation of $R$ that $\sigma$ induces (first part).

Show that if $\sigma$ and $\tau$ induce the same permutation of $R$, then $\sigma = \tau$.
