---
kind: lesson
title: check 7c-one-generator
---
Your question "why does this make $\sigma=\tau$?" is answered by 7(b) with a single generator. $K=\mathbb{Q}(\zeta_n)$ is generated over $\mathbb{Q}$ by one element, $\alpha_1=\zeta_n$. So 7(b) says an automorphism of $K$ fixing $\mathbb{Q}$ is determined by where it sends $\zeta_n$. You showed $\sigma(\zeta_n)=\tau(\zeta_n)$, so $\sigma=\tau$. That is injectivity.

Your $x$ is 7(b) in miniature. Every element of $K$ is $p(\zeta_n)$ for a rational polynomial $p$, and $\sigma(p(\zeta_n))=p(\sigma(\zeta_n))$. So $\sigma$ of anything depends only on $\sigma(\zeta_n)$.

Your setup is right: $k\equiv k' \pmod n$ gives $\zeta_n^{k'}=\zeta_n^{k}$, and the $e^{2\pi i hn/n}=1$ step is clean.

One line is still a jump. You wrote $\sigma(x)=3-\zeta_n^{k}+5\zeta_n^{2k}$ straight from $x$. The step $\sigma(\zeta_n^{2})=\sigma(\zeta_n)^{2}$ is missing, and that is the only place "$\sigma$ is an automorphism" is used.

What it uses:

- $\zeta_n=e^{2\pi i/n}$ and $K=\mathbb{Q}(\zeta_n)$.
- $\sigma(a+b)=\sigma(a)+\sigma(b)$ (additive).
- $\sigma(ab)=\sigma(a)\sigma(b)$ (multiplicative).
- $\sigma(q)=q$ for $q\in\mathbb{Q}$ (fixes $\mathbb{Q}$).
- $\sigma(\zeta_n)=\zeta_n^{k}$.

So: expand $\sigma(5\zeta_n^{2})$ one line at a time until you reach $5\zeta_n^{2k}$, and name which of the three rules each line uses.
