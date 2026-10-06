---
kind: lesson
title: check 8c-onto-first-piece
---
Your statement is exactly right. Now use it: 8(a) turns it into two smaller facts about $\zeta_p^k$, and you prove the first one now.

8(a) builds an isomorphism $\mathbb{Q}(\zeta_p) \to \mathbb{Q}(\zeta_p^k)$ sending $\zeta_p \mapsto \zeta_p^k$. It needs $\zeta_p$ and $\zeta_p^k$ to have the same minimal polynomial. That is the first fact. The second fact, $\mathbb{Q}(\zeta_p^k) = \mathbb{Q}(\zeta_p)$, is what makes the isomorphism an automorphism. It comes next turn.

For the first fact you only need $\Phi_p(\zeta_p^k) = 0$. Then $\Phi_p$ is irreducible, monic, and kills $\zeta_p^k$, so it is the minimal polynomial of $\zeta_p^k$ too.

What you need:
- $\zeta_p = e^{2\pi i/p}$, $p$ prime, $1 \le k \le p-1$.
- $\Phi_p(x) = x^{p-1} + \dots + x + 1$, irreducible over $\mathbb{Q}$ (your degree half).
- $(x-1)\,\Phi_p(x) = x^p - 1$.
- 8(a): if $\alpha, \beta$ have the same minimal polynomial over $F$, there is a unique isomorphism $F(\alpha) \to F(\beta)$ fixing $F$ with $\alpha \mapsto \beta$.

Show: $\Phi_p(\zeta_p^k) = 0$ for each $k$ with $1 \le k \le p-1$.
