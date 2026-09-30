---
kind: lesson
title: check 7c-drop-the-sigma
---
One line is wrong: $\sigma(\zeta_n)^{n/d}=\sigma(\zeta_n^{\,k})^{n/d}$. The rule is $\sigma(\zeta_n)=\zeta_n^{\,k}$, with no $\sigma$ left on the right. You swapped $\zeta_n$ for $\zeta_n^{\,k}$ *inside* the $\sigma$, and $\sigma(\zeta_n^{\,k})=\zeta_n^{\,k^2}$, which is a different number.

Everything else is right. The top half gives $\zeta_n^{\,n/d}\neq 1$ correctly. The rewrite $kn/d=n\cdot(k/d)$ and $\zeta_n^{\,n}=1$ is exactly the move. Once the $\sigma$ is gone, those same steps work without it.

The finish needs one more sentence, too. Getting $\sigma(\zeta_n^{\,n/d})=1$ is not yet a contradiction. It becomes one because $\sigma(1)=1$ and $\sigma$ is injective (one-to-one), so $\zeta_n^{\,n/d}=1$, against your top half.

**Problem 7(c), first claim.** Let $K=\mathbb{Q}(\zeta_n)$ and $\sigma\in\operatorname{Aut}(K/\mathbb{Q})$ with $\sigma(\zeta_n)=\zeta_n^{\,k}$. Show $\gcd(k,n)=1$. Suppose instead $d=\gcd(k,n)>1$.

What it uses:

- $\zeta_n=e^{2\pi i/n}$, and $\zeta_n^{\,m}=1$ exactly when $n\mid m$.
- $d$ divides both $k$ and $n$, so $k/d$ and $n/d$ are integers.
- $\sigma(a^m)=\sigma(a)^m$ for integers $m$.
- $\sigma(1)=1$, and $\sigma$ is injective.
- Shown by you: $\zeta_n^{\,n/d}\neq 1$.

Your move: rewrite the bottom chain starting $\sigma(\zeta_n^{\,n/d})=\sigma(\zeta_n)^{n/d}=(\zeta_n^{\,k})^{n/d}=\cdots$, with no $\sigma$ after the second equals sign, down to $1$. Then add the injectivity line that makes it a contradiction.
