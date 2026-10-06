---
kind: lesson
title: check 10a-reverse-inclusion
---
The cubes are right, and the inclusion you wrote is right: both new roots lie in $\mathbb{Q}(\sqrt[3]{2}, \omega)$. That is only half of the equality. You still need the other direction, $\mathbb{Q}(\sqrt[3]{2}, \omega) \subseteq \mathbb{Q}(\sqrt[3]{2}, \omega\sqrt[3]{2}, \omega^2\sqrt[3]{2})$. The left field has $\omega$ as a generator, and the right field is not given $\omega$. So you must build $\omega$ out of the roots.

One more line belongs beside it. The three roots are distinct, because $1, \omega, \omega^2$ are. A cubic has at most three roots, so these are all of them.

**Problem 10(a).** Let $\omega = \zeta_3$. Show that the complex roots of $x^3 - 2$ are $\sqrt[3]{2}$, $\omega\sqrt[3]{2}$ and $\omega^2\sqrt[3]{2}$. Conclude that its splitting field over $\mathbb{Q}$ is $E = \mathbb{Q}(\sqrt[3]{2}, \omega)$.

What you need:
- $\omega = \zeta_3 = e^{2\pi i/3}$, so $\omega^3 = 1$ and $1, \omega, \omega^2$ are distinct.
- $\sqrt[3]{2}$ is the real cube root of $2$, so $\sqrt[3]{2} \neq 0$.
- A polynomial of degree $n$ has at most $n$ roots in $\mathbb{C}$.
- Splitting field of $f$ over $\mathbb{Q}$: $\mathbb{Q}(\alpha_1, \dots, \alpha_n)$, where $\alpha_1, \dots, \alpha_n$ are all the complex roots of $f$.
- A field is closed under division by nonzero elements.

Show that $\omega \in \mathbb{Q}(\sqrt[3]{2}, \omega\sqrt[3]{2}, \omega^2\sqrt[3]{2})$, so that $\mathbb{Q}(\sqrt[3]{2}, \omega) \subseteq \mathbb{Q}(\sqrt[3]{2}, \omega\sqrt[3]{2}, \omega^2\sqrt[3]{2})$.
