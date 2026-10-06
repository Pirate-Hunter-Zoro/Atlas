---
kind: lesson
title: check 10d-subgroup-of-s3
---
Correct. Every element of $\mathbb{Q}(R)$ is a rational combination of monomials in the roots, $\sigma$ and $\tau$ fix the rational coefficients, and they agree on the roots, so they agree on $x$. The one line you left implicit is $E = \mathbb{Q}(R)$. That is 10(a), and the write-up states it.

Last clause of 10(d): conclude that $\operatorname{Aut}(E/\mathbb{Q})$ is isomorphic to a subgroup of $S_3$.

The recipe is the map $\Phi(\sigma) = \sigma|_R$, sending each automorphism to the permutation of $R$ it induces. Three facts combine:
- $\Phi$ lands in $\operatorname{Sym}(R) \cong S_3$ (your first part).
- $\Phi$ is injective (your second part).
- $\Phi$ is a homomorphism. This is the one you have not shown.

An injective homomorphism is an isomorphism onto its image, and the image of a homomorphism is a subgroup.

**10(d), last part.** Let $E = \mathbb{Q}(\sqrt[3]{2}, \zeta_3)$ and define $\Phi \colon \operatorname{Aut}(E/\mathbb{Q}) \to \operatorname{Sym}(R)$ by $\Phi(\sigma) = \sigma|_R$. Show $\Phi$ is an injective homomorphism, and conclude that $\operatorname{Aut}(E/\mathbb{Q})$ is isomorphic to a subgroup of $S_3$.

What you need:
- $R = \{r_1, r_2, r_3\}$, the three distinct roots of $x^3 - 2$ (10(a)).
- $\operatorname{Sym}(R)$: the group of bijections $R \to R$ under composition; $\operatorname{Sym}(R) \cong S_3$ since $|R| = 3$.
- The group operation in $\operatorname{Aut}(E/\mathbb{Q})$ is composition, $\sigma\tau = \sigma \circ \tau$.
- Homomorphism: $\Phi(\sigma \circ \tau) = \Phi(\sigma) \circ \Phi(\tau)$ for all $\sigma, \tau$.
- $\sigma|_R$ is a permutation of $R$ (first part); $\sigma|_R = \tau|_R \Rightarrow \sigma = \tau$ (second part).
- An injective homomorphism $G \to H$ is an isomorphism of $G$ onto its image, which is a subgroup of $H$.

Show that $\Phi(\sigma) = \sigma|_R$ is an injective homomorphism $\operatorname{Aut}(E/\mathbb{Q}) \to \operatorname{Sym}(R)$, and conclude that $\operatorname{Aut}(E/\mathbb{Q})$ is isomorphic to a subgroup of $S_3$.
