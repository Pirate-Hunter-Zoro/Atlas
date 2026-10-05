---
kind: lesson
title: check 10a-roots-distinct
---
No question on the page. The reverse inclusion is now right: $\omega = (\omega\sqrt[3]{2})(\sqrt[3]{2})^2/2$ is built from elements of $F$, and $\sqrt[3]{2} \in F$, so $\mathbb{Q}(\sqrt[3]{2}, \omega) \subseteq F$. Both inclusions are done.

One line of 10(a) is still missing. You checked that the three numbers are roots. The problem says they are *the* complex roots, meaning there are no others. That needs them to be three different numbers, because a cubic has at most three roots.

**Problem 10(a), the last line.** Let $\omega = \zeta_3$. Show that $\sqrt[3]{2}$, $\omega\sqrt[3]{2}$, $\omega^2\sqrt[3]{2}$ are pairwise distinct, and conclude they are all the complex roots of $x^3 - 2$.

What you need:
- $\omega = \zeta_3 = e^{2\pi i/3}$, so $\omega^3 = 1$ and $\omega \neq 1$.
- $\sqrt[3]{2}$ is the real cube root of $2$, and $\sqrt[3]{2} \neq 0$.
- A nonzero polynomial of degree $n$ over a field has at most $n$ roots in that field.
- You may cancel a nonzero factor from both sides of an equation in $\mathbb{C}$.

Show the three numbers $\sqrt[3]{2}$, $\omega\sqrt[3]{2}$, $\omega^2\sqrt[3]{2}$ are pairwise distinct, and conclude they are all the complex roots of $x^3 - 2$.
