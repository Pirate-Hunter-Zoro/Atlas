---
kind: lesson
title: check roots-to-roots
---
Today is the worksheet that replaces Chapter 6: Problems 7 to 10, in the sheet's order, starting with 7(a). Problem 7 is the engine for the rest. Problems 8 to 10 compute automorphism groups of roots-of-unity fields, and every one of those computations leans on 7(a) and 7(b). None of the 14 parts is written up yet.

**Problem 7(a).** Let $K/F$ be an extension and $\sigma \in \operatorname{Aut}(K/F)$. If $f \in F[x]$ and $f(\alpha) = 0$ for some $\alpha \in K$, then $f(\sigma(\alpha)) = 0$.

Before the general case, one concrete instance. Take $K = \mathbb{C}$, $F = \mathbb{Q}$, and $\sigma$ complex conjugation, $\sigma(a + bi) = a - bi$. Take $\alpha = 1 + 2i$, a root of $f(x) = x^2 - 2x + 5$.

What you have to work with:
- $\operatorname{Aut}(K/F)$: the ring isomorphisms $K \to K$ that fix every element of $F$.
- adds: $\sigma(u + v) = \sigma(u) + \sigma(v)$.
- multiplies: $\sigma(uv) = \sigma(u)\,\sigma(v)$.
- fixes $\mathbb{Q}$: $\sigma(c) = c$ for every $c \in \mathbb{Q}$.
- The starting fact: $\alpha^2 - 2\alpha + 5 = 0$.

Your move: start from $\sigma(\alpha^2 - 2\alpha + 5) = \sigma(0)$ and push $\sigma$ inward until you reach $\sigma(\alpha)^2 - 2\sigma(\alpha) + 5 = 0$. Write one equality per line. Label each line adds, multiplies or fixes $\mathbb{Q}$. Say which lines need fixes $\mathbb{Q}$, and why $\sigma(0) = 0$.
