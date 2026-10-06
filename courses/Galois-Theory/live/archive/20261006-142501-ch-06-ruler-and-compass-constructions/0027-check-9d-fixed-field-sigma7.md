---
kind: lesson
title: check 9d-fixed-field-sigma7
---
Correct, and complete. $\sigma_5(i) = \zeta^{10} = \zeta^2 = i$ puts $\mathbb{Q}(i)$ inside the fixed field. $\zeta$ not being fixed makes the fixed field proper. Then $[K:K^{\sigma_5}]$ divides $[K:\mathbb{Q}(i)] = 2$ and is not 1, so it is 2, and the inner step is degree 1. That is the squeeze. It goes into the write-up as you wrote it.

Next is the same squeeze with a less obvious generator.

**Problem 9(d), fixed field of $\sigma_7$.** With $\zeta = \zeta_8$ and $K = \mathbb{Q}(\zeta) = \mathbb{Q}(i,\sqrt2)$, let $\sigma_7$ be the automorphism of $K$ with $\sigma_7(\zeta) = \zeta^7$. Show that the subfield of $K$ fixed by $\sigma_7$ is $\mathbb{Q}(\sqrt2)$.

What you need:
- Fixed field: $K^{\sigma_7} = \{a \in K : \sigma_7(a) = a\}$, a subfield of $K$ containing $\mathbb{Q}$.
- $\zeta = \frac{1+i}{\sqrt2}$ and $\zeta^7 = \zeta^{-1} = \overline{\zeta} = \frac{1-i}{\sqrt2}$.
- $\zeta^j = \zeta^{j'}$ exactly when $j \equiv j' \pmod 8$.
- $[K:\mathbb{Q}] = 4$ and $[\mathbb{Q}(\sqrt2):\mathbb{Q}] = 2$, so $[K:\mathbb{Q}(\sqrt2)] = 2$.
- Tower law: for fields $F \subseteq L \subseteq M$, $[M:F] = [M:L]\,[L:F]$.
- $\sigma_7 \ne \mathrm{id}$, since $\zeta^7 \ne \zeta$.

The one new move: $\sqrt2$ is not a power of $\zeta$, so write it as a sum of two powers of $\zeta$ first, then apply $\sigma_7$. The squeeze is the same as for $\sigma_5$.

Show that the subfield of $K$ fixed by $\sigma_7$ is exactly $\mathbb{Q}(\sqrt2)$.
