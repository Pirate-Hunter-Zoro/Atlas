---
kind: lesson
title: check 10b-degree-six
---
No question on the page. 10(a) is now complete and correct. $\omega \ne 1$ and $\omega^2 \ne 1$ separate $\sqrt[3]{2}$ from the other two, and $\omega^2 = \omega \Rightarrow \omega = 1$ separates those two. Three distinct roots of a cubic are all of its roots. I am writing 10(a) up from your pages now.

**Problem 10(b).** With $\omega = \zeta_3$ and $E = \mathbb{Q}(\sqrt[3]{2}, \omega)$, show that $[E:\mathbb{Q}] = 6$. In particular, $\mathbb{Q}(\sqrt[3]{2})$ contains a root of $x^3 - 2$ but is not its splitting field.

The recipe is the tower $\mathbb{Q} \subseteq \mathbb{Q}(\sqrt[3]{2}) \subseteq E$. Each step's degree is the degree of a minimal polynomial. The bottom step is $3$. The top step is $2$, and that one has to be argued: $\omega$ satisfies a quadratic, and $\omega$ is not already in $\mathbb{Q}(\sqrt[3]{2})$.

What you need:
- $\omega = e^{2\pi i/3} = -\tfrac12 + \tfrac{\sqrt3}{2}i$, a root of $x^2 + x + 1 = (x^3-1)/(x-1)$.
- $[F(\alpha):F]$ equals the degree of the minimal polynomial of $\alpha$ over $F$.
- Eisenstein: if a prime $p$ divides every non-leading coefficient, $p \nmid$ the leading one, and $p^2 \nmid$ the constant, the polynomial is irreducible over $\mathbb{Q}$.
- Tower law: $[E:\mathbb{Q}] = [E:\mathbb{Q}(\sqrt[3]{2})]\,[\mathbb{Q}(\sqrt[3]{2}):\mathbb{Q}]$.
- $E$ is the splitting field of $x^3 - 2$ over $\mathbb{Q}$, by 10(a).

Show that $[E:\mathbb{Q}] = 6$, and conclude that $\mathbb{Q}(\sqrt[3]{2})$ contains a root of $x^3 - 2$ but is not its splitting field.
