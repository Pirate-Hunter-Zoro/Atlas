---
kind: lesson
title: check 9b-difference-of-squares
---
The trick is to add and subtract a middle term so $x^4+1$ becomes a difference of two squares. Then $A^2 - B^2 = (A-B)(A+B)$ does the rest.

You already did this over $\mathbb{Q}(i)$, and it is right: $x^4 + 1 = x^4 - i^2 = (x^2+i)(x^2-i)$. That case is done.

Your $\mathbb{Q}(\sqrt2)$ attempt, $(x^2+\sqrt2)(x^2-\sqrt2)+3$, is true but is not a product. The $+3$ is the problem. Using $\sqrt2$ on the constant term only gives $x^4 - 2$, the wrong constant. Put $\sqrt2$ on the $x$ term instead:

$$x^4 + 1 = (x^2+1)^2 - 2x^2.$$

Here $2x^2$ is a square once $\sqrt2$ is allowed. For $\mathbb{Q}(\sqrt{-2})$, subtract instead of add:

$$x^4 + 1 = (x^2-1)^2 + 2x^2.$$

Ask which number squares to $-2$.

**Problem 9(b).** With $\zeta = \zeta_8$ and $K = \mathbb{Q}(\zeta)$, show that $x^4+1$ factors into quadratics over each of $\mathbb{Q}(\sqrt2)$, $\mathbb{Q}(i)$ and $\mathbb{Q}(\sqrt{-2})$.

What you need:
- $\mathbb{Q}(\sqrt2) = \{a + b\sqrt2 : a,b \in \mathbb{Q}\}$, and likewise $\mathbb{Q}(i)$, $\mathbb{Q}(\sqrt{-2})$.
- "Factors into quadratics over $F$": $x^4+1 = (x^2+ax+b)(x^2+cx+d)$ with $a,b,c,d \in F$.
- An explicit factorisation, multiplied out, is a complete proof.
- Difference of squares: $A^2 - B^2 = (A-B)(A+B)$.
- Done: over $\mathbb{Q}(i)$, $x^4+1 = (x^2+i)(x^2-i)$.

Use the two identities above to write $x^4+1$ as a product of two quadratics with coefficients in $\mathbb{Q}(\sqrt2)$, and then in $\mathbb{Q}(\sqrt{-2})$.
