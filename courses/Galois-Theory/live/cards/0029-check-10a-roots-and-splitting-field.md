---
kind: lesson
title: check 10a-roots-and-splitting-field
---
Correct, and 9(d) is finished. $\sqrt{-2} = \zeta + \zeta^3$ from the cosines, $\sigma_3$ swaps the two terms because $\zeta^9 = \zeta$, and the squeeze closes it. Two copy-slips from your $\sigma_7$ page: you labelled the map $\sigma_7$, and the last line says $\mathbb{Q}(\sqrt2)$. The write-up reads $\sigma_3$ and $\mathbb{Q}(\sqrt{-2})$. It also spells out the degree: $[\mathbb{Q}(\sqrt{-2}):\mathbb{Q}] = 2$ and $[K:\mathbb{Q}] = 4$ give $[K:\mathbb{Q}(\sqrt{-2})] = 2$ by the tower law.

Problem 10 is the first splitting field that is not cyclotomic.

**Problem 10(a).** Let $\omega = \zeta_3$. Show that the complex roots of $x^3 - 2$ are $\sqrt[3]{2}$, $\omega\sqrt[3]{2}$ and $\omega^2\sqrt[3]{2}$. Conclude that its splitting field over $\mathbb{Q}$ is $E = \mathbb{Q}(\sqrt[3]{2}, \omega)$.

What you need:
- $\omega = \zeta_3 = e^{2\pi i/3}$, so $\omega^3 = 1$ and $1, \omega, \omega^2$ are distinct.
- $\sqrt[3]{2}$ is the real cube root of $2$.
- A polynomial of degree $n$ has at most $n$ roots in $\mathbb{C}$.
- Splitting field of $f$ over $\mathbb{Q}$: $\mathbb{Q}(\alpha_1, \dots, \alpha_n)$, where $\alpha_1, \dots, \alpha_n$ are all the complex roots of $f$.

The recipe: cube each candidate, count them, then show the two fields contain each other's generators. The only step with content is getting $\omega$ back out of the roots.

Show that the roots of $x^3 - 2$ are $\sqrt[3]{2}$, $\omega\sqrt[3]{2}$, $\omega^2\sqrt[3]{2}$, and that $\mathbb{Q}(\sqrt[3]{2}, \omega\sqrt[3]{2}, \omega^2\sqrt[3]{2}) = \mathbb{Q}(\sqrt[3]{2}, \omega)$.
