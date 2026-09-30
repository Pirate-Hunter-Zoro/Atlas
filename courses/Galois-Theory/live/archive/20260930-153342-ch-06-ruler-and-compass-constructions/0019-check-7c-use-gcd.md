---
kind: lesson
title: check 7c-use-gcd
---
You use the gcd through its *other* half: $d$ divides $k$ too, not just $n$. You have used $d\mid n$ (so $n/d$ is an integer). The step you have not taken yet is the one where $k$ enters, and that is where $d\mid k$ does its work.

Your new chain is right so far. $\sigma(\zeta_n^{\,n/d})=\sigma(\zeta_n)^{n/d}$ is legal, because $n/d$ is an integer. And $\zeta_n^{\,n/d}=e^{2\pi i/d}\neq 1$ is right. Rewriting $\sigma(\zeta_n)$ as $\sigma(e^{2\pi i/n})$ is only a change of name, though. It gets you nowhere. Replace it with what $\sigma$ actually does: $\sigma(\zeta_n)=\zeta_n^{\,k}$. That gives

$$\sigma(\zeta_n^{\,n/d})=\left(\zeta_n^{\,k}\right)^{n/d}=\zeta_n^{\,k\cdot n/d}.$$

Now write $k=d\cdot(k/d)$, where $k/d$ is an integer because $d\mid k$. Then $k\cdot n/d = n\cdot (k/d)$.

**Problem 7(c), first claim.** Let $K=\mathbb{Q}(\zeta_n)$ and $\sigma\in\operatorname{Aut}(K/\mathbb{Q})$ with $\sigma(\zeta_n)=\zeta_n^{\,k}$. Show $\gcd(k,n)=1$. Suppose instead $d=\gcd(k,n)>1$.

What it uses:

- $\zeta_n=e^{2\pi i/n}$: $\zeta_n^{\,m}=1$ exactly when $n\mid m$.
- $d$ divides both $k$ and $n$, so $k/d$ and $n/d$ are integers.
- $\sigma(a^m)=\sigma(a)^m$ for integers $m$.
- $\sigma(1)=1$, and $\sigma$ is injective (one-to-one).
- Shown by you: $\zeta_n^{\,n/d}\neq 1$.

Your move: using $k\cdot n/d=n\cdot(k/d)$, what is $\zeta_n^{\,k\cdot n/d}$? Then use $\sigma(1)=1$ and injectivity to finish the contradiction.
