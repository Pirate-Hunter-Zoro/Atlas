---
kind: lesson
title: check 7c-the-missing-line
---
Nearly: the chain is right and the reduction mod $n$ at the end is right. One equality is still unjustified, and it is the same one as last time.

You wrote $\sigma(\zeta_n^{\,l})=\zeta_n^{\,kl}$ in one step. That jump hides two facts. First, $\sigma(\zeta_n^{\,l})=\sigma(\zeta_n)^{l}$, because $\sigma$ respects multiplication. Second, $\sigma(\zeta_n)^{l}=(\zeta_n^{\,k})^{l}$, because $\sigma(\zeta_n)=\zeta_n^{\,k}$. Only then does $(\zeta_n^{\,k})^{l}=\zeta_n^{\,kl}$. The first fact is where $\sigma$ being an automorphism is actually used, so it cannot be silent.

Also: the $n=5$ at the left is stray. This is the general $n$ now.

**Exercise (7(c), homomorphism part).** Let $K=\mathbb{Q}(\zeta_n)$ and $\sigma,\tau\in\operatorname{Aut}(K/\mathbb{Q})$ with $\sigma(\zeta_n)=\zeta_n^{\,k}$ and $\tau(\zeta_n)=\zeta_n^{\,l}$. Show $(\sigma\circ\tau)(\zeta_n)=\zeta_n^{\,kl}$, so $\sigma\mapsto k \bmod n$ turns composition into multiplication mod $n$.

What it uses:

- $\zeta_n=e^{2\pi i/n}$, and $\zeta_n^{\,n}=1$.
- $\sigma(ab)=\sigma(a)\sigma(b)$, since $\sigma$ is a field automorphism.
- $\sigma\circ\tau$ means apply $\tau$ first, then $\sigma$.
- $\zeta_n^{\,a}=\zeta_n^{\,b}$ exactly when $a\equiv b \pmod n$.

Your move: prove $\sigma(\zeta_n^{\,l})=\sigma(\zeta_n)^{l}$ for every integer $l\ge 1$, using only $\sigma(ab)=\sigma(a)\sigma(b)$. One line is enough if you say how it repeats. Then rewrite your chain for $(\sigma\circ\tau)(\zeta_n)$ with that line in it, naming the rule on each line.
