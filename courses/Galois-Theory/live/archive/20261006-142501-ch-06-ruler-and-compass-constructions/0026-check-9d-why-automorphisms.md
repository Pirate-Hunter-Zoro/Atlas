---
kind: lesson
title: check 9d-why-automorphisms
---
It doesn't. The order-2 lines assume $\sigma_k$ is already an automorphism and only compute its square. What makes $\sigma_k$ an automorphism is the top half of your page, the existence step.

Existence is two facts, and you have both:
1. $\zeta^k$ is a root of $x^4+1$, your three checkmarks. Since $x^4+1$ is irreducible (9(a)), it is the minimal polynomial of both $\zeta$ and $\zeta^k$. So 8(a) gives an isomorphism $\mathbb{Q}(\zeta) \to \mathbb{Q}(\zeta^k)$ fixing $\mathbb{Q}$ with $\zeta \mapsto \zeta^k$.
2. $\mathbb{Q}(\zeta^k) = \mathbb{Q}(\zeta)$. One way: $\zeta^k \in \mathbb{Q}(\zeta)$. The other: $\zeta = \zeta^{k^2} = (\zeta^k)^k \in \mathbb{Q}(\zeta^k)$, because $k^2 \equiv 1 \pmod 8$.

Fact 2 turns the isomorphism of fact 1 into a map $K \to K$. A field isomorphism from $K$ onto $K$ is an automorphism. That is $\sigma_k$.

Only then does order 2 make sense. $\sigma_k^2$ is a composite of automorphisms, it fixes $\mathbb{Q}$, and it sends $\zeta$ to $\zeta$. A map fixing $\mathbb{Q}$ is determined by where it sends the generator $\zeta$, so $\sigma_k^2 = \mathrm{id}$.

Back to the open piece.

**Problem 9(d), fixed field of $\sigma_5$.** With $\zeta = \zeta_8$ and $K = \mathbb{Q}(\zeta) = \mathbb{Q}(i,\sqrt2)$, let $\sigma_5$ be the automorphism of $K$ with $\sigma_5(\zeta) = \zeta^5$. Show that the subfield of $K$ fixed by $\sigma_5$ is $\mathbb{Q}(i)$.

What you need:
- Fixed field: $K^{\sigma_5} = \{a \in K : \sigma_5(a) = a\}$, a subfield of $K$ containing $\mathbb{Q}$.
- $i = \zeta^2$, and $\zeta^j = \zeta^{j'}$ exactly when $j \equiv j' \pmod 8$.
- $[K:\mathbb{Q}] = 4$ and $[\mathbb{Q}(i):\mathbb{Q}] = 2$, so $[K:\mathbb{Q}(i)] = 2$.
- Tower law: for fields $F \subseteq L \subseteq M$, $[M:F] = [M:L]\,[L:F]$.
- $\sigma_5 \ne \mathrm{id}$, since $\zeta^5 \ne \zeta$.

The recipe has three moves:
1. Show $\sigma_5(i) = i$, so $\mathbb{Q}(i) \subseteq K^{\sigma_5}$.
2. Show $K^{\sigma_5} \ne K$.
3. Squeeze: $\mathbb{Q}(i) \subseteq K^{\sigma_5} \subsetneq K$ with $[K:\mathbb{Q}(i)] = 2$, and the tower law leaves one option.

Show that the subfield of $K$ fixed by $\sigma_5$ is exactly $\mathbb{Q}(i)$.
