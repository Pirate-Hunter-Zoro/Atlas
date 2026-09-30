---
kind: lesson
title: check 7c-bound
---
Agreed: injectivity is proved. Your chain is complete, and the note under it names exactly what licenses the skipped lines. $\sigma,\tau$ are ring maps $K\to K$ fixing $\mathbb{Q}$, so they pass through sums, products and powers and leave each $a_j$ alone. That is the whole justification, and you stated it.

The injectivity paragraph is going into 7(c) in the worksheet file now, in your order: $k\equiv k' \pmod n$ gives $\zeta_n^{k}=\zeta_n^{k'}$, then the sum for arbitrary $x$.

One piece of 7(c) is left: the bound on the size of the group.

What it uses:

- $\zeta_n=e^{2\pi i/n}$ and $K=\mathbb{Q}(\zeta_n)$.
- $\mathrm{Aut}(K/\mathbb{Q})$ is the group of automorphisms of $K$ fixing $\mathbb{Q}$.
- $(\mathbb{Z}/n\mathbb{Z})^\times$ is the group of residues $k \bmod n$ with $\gcd(k,n)=1$, under multiplication.
- $\varphi(n)$ is Euler's function: the number of $k$ in $\{1,\dots,n\}$ with $\gcd(k,n)=1$.
- Your map $\sigma\mapsto k \bmod n$, where $\sigma(\zeta_n)=\zeta_n^{k}$, lands in $(\mathbb{Z}/n\mathbb{Z})^\times$, is a homomorphism, and is injective.

So: show $|\mathrm{Aut}(K/\mathbb{Q})|\le\varphi(n)$.
