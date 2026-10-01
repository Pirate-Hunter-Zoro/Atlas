---
kind: lesson
title: check 9a-x4-plus-1-pose
---
Step two is right, and with it 8(c) is finished: the injection $\mathrm{Aut}(\mathbb{Q}(\zeta_p)/\mathbb{Q}) \to (\mathbb{Z}/p)^\times$ is onto. No question on the page.

Your $k'$ with $kk' \equiv 1 \pmod p$ gives $(\zeta_p^k)^{k'} = \zeta_p^{kk'} = \zeta_p$, so $\zeta_p \in \mathbb{Q}(\zeta_p^k)$ and the fields are equal. Then 8(a) makes $\zeta_p \mapsto \zeta_p^k$ an automorphism, for every $k$ in $(\mathbb{Z}/p)^\times$.

Your middle line still reads $\zeta_p^k - 1 = 1 - 1$. The write-up says $(\zeta_p^k)^p = (\zeta_p^p)^k = 1$ instead, and 8(c) is now typeset in full.

**Problem 9(a).** Let $\zeta = \zeta_8$ and $K = \mathbb{Q}(\zeta)$. Show that $\zeta$ is a root of $x^4 + 1$, that $x^4 + 1$ is irreducible over $\mathbb{Q}$, and hence that $[K : \mathbb{Q}] = 4$.

What you need:
- $\zeta_8 = e^{2\pi i/8} = e^{\pi i/4}$.
- Eisenstein at a prime $q$: monic, $q$ divides every non-leading coefficient, $q^2$ does not divide the constant term. Then it is irreducible over $\mathbb{Q}$.
- $f(x)$ is irreducible exactly when $f(x+c)$ is, for any $c \in \mathbb{Q}$ (your 8(b) shift).
- $[F(\alpha):F]$ is the degree of the minimal polynomial of $\alpha$ over $F$.

Show $\zeta_8$ is a root of $x^4+1$, that $x^4+1$ is irreducible over $\mathbb{Q}$, and so that $[\mathbb{Q}(\zeta_8):\mathbb{Q}] = 4$.
