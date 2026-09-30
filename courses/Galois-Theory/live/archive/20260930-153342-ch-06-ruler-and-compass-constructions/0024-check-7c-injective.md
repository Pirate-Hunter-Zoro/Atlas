---
kind: lesson
title: check 7c-injective
---
Agreed: the homomorphism part of 7(c) is done. The missing line is now there: $\sigma(\zeta_n^{\,l})=\sigma(\zeta_n)^{l}$, which is $\sigma(ab)=\sigma(a)\sigma(b)$ applied $l-1$ times. Your chain then gives $(\sigma\circ\tau)(\zeta_n)=\zeta_n^{\,kl \bmod n}$, so composition becomes multiplication mod $n$. I am filing it now.

Next is injectivity: different automorphisms give different $k$.

**Exercise (7(c), injective part).** Let $K=\mathbb{Q}(\zeta_n)$. Show that the map $\operatorname{Aut}(K/\mathbb{Q})\to(\mathbb{Z}/n\mathbb{Z})^\times$, $\sigma\mapsto k \bmod n$ where $\sigma(\zeta_n)=\zeta_n^{\,k}$, is injective.

What it uses:

- $\zeta_n=e^{2\pi i/n}$, and $K=\mathbb{Q}(\zeta_n)$ is generated over $\mathbb{Q}$ by $\zeta_n$.
- 7(b): an automorphism of $K=F(\alpha_1,\dots,\alpha_r)$ fixing $F$ is determined by the values $\sigma(\alpha_1),\dots,\sigma(\alpha_r)$.
- $\zeta_n^{\,a}=\zeta_n^{\,b}$ exactly when $a\equiv b \pmod n$.
- Injective: $\sigma\mapsto k$ and $\tau\mapsto k$ force $\sigma=\tau$.

Your move: suppose $\sigma$ and $\tau$ both map to the same $k \bmod n$. Say what $\sigma(\zeta_n)$ and $\tau(\zeta_n)$ are, then which fact above makes $\sigma=\tau$.

So: if $\sigma(\zeta_n)=\zeta_n^{\,k}$ and $\tau(\zeta_n)=\zeta_n^{\,k'}$ with $k\equiv k'\pmod n$, prove $\sigma=\tau$.
