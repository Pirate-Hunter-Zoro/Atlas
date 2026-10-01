---
kind: lesson
title: check 9d-existence
---
Right, and 9(c) is done. $\zeta = \frac{\sqrt2}{2} + i\frac{\sqrt2}{2}$ puts $\zeta$ in $\mathbb{Q}(i,\sqrt2)$, so $K \subseteq \mathbb{Q}(i,\sqrt2)$. With last card's $\sqrt2 = \zeta + \zeta^7$ and $i = \zeta^2$, the two fields are equal. The write-up now says exactly that.

**Problem 9(d).** With $\zeta = \zeta_8$ and $K = \mathbb{Q}(\zeta)$: for $k \in \{3,5,7\}$, show there is an automorphism $\sigma_k$ of $K$ with $\sigma_k(\zeta) = \zeta^k$, that each $\sigma_k$ has order $2$, and that the subfields of $K$ fixed by $\sigma_5$, $\sigma_7$ and $\sigma_3$ are $\mathbb{Q}(i)$, $\mathbb{Q}(\sqrt2)$ and $\mathbb{Q}(\sqrt{-2})$ respectively.

Three pieces: existence, order 2, fixed fields. Existence first. It is the same move you made for $\sigma_k$ in 8(c).

What you need:
- $\zeta = e^{2\pi i/8}$, so $\zeta^8 = 1$ and $\zeta^4 = -1$.
- $x^4 + 1$ is the minimal polynomial of $\zeta$ over $\mathbb{Q}$ (9(a)), and $[K:\mathbb{Q}] = 4$.
- 8(a): if $\alpha, \beta$ have the same minimal polynomial over $F$, there is a unique isomorphism $F(\alpha) \to F(\beta)$ fixing $F$ and sending $\alpha \mapsto \beta$.
- An automorphism of $K$ is an isomorphism $K \to K$.
- Order $2$: $\sigma_k \ne \mathrm{id}$ and $\sigma_k \circ \sigma_k = \mathrm{id}$.
- Fixed field of $\sigma$: $\{a \in K : \sigma(a) = a\}$.
- From 9(c): $i = \zeta^2$, $\sqrt2 = \zeta + \zeta^7$, $K = \mathbb{Q}(i,\sqrt2)$.

Show that for each $k \in \{3,5,7\}$ there is an automorphism $\sigma_k$ of $K$ with $\sigma_k(\zeta) = \zeta^k$.
