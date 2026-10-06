---
kind: lesson
title: check 9d-fixed-field-sigma3
---
Correct, and complete. You found $\sqrt2 = \zeta + \zeta^{-1}$ yourself, and $\sigma_7$ swaps the two terms because $\zeta^{-7} = \zeta$. That puts $\mathbb{Q}(\sqrt2)$ inside the fixed field. $\zeta$ not being fixed makes it proper, and $[K:\mathbb{Q}(\sqrt2)] = 2$ finishes the squeeze. It goes into the write-up as you wrote it, with one added line: $\zeta + \zeta^{-1} = 2\,\mathrm{Re}\,\zeta = 2\cdot\tfrac{1}{\sqrt2} = \sqrt2$.

The last fixed field in 9(d) is the same squeeze again.

**Problem 9(d), fixed field of $\sigma_3$.** With $\zeta = \zeta_8$ and $K = \mathbb{Q}(\zeta) = \mathbb{Q}(i,\sqrt2)$, let $\sigma_3$ be the automorphism of $K$ with $\sigma_3(\zeta) = \zeta^3$. Show that the subfield of $K$ fixed by $\sigma_3$ is $\mathbb{Q}(\sqrt{-2})$.

What you need:
- Fixed field: $K^{\sigma_3} = \{a \in K : \sigma_3(a) = a\}$, a subfield of $K$ containing $\mathbb{Q}$.
- $\zeta = \frac{1+i}{\sqrt2}$ and $\zeta^3 = \frac{-1+i}{\sqrt2}$.
- $\zeta^j = \zeta^{j'}$ exactly when $j \equiv j' \pmod 8$.
- $\sqrt{-2} = i\sqrt2$, a root of the irreducible $x^2+2$, so $[\mathbb{Q}(\sqrt{-2}):\mathbb{Q}] = 2$.
- $[K:\mathbb{Q}] = 4$, so $[K:\mathbb{Q}(\sqrt{-2})] = 2$.
- Tower law: for fields $F \subseteq L \subseteq M$, $[M:F] = [M:L]\,[L:F]$.
- $\sigma_3 \ne \mathrm{id}$, since $\zeta^3 \ne \zeta$.

As with $\sigma_7$, write $\sqrt{-2}$ as a sum of two powers of $\zeta$, then apply $\sigma_3$.

Show that the subfield of $K$ fixed by $\sigma_3$ is exactly $\mathbb{Q}(\sqrt{-2})$.
