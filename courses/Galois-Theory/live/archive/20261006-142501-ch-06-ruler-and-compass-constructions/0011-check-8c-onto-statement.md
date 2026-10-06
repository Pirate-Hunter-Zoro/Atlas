---
kind: lesson
title: check 8c-onto-statement
---
Back to 8(c), then. The degree half stays as you wrote it. What is left is one claim: every $k$ from $1$ to $p-1$ is actually hit.

**What "onto" means here.** Problem 7(c) gave you a map $\operatorname{Aut}(\mathbb{Q}(\zeta_p)/\mathbb{Q}) \to (\mathbb{Z}/p\mathbb{Z})^\times$. It sends $\sigma$ to the $k$ with $\sigma(\zeta_p) = \zeta_p^k$. You proved it is injective. Onto says the reverse: pick any $k$ with $1 \le k \le p-1$, and some automorphism sends $\zeta_p$ to $\zeta_p^k$. So you must build, for each such $k$, an automorphism $\sigma_k$ of $\mathbb{Q}(\zeta_p)$ fixing $\mathbb{Q}$ with $\sigma_k(\zeta_p) = \zeta_p^k$.

The tool is your own 8(a). It needs two things about $\zeta_p^k$: that it has the same minimal polynomial as $\zeta_p$, and that $\mathbb{Q}(\zeta_p^k)$ is the same field as $\mathbb{Q}(\zeta_p)$.

What you need:
- $\zeta_p = e^{2\pi i/p}$, $p$ prime.
- $\Phi_p(x) = x^{p-1} + \dots + x + 1$, the minimal polynomial of $\zeta_p$ over $\mathbb{Q}$ (your degree half).
- 8(a): if $\alpha, \beta$ have the same minimal polynomial over $F$, there is a unique isomorphism $F(\alpha) \to F(\beta)$ fixing $F$ with $\alpha \mapsto \beta$.
- 7(c): the injection $\sigma \mapsto k$, where $\sigma(\zeta_p) = \zeta_p^k$.

Prove: for each $k$ with $1 \le k \le p-1$ there is an automorphism $\sigma_k$ of $\mathbb{Q}(\zeta_p)$ fixing $\mathbb{Q}$ with $\sigma_k(\zeta_p) = \zeta_p^k$. Hence the injection of 7(c) is onto, so $\operatorname{Aut}(\mathbb{Q}(\zeta_p)/\mathbb{Q}) \cong (\mathbb{Z}/p\mathbb{Z})^\times$.
