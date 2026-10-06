---
kind: lesson
title: check 9d-order-two
---
Existence is right, for all three $k$. $(\zeta^k)^4 = e^{k\pi i} = -1$ because $k$ is odd, so $\zeta^k$ is a root of $x^4+1$. That is fact 1, and fact 2 was already done. So 8(a) gives $\sigma_k$, and it lands in $K$. Existence is now typeset in 9(d) of the worksheet.

One small thing the file fixes for you: what 8(a) hands you is an isomorphism $\mathbb{Q}(\zeta) \to \mathbb{Q}(\zeta^k)$. It is an automorphism of $K$ only because $\mathbb{Q}(\zeta^k) = K$. The write-up says so in one line.

Next piece of 9(d): order 2.

**Problem 9(d), order 2.** With $\zeta = \zeta_8$ and $K = \mathbb{Q}(\zeta)$, let $\sigma_k$ be the automorphism of $K$ with $\sigma_k(\zeta) = \zeta^k$, for $k \in \{3,5,7\}$. Show that each $\sigma_k$ has order 2.

What you need:
- $\zeta = e^{2\pi i/8}$, so $\zeta^8 = 1$, and $\zeta^j = \zeta^{j'}$ exactly when $j \equiv j' \pmod 8$.
- $k^2 \equiv 1 \pmod 8$ for $k = 3, 5, 7$ (you noticed this last time).
- An automorphism of $\mathbb{Q}(\zeta)$ fixes $\mathbb{Q}$ and is determined by where it sends $\zeta$.
- $\sigma$ has order 2 means $\sigma^2 = \mathrm{id}$ and $\sigma \ne \mathrm{id}$.

Show that $\sigma_k^2 = \mathrm{id}$ and $\sigma_k \ne \mathrm{id}$ for each $k \in \{3,5,7\}$.
