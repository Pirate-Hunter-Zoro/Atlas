---
kind: lesson
title: check 10d-not-a-definition
---
No, it is not a definition. It is two short facts, and one of them you have not said yet.

The definition of $\sigma \in \operatorname{Aut}(E/\mathbb{Q})$ says only: a bijective field homomorphism $E \to E$ that fixes every rational. Nothing in it mentions roots. "Roots go to roots" is a one-line lemma on top of it: apply $\sigma$ to $r^3 - 2 = 0$, and since $\sigma$ respects products and fixes $2$, you get $\sigma(r)^3 - 2 = 0$.

So roots go to roots gives you a map $\{r_1, r_2, r_3\} \to \{r_1, r_2, r_3\}$. That is not yet a permutation. A permutation must hit all three roots. That is the missing fact.

Your "different roots if they don't fix the roots" is not needed, and not true in general: $\sigma$ may fix $r_1$ and swap $r_2, r_3$.

One slip in your second paragraph. Elements of $E$ are not rational *linear* combinations of $r_1, r_2, r_3$. Those only span a 2-dimensional space, since $r_1 + r_2 + r_3 = 0$, and $[E:\mathbb{Q}] = 6$. They are rational *polynomial* expressions in the roots, such as $r_1^2$ or $r_1 r_2$. "Determined by generators" is still the right fact; just say polynomial.

**10(d), first part.** Let $E = \mathbb{Q}(\sqrt[3]{2}, \zeta_3)$ and $\sigma \in \operatorname{Aut}(E/\mathbb{Q})$. Show $\sigma$ restricted to $\{r_1, r_2, r_3\}$ is a permutation of that set.

What you need:
- $r_1 = \sqrt[3]{2}$, $r_2 = \omega\sqrt[3]{2}$, $r_3 = \omega^2\sqrt[3]{2}$, with $\omega = \zeta_3$: the three roots of $x^3 - 2$, pairwise distinct (10(a)).
- Roots go to roots: $\sigma(r_i) \in \{r_1, r_2, r_3\}$ for each $i$.
- $\sigma$ is injective, since it is a field homomorphism.
- A permutation of a set is a bijection from the set to itself.

You have $\sigma$ sending $\{r_1, r_2, r_3\}$ into itself. Why does it hit all three roots, so that it is a permutation?
