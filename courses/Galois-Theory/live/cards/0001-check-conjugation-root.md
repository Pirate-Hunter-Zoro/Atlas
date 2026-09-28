---
kind: lesson
title: check conjugation-root
---
Chapter 6 is skipped, as you chose; this sitting works the worksheet that replaces it, `worksheet-automorphisms-splitting-fields`, Problems 7 to 10 in the sheet's order. Those four are the whole sheet here: 7 and 8 build the tools, 9 and 10 spend them on roots of unity. Problems 11 and 12, the finite-field pair, get their own sheet.

The first exercise is 7(a). Let $K/F$ be an extension and $\sigma \in \operatorname{Aut}(K/F)$. Show that if $f \in F[x]$ and $f(\alpha)=0$ for some $\alpha \in K$, then $f(\sigma(\alpha))=0$.

Before the general case, one concrete instance. Take $K=\mathbb{C}$, $F=\mathbb{Q}$, $\sigma(z)=\bar z$ (complex conjugation), and $\alpha = 1+2i$, a root of $f(x)=x^2-2x+5$.

- $\operatorname{Aut}(K/F)$: bijections $K \to K$ with $\sigma(a+b)=\sigma(a)+\sigma(b)$ and $\sigma(ab)=\sigma(a)\sigma(b)$ that fix every element of $F$.
- "Fixes $\mathbb{Q}$": $\sigma(c)=c$ for every rational $c$.
- $f(\alpha)=0$ means $\alpha^2-2\alpha+5=0$.

Your move: starting from $\sigma(\alpha^2-2\alpha+5)=\sigma(0)$, push $\sigma$ through one equality per line until you reach $\sigma(\alpha)^2-2\sigma(\alpha)+5=0$. Label each line "adds", "multiplies" or "fixes $\mathbb{Q}$". Say which lines need "fixes $\mathbb{Q}$", and why $\sigma(0)=0$.
