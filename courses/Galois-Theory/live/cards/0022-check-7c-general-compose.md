---
kind: lesson
title: check 7c-general-compose
---
Right: $(\sigma\circ\tau)(\zeta_5)=\zeta_5$, so $j=1$, and $1\equiv 2\cdot 3 \pmod 5$. The exponents multiply, then reduce mod $5$.

One line is missing. You went from $\sigma(\zeta_5^{\,3})$ straight to $\zeta_5^{\,6}$. The step between is $\sigma(\zeta_5^{\,3})=\sigma(\zeta_5)^3=(\zeta_5^{\,2})^3$. In the general case that line is the whole proof, so write it.

Now the general version, which is the homomorphism claim of 7(c).

**Exercise.** Let $K=\mathbb{Q}(\zeta_n)$ and $\sigma,\tau\in\operatorname{Aut}(K/\mathbb{Q})$ with $\sigma(\zeta_n)=\zeta_n^{\,k}$ and $\tau(\zeta_n)=\zeta_n^{\,l}$. Show that $(\sigma\circ\tau)(\zeta_n)=\zeta_n^{\,kl}$. Conclude that the exponent of $\sigma\circ\tau$ is $kl \bmod n$, so $\sigma\mapsto k \bmod n$ turns composition into multiplication.

What it uses:

- $\zeta_n=e^{2\pi i/n}$, and $\zeta_n^{\,n}=1$.
- $\sigma(a^m)=\sigma(a)^m$ for integers $m$, because $\sigma$ multiplies.
- $\sigma\circ\tau$ means apply $\tau$ first, then $\sigma$.
- $\zeta_n^{\,a}=\zeta_n^{\,b}$ exactly when $a\equiv b \pmod n$.
- A homomorphism here: the exponent of $\sigma\circ\tau$ is the product of the exponents of $\sigma$ and $\tau$, mod $n$.

Your move: compute $(\sigma\circ\tau)(\zeta_n)$ one equality per line, naming the rule each line uses. Then say why this shows $\sigma\circ\tau\mapsto kl \bmod n$.
