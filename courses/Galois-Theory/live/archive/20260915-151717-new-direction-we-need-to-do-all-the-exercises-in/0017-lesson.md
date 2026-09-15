---
kind: lesson
title: four-five-closed-now-bound-a-degree-by-a-product
---
Skipped, so 4.5 is closed and here is the rest of it in four lines. $m_K$ is a
polynomial over $L$ with $\alpha$ as a root, and $m_L$ is the minimal such, so
$m_L \mid m_K$ and $d \leq n$. The tower law read two ways gives
$[L(\alpha):K] = d\,[L:K] = [L(\alpha):K(\alpha)]\,n$, so $n \mid d\,[L:K]$.
The hypothesis says $\gcd(n, [L:K]) = 1$, hence $n \mid d$, and with $d \leq n$
that forces $d = n$. Two monic polynomials, one dividing the other, same degree:
$m_L = m_K$, whose coefficients are in $K$.

**Exercise 4.2.** Let $L : K$ be a finite extension. Let $K_1$ and $K_2$ be
intermediate fields with $L = K(K_1, K_2)$. Show that
$[L:K] \leq [K_1:K]\,[K_2:K]$.

What you need:

- $L : K$ — $K$ is a subfield of $L$; $L$ is then a vector space over $K$.
- $[L:K]$ — the dimension of $L$ as a vector space over $K$. Finite here.
- **intermediate field** — a subfield of $L$ that contains $K$.
- $K(K_1, K_2)$ — the smallest subfield of $L$ containing $K$, $K_1$ and $K_2$.
- **spanning bound** — if a set of $m$ elements spans a vector space, its dimension is at most $m$.
- **Tower law** — for $L : M : K$, $[L:K] = [L:M]\,[M:K]$.

**Your move.** One step, on numbers, not in general. Take $K = \mathbb{Q}$,
$K_1 = \mathbb{Q}(\sqrt{2})$, $K_2 = \mathbb{Q}(\sqrt{3})$, so
$L = \mathbb{Q}(\sqrt{2}, \sqrt{3})$. A basis of $K_1$ over $\mathbb{Q}$ is
$\{1, \sqrt{2}\}$ and a basis of $K_2$ over $\mathbb{Q}$ is $\{1, \sqrt{3}\}$.
Write down a finite set of elements of $L$, built only out of those four, that
spans $L$ over $\mathbb{Q}$ — and say how many elements are in it.
