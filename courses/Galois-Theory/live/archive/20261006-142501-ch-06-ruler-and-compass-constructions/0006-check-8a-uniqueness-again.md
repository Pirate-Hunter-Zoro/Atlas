---
kind: lesson
title: check 8c-degree-p5
---
Problem 8(b) is agreed. The label is fixed, you checked all three Eisenstein conditions at $p$, and you shifted back from $\Phi_p(x+1)$ to $\Phi_p(x)$. The line $p \mid \binom{p}{k}$ for $2 \le k \le p-1$ stands as a stated fact. The worksheet now has 8(b) typeset beside your handwriting. 8(a) is already done, uniqueness included.

**Problem 8(c).** Deduce that $[\mathbb{Q}(\zeta_p) : \mathbb{Q}] = p - 1$ and that the injection of Problem 7(c) is an isomorphism, $\operatorname{Aut}(\mathbb{Q}(\zeta_p)/\mathbb{Q}) \cong (\mathbb{Z}/p\mathbb{Z})^{\times}$.

What you need:
- $\zeta_p = e^{2\pi i/p}$, a primitive $p$-th root of unity.
- $\Phi_p(x) = x^{p-1} + \cdots + x + 1$, irreducible over $\mathbb{Q}$ by your 8(b).
- $(x-1)\Phi_p(x) = x^p - 1$, your first line in 8(b).
- $[F(\alpha):F] = \deg$ of the minimal polynomial of $\alpha$ over $F$.
- 7(c): $\sigma \mapsto k \bmod p$, where $\sigma(\zeta_p) = \zeta_p^{\,k}$, is an injective homomorphism $\operatorname{Aut}(\mathbb{Q}(\zeta_p)/\mathbb{Q}) \hookrightarrow (\mathbb{Z}/p\mathbb{Z})^{\times}$.
- 8(a): if $\alpha, \beta$ are roots of the same irreducible $q \in F[x]$, there is a unique isomorphism $F(\alpha) \to F(\beta)$ fixing $F$ with $\alpha \mapsto \beta$.

First, one small case. Take $p = 5$. What is the minimal polynomial of $\zeta_5$ over $\mathbb{Q}$, and so what is $[\mathbb{Q}(\zeta_5):\mathbb{Q}]$? Say why $\zeta_5$ is a root of it.
