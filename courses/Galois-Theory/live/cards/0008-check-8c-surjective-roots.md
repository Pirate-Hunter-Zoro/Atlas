---
kind: lesson
title: check 8c-surjective-roots
---
---
kind: lesson
title: 8(c) degree agreed -- now surjectivity
---
Your degree argument is right: $[\mathbb{Q}(\zeta_p):\mathbb{Q}] = p-1$. The "clearly" hides one fact, which I take as read: $\zeta_p \neq 1$, so it is a root of the factor $\Phi_p$ rather than of $x-1$. Monic, irreducible, and killing $\zeta_p$ makes $\Phi_p$ the minimal polynomial.

**Problem 8(c), second half.** Show the injection of 7(c) is onto, so $\operatorname{Aut}(\mathbb{Q}(\zeta_p)/\mathbb{Q}) \cong (\mathbb{Z}/p\mathbb{Z})^{\times}$.

What you need:
- $\zeta_p = e^{2\pi i/p}$, with $\zeta_p^{\,p} = 1$ and $\zeta_p^{\,k} \neq 1$ for $1 \le k \le p-1$.
- $\Phi_p(x) = x^{p-1} + \cdots + x + 1$, irreducible over $\mathbb{Q}$ (8(b)), and $(x-1)\Phi_p(x) = x^p - 1$.
- 7(c): $\sigma \mapsto k \bmod p$, where $\sigma(\zeta_p) = \zeta_p^{\,k}$, is an injective homomorphism into $(\mathbb{Z}/p\mathbb{Z})^{\times}$.
- 8(a): if $\alpha, \beta$ are roots of the same irreducible $q \in F[x]$, there is a unique isomorphism $F(\alpha) \to F(\beta)$ fixing $F$ with $\alpha \mapsto \beta$.

One piece first. Fix $k$ with $1 \le k \le p-1$. Why is $\zeta_p^{\,k}$ a root of $\Phi_p$, and what is $\mathbb{Q}(\zeta_p^{\,k})$ as a field?
