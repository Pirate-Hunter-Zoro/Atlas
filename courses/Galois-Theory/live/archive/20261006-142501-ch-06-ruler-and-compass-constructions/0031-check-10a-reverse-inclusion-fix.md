---
kind: lesson
title: check 10a-reverse-inclusion-fix
---
No question on the page, so straight to the working. The idea is right: divide a root by $\sqrt[3]{2}$ to get $\omega$. Two things in that line are off.

First, the exponent. With a cube, $(\omega\sqrt[3]{2})(\sqrt[3]{2})^3/2 = \omega\sqrt[3]{2} \cdot 2/2 = \omega\sqrt[3]{2}$, not $\omega$. You want $(\sqrt[3]{2})^2$, since $\sqrt[3]{2}\cdot(\sqrt[3]{2})^2 = 2$.

Second, the field. For $\supseteq$ you must show $\omega$ lies in the field of roots, $F = \mathbb{Q}(\sqrt[3]{2}, \omega\sqrt[3]{2}, \omega^2\sqrt[3]{2})$. Saying a factor lies in $\mathbb{Q}(\sqrt[3]{2}, \omega)$ proves nothing here; that field already contains $\omega$. Each factor in your product has to be in $F$, and you should say why it is.

**Problem 10(a), reverse inclusion.** Let $\omega = \zeta_3$. Show that $\mathbb{Q}(\sqrt[3]{2}, \omega) \subseteq \mathbb{Q}(\sqrt[3]{2}, \omega\sqrt[3]{2}, \omega^2\sqrt[3]{2})$.

What you need:
- $\omega = \zeta_3 = e^{2\pi i/3}$, so $\omega^3 = 1$.
- $\sqrt[3]{2}$ is the real cube root of $2$, so $(\sqrt[3]{2})^3 = 2$ and $\sqrt[3]{2} \neq 0$.
- $F = \mathbb{Q}(\sqrt[3]{2}, \omega\sqrt[3]{2}, \omega^2\sqrt[3]{2})$ is the smallest field containing $\mathbb{Q}$ and those three roots.
- A field is closed under multiplication and under division by nonzero elements.
- $\mathbb{Q}(a, b) \subseteq F$ exactly when $a \in F$ and $b \in F$.

Write $\omega$ as a product or quotient of elements you can show are in $F$, say why each one is in $F$, and conclude $\mathbb{Q}(\sqrt[3]{2}, \omega) \subseteq F$.
