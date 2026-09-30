---
kind: lesson
title: check 7c-compose
---
Your chain is right, so the first claim of 7(c) is agreed: every $\sigma$ has $\sigma(\zeta_n)=\zeta_n^{\,k}$ with $\gcd(k,n)=1$.

The $\sigma$ is gone after the second equals sign, and $(\zeta_n^{\,k})^{n/d}=(\zeta_n^{\,n})^{k/d}=1$ is clean. You still stopped at "$=1$, contradiction". The step you skipped: $\sigma(\zeta_n^{\,n/d})=1=\sigma(1)$, and $\sigma$ is injective, so $\zeta_n^{\,n/d}=1$. That is what clashes with your top half. The write-up now says it, and it is typeset.

Next is the second claim: the map $\sigma\mapsto k \bmod n$ is a homomorphism. First, one concrete case.

**Check.** Take $n=5$. Let $\sigma(\zeta_5)=\zeta_5^{\,2}$ and $\tau(\zeta_5)=\zeta_5^{\,3}$.

What it uses:

- $\zeta_5=e^{2\pi i/5}$, and $\zeta_5^{\,5}=1$.
- $\sigma(a^m)=\sigma(a)^m$ for integers $m$.
- $\sigma\circ\tau$ means apply $\tau$ first, then $\sigma$.

Your move: compute $(\sigma\circ\tau)(\zeta_5)$ as a power $\zeta_5^{\,j}$ with $0\le j<5$, one equality per line. Then say how $j$ relates to the exponents $2$ and $3$.
