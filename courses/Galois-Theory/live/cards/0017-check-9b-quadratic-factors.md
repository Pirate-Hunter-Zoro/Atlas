---
kind: lesson
title: check 9b-quadratic-factors
---
9(a) is right and complete. $(x+1)^4 + 1 = x^4 + 4x^3 + 6x^2 + 4x + 2$ is Eisenstein at $2$: $2$ divides $4, 6, 4, 2$ and $4 \nmid 2$. So $x^4+1$ is irreducible, it is the minimal polynomial of $\zeta_8$, and $[\mathbb{Q}(\zeta_8):\mathbb{Q}] = 4$. No question on the page; the bottom-right "$p \in \mathbb{Q}(\zeta_p^k)$" is left over from 8(c). The write-up now has 9(a) as you wrote it.

So $x^4+1$ has no factor over $\mathbb{Q}$. Over a slightly bigger field it does.

**Problem 9(b).** With $\zeta = \zeta_8$ and $K = \mathbb{Q}(\zeta)$, show that $x^4 + 1$ factors into quadratics over each of $\mathbb{Q}(\sqrt{2})$, $\mathbb{Q}(i)$ and $\mathbb{Q}(\sqrt{-2})$.

What you need:
- $\mathbb{Q}(\sqrt{2}) = \{a + b\sqrt{2} : a, b \in \mathbb{Q}\}$, and likewise $\mathbb{Q}(i)$, $\mathbb{Q}(\sqrt{-2})$.
- "Factors into quadratics over $F$": $x^4 + 1 = (x^2 + ax + b)(x^2 + cx + d)$ with $a, b, c, d \in F$.
- An explicit factorisation, multiplied out, is a complete proof. No irreducibility argument is asked for.

Write $x^4 + 1$ as a product of two quadratics with coefficients in $\mathbb{Q}(\sqrt{2})$, then in $\mathbb{Q}(i)$, then in $\mathbb{Q}(\sqrt{-2})$.
