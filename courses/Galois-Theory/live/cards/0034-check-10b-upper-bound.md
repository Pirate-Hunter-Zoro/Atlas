---
kind: lesson
title: check 10b-upper-bound
---
Divisibility only gives a floor: $6 \mid [E:\mathbb{Q}]$ says the degree is $6$, $12$, $18$, and so on. To pin it at $6$ you need a ceiling, $[E:\mathbb{Q}] \le 6$. Lower bound plus upper bound gives equality. Your route is good, and it is cleaner than the one I suggested: it never needs to show $\omega \notin \mathbb{Q}(\sqrt[3]{2})$.

The ceiling comes from the tower $\mathbb{Q} \subseteq \mathbb{Q}(\sqrt[3]{2}) \subseteq E = \mathbb{Q}(\sqrt[3]{2})(\omega)$. The bottom step is $3$. So you only need the top step to be at most $2$.

The polynomial you were missing is $x^2 + x + 1$. Since $\omega^3 = 1$ and $\omega \ne 1$, dividing $\omega^3 - 1 = 0$ by $\omega - 1$ gives $\omega^2 + \omega + 1 = 0$. It is irreducible over $\mathbb{Q}$ because its roots $\omega, \omega^2$ are not real, so it has no rational root. That gives $[\mathbb{Q}(\omega):\mathbb{Q}] = 2$, which is your $2 \mid [E:\mathbb{Q}]$.

**Problem 10(b).** With $\omega = \zeta_3$ and $E = \mathbb{Q}(\sqrt[3]{2}, \omega)$, show that $[E:\mathbb{Q}] = 6$. In particular, $\mathbb{Q}(\sqrt[3]{2})$ contains a root of $x^3 - 2$ but is not its splitting field.

What you need:
- $\omega = e^{2\pi i/3}$ is a root of $x^2 + x + 1$, irreducible over $\mathbb{Q}$.
- $[F(\alpha):F]$ equals the degree of the minimal polynomial of $\alpha$ over $F$.
- The minimal polynomial of $\alpha$ over $F$ divides every polynomial in $F[x]$ that has $\alpha$ as a root.
- Tower law: $[E:\mathbb{Q}] = [E:\mathbb{Q}(\sqrt[3]{2})]\,[\mathbb{Q}(\sqrt[3]{2}):\mathbb{Q}]$, and the same through $\mathbb{Q}(\omega)$.
- You have already: $2 \mid [E:\mathbb{Q}]$ and $3 \mid [E:\mathbb{Q}]$, so $6 \mid [E:\mathbb{Q}]$.
- $E$ is the splitting field of $x^3 - 2$ over $\mathbb{Q}$, by 10(a).

Show that $[E:\mathbb{Q}(\sqrt[3]{2})] \le 2$, and use it to conclude $[E:\mathbb{Q}] = 6$ and that $\mathbb{Q}(\sqrt[3]{2})$ is not the splitting field of $x^3 - 2$.
