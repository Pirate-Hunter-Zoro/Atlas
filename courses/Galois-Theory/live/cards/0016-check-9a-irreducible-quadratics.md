---
kind: lesson
title: check 9a-irreducible-quadratics
---
The root is right: $\zeta_8^4 = e^{i\pi} = -1$, so $\zeta_8^4 + 1 = 0$. The irreducibility is not proved. No question on the page.

"No rational roots" only rules out a linear factor. A quartic can still split into two quadratics. It happens: $x^4 + 4$ has no rational roots, yet
$$x^4 + 4 = (x^2 + 2x + 2)(x^2 - 2x + 2).$$
So $x^4+1$ needs an argument that kills a quadratic-times-quadratic factorisation too. Rational-root testing settles irreducibility only in degree 2 and 3.

**Problem 9(a), irreducibility.** Show that $x^4 + 1$ is irreducible over $\mathbb{Q}$.

What you need:
- Eisenstein at a prime $q$: monic, $q$ divides every non-leading coefficient, $q^2$ does not divide the constant term. Then it is irreducible over $\mathbb{Q}$.
- $f(x)$ is irreducible exactly when $f(x+c)$ is, for any $c \in \mathbb{Q}$ (your 8(b) shift).
- Gauss: a monic integer polynomial that factors over $\mathbb{Q}$ factors into monic integer polynomials.

Your root computation and the step "minimal polynomial has degree 4, so $[\mathbb{Q}(\zeta_8):\mathbb{Q}] = 4$" stand once this is done.

Prove that $x^4 + 1$ is irreducible over $\mathbb{Q}$ -- ruling out two quadratic factors, not only linear ones.
