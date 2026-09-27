---
kind: lesson
title: ws-7a-check-conjugation
---
The check on the board is still open: push complex conjugation through one polynomial equation, one step at a time. It is the whole of Problem 7(a) on a single example, so the general proof will be this computation with letters.

**Problem 7(a).** Let $K/F$ be an extension and $\sigma \in \operatorname{Aut}(K/F)$. Show that if $f \in F[x]$ and $f(\alpha) = 0$ for some $\alpha \in K$, then $f(\sigma(\alpha)) = 0$.

**The check.** Take $F = \mathbb{Q}$, $K = \mathbb{Q}(i)$, $\sigma$ = complex conjugation, $f(x) = x^2 - 2x + 5$ and $\alpha = 1 + 2i$. Then
$$\alpha^2 - 2\alpha + 5 = 0.$$

- $K/F$: a field $K$ containing the field $F$.
- $\operatorname{Aut}(K/F)$: the bijective ring maps $K \to K$ that fix every element of $F$.
- Ring map: $\sigma(a+b) = \sigma(a)+\sigma(b)$ and $\sigma(ab) = \sigma(a)\sigma(b)$.
- Complex conjugation: $\sigma(a+bi) = a - bi$; it fixes every rational number.

Start from $\sigma(\alpha^2 - 2\alpha + 5) = \sigma(0)$ and reach $\sigma(\alpha)^2 - 2\,\sigma(\alpha) + 5 = 0$, one equality per line. Beside each equality, write which property it uses: adds, multiplies, or fixes $\mathbb{Q}$. Then say which step needs "fixes $\mathbb{Q}$".
