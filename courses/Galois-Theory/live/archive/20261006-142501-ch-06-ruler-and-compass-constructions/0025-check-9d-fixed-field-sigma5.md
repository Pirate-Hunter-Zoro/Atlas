---
kind: lesson
title: check 9d-fixed-field-sigma5
---
Order 2 is right, for all three $k$. $\sigma_k^2(\zeta) = \zeta^{k^2} = \zeta$ and $\sigma_k(\zeta) = \zeta^k \ne \zeta$. The write-up adds the two links you left silent. First, $\sigma_k^2(\zeta) = \sigma_k(\zeta^k) = \sigma_k(\zeta)^k$, because $\sigma_k$ respects products. Second, $\sigma_k^2$ agrees with $\mathrm{id}$ on $\zeta$ and on $\mathbb{Q}$, so $\sigma_k^2 = \mathrm{id}$.

Last piece of 9(d): the fixed fields. Start with $\sigma_5$.

**Problem 9(d), fixed field of $\sigma_5$.** With $\zeta = \zeta_8$ and $K = \mathbb{Q}(\zeta) = \mathbb{Q}(i,\sqrt2)$, let $\sigma_5$ be the automorphism of $K$ with $\sigma_5(\zeta) = \zeta^5$. Show that the subfield of $K$ fixed by $\sigma_5$ is $\mathbb{Q}(i)$.

What you need:
- Fixed field: $K^{\sigma_5} = \{a \in K : \sigma_5(a) = a\}$, a subfield of $K$ containing $\mathbb{Q}$.
- $i = \zeta^2$, and $\zeta^j = \zeta^{j'}$ exactly when $j \equiv j' \pmod 8$.
- $[K:\mathbb{Q}] = 4$ and $[\mathbb{Q}(i):\mathbb{Q}] = 2$, so $[K:\mathbb{Q}(i)] = 2$.
- Tower law: for fields $F \subseteq L \subseteq M$, $[M:F] = [M:L]\,[L:F]$.
- $\sigma_5 \ne \mathrm{id}$, from the order-2 step.

The recipe has three moves:
1. Show $\sigma_5(i) = i$, so $\mathbb{Q}(i) \subseteq K^{\sigma_5}$.
2. Show $K^{\sigma_5} \ne K$.
3. Squeeze: $\mathbb{Q}(i) \subseteq K^{\sigma_5} \subsetneq K$ with $[K:\mathbb{Q}(i)] = 2$, and the tower law leaves one option.

Show that the subfield of $K$ fixed by $\sigma_5$ is exactly $\mathbb{Q}(i)$.
