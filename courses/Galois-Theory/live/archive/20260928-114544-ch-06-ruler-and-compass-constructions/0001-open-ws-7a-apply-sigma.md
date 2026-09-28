---
kind: lesson
title: open ws-7a-apply-sigma
---
Chapter 5 is finished, five of five, so this sitting opens the worksheet that replaces chapter 6: *Automorphisms, Irreducibility and Splitting Fields*. We work Problems 7, 8, 9 and 10 in the sheet's order, starting at 7(a).

Why these four: 7 says what an automorphism can do to a root, 8 proves $\Phi_p$ irreducible (Eisenstein again, which you own), 9 runs everything on $\zeta_8$, and 10 is the first splitting field. Each one feeds the next. Problems 11 and 12 are the finite-field pair and wait for their own sheet.

**Problem 7(a).** Let $K/F$ be an extension and $\sigma \in \operatorname{Aut}(K/F)$. Show that if $f \in F[x]$ and $f(\alpha) = 0$ for some $\alpha \in K$, then $f(\sigma(\alpha)) = 0$.

One small check first, on a concrete case. Take $F = \mathbb{Q}$, $K = \mathbb{Q}(i)$, $\sigma$ = complex conjugation, $f(x) = x^2 - 2x + 5$ and $\alpha = 1 + 2i$. Then
$$\alpha^2 - 2\alpha + 5 = 0.$$

- $\operatorname{Aut}(K/F)$: the bijective ring maps $K \to K$ that fix every element of $F$.
- Ring map: $\sigma(a+b) = \sigma(a)+\sigma(b)$ and $\sigma(ab) = \sigma(a)\sigma(b)$.
- Complex conjugation: $\sigma(a+bi) = a - bi$; it fixes $\mathbb{Q}$.

Starting from $\sigma(\alpha^2 - 2\alpha + 5) = \sigma(0)$, reach $\sigma(\alpha)^2 - 2\,\sigma(\alpha) + 5 = 0$ one equality at a time. Beside each equality, name the property of $\sigma$ it uses: adds, multiplies, or fixes $\mathbb{Q}$. Which step needs "fixes $\mathbb{Q}$"?
