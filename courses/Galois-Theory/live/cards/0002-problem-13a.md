---
kind: question
title: problem-13a
---
The sheet is Problems 13–19 on the Galois correspondence and cyclotomic fields, and we start at Problem 13(a). I am taking all seven as assigned; say so if only some are.

**Problem 13(a).** Let $p$ be an odd prime, $\zeta = \zeta_p$, $K = \mathbb{Q}(\zeta)$ and $G = \mathrm{Gal}(K/\mathbb{Q})$. Show that $G$ is cyclic of order $p-1$.

The proof has three pieces: count $|G|$, embed $G$ into a group you know, and show that group is cyclic. Before any of that, one small case.

**Your check.** Take $p = 5$, so $\zeta = \zeta_5 = e^{2\pi i/5}$. An automorphism $\sigma$ of $\mathbb{Q}(\zeta_5)$ must send $\zeta$ to some complex number. Which of $1, \zeta, \zeta^2, \zeta^3, \zeta^4$ can $\sigma(\zeta)$ be? Give a reason that rules out each one you exclude.

What you may use:

- $\zeta_n = e^{2\pi i/n}$, a primitive $n$-th root of unity: $\zeta_n^n = 1$ and no smaller positive power equals $1$.
- $\mathrm{Gal}(K/\mathbb{Q})$: the field automorphisms of $K$. Every one fixes $\mathbb{Q}$ pointwise.
- An automorphism fixing $\mathbb{Q}$ sends a root of a polynomial with rational coefficients to another root of the same polynomial.
- An automorphism is injective, and it respects multiplication: $\sigma(\zeta^k) = \sigma(\zeta)^k$.
- $(\mathbb{Z}/p\mathbb{Z})^\times$: the nonzero residues mod $p$ under multiplication, a group of order $p-1$.

For $p = 5$: which of $1, \zeta, \zeta^2, \zeta^3, \zeta^4$ can $\sigma(\zeta)$ be, and why is each excluded one impossible?
