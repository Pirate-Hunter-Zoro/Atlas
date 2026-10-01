---
kind: lesson
title: check 8c-onto-same-field
---
Step one is done: $\Phi_p(\zeta_p^k) = 0$. One line of it is wrong, though.

You wrote $(\zeta_p^k)^p - 1 = \zeta_p^k - 1 = 1 - 1$. That says $\zeta_p^k = 1$, which your next line correctly denies. The right middle step is $(\zeta_p^k)^p = (\zeta_p^p)^k = 1^k = 1$. So the right-hand side is $0$, $\zeta_p^k - 1 \ne 0$, and $\Phi_p(\zeta_p^k) = 0$. Your conclusion stands.

So $\zeta_p^k$ is a root of the irreducible $\Phi_p$, just as $\zeta_p$ is. Problem 8(a) then gives an isomorphism $\mathbb{Q}(\zeta_p) \to \mathbb{Q}(\zeta_p^k)$ sending $\zeta_p \mapsto \zeta_p^k$. It is an automorphism only if those two fields are the same field. That is step two.

Clearly $\mathbb{Q}(\zeta_p^k) \subseteq \mathbb{Q}(\zeta_p)$. The other inclusion needs $\zeta_p \in \mathbb{Q}(\zeta_p^k)$.

What you need:
- $\zeta_p = e^{2\pi i/p}$, $p$ prime, $1 \le k \le p-1$.
- $\zeta_p^p = 1$, so exponents of $\zeta_p$ only matter mod $p$.
- $p \nmid k$, so $k$ is a unit in $\mathbb{Z}/p$: some integer $m$ has $km \equiv 1 \pmod p$.
- $\mathbb{Q}(\beta)$ is the smallest field containing $\mathbb{Q}$ and $\beta$, so it contains every power of $\beta$.

Show: $\zeta_p \in \mathbb{Q}(\zeta_p^k)$, by writing $\zeta_p$ as a power of $\zeta_p^k$. Conclude $\mathbb{Q}(\zeta_p^k) = \mathbb{Q}(\zeta_p)$.
