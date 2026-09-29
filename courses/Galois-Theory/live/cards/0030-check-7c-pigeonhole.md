---
kind: lesson
title: check 7c-pigeonhole
---
Not yet: the contradiction you reach is the wrong one. Every $\sigma$ already has $\gcd(k,n)=1$ — you proved that earlier in 7(c). So "more than $\varphi(n)$ automorphisms" cannot produce a $\sigma$ with $\gcd(k,n)>1$. It produces something else.

Here is the concrete case. Take $n=5$, so $\varphi(5)=4$ and $(\mathbb{Z}/5\mathbb{Z})^\times=\{1,2,3,4\}$. Pretend $\mathrm{Aut}(K/\mathbb{Q})$ had five elements $\sigma_1,\dots,\sigma_5$. Each one sends $\zeta_5$ to $\zeta_5^{k}$ with $k\in\{1,2,3,4\}$.

What it uses:

- $\zeta_n=e^{2\pi i/n}$ and $K=\mathbb{Q}(\zeta_n)$.
- $\mathrm{Aut}(K/\mathbb{Q})$ is the group of automorphisms of $K$ fixing $\mathbb{Q}$.
- $(\mathbb{Z}/n\mathbb{Z})^\times$ is the residues $k \bmod n$ with $\gcd(k,n)=1$; it has $\varphi(n)$ elements.
- Your map $\sigma\mapsto k \bmod n$, where $\sigma(\zeta_n)=\zeta_n^{k}$, lands in $(\mathbb{Z}/n\mathbb{Z})^\times$ and is injective: two automorphisms with the same $k$ are equal.

Five automorphisms, four possible values of $k$: what must happen to two of $\sigma_1,\dots,\sigma_5$, and which fact in the list above does that contradict?
