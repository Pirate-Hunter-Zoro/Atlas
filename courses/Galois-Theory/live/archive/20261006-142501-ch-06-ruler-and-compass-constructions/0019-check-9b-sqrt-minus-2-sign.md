---
kind: lesson
title: check 9b-sqrt-minus-2-sign
---
Your $\mathbb{Q}(\sqrt2)$ factorisation is right, and so is $\mathbb{Q}(i)$. The $\mathbb{Q}(\sqrt{-2})$ one has a sign slip: your boxed product multiplies out to $x^4 + 4x^2 + 1$, not $x^4+1$.

Your first line is right: $x^4+1 = (x^2-1)^2 + 2x^2$. On the second line, $x^2-1$ turned into $x^2+1$. Nothing justifies that change. The $\sqrt{-2}$ belongs only on the $x$ term, since $(\sqrt{-2}\,x)^2 = -2x^2$, so $+2x^2 = -(\sqrt{-2}\,x)^2$. The bracket $(x^2-1)$ stays exactly as it was.

**Problem 9(b).** With $\zeta = \zeta_8$ and $K = \mathbb{Q}(\zeta)$, show that $x^4+1$ factors into quadratics over each of $\mathbb{Q}(\sqrt2)$, $\mathbb{Q}(i)$ and $\mathbb{Q}(\sqrt{-2})$.

What you need:
- $\mathbb{Q}(\sqrt{-2}) = \{a + b\sqrt{-2} : a,b \in \mathbb{Q}\}$, and $(\sqrt{-2})^2 = -2$.
- "Factors into quadratics over $F$": $x^4+1 = (x^2+ax+b)(x^2+cx+d)$ with $a,b,c,d \in F$.
- Difference of squares: $A^2 - B^2 = (A-B)(A+B)$.
- Done: $x^4+1 = (x^2+i)(x^2-i)$ over $\mathbb{Q}(i)$.
- Done: $x^4+1 = (x^2+1-\sqrt2\,x)(x^2+1+\sqrt2\,x)$ over $\mathbb{Q}(\sqrt2)$.

Starting from $x^4+1 = (x^2-1)^2 - (\sqrt{-2}\,x)^2$, write $x^4+1$ as a product of two quadratics with coefficients in $\mathbb{Q}(\sqrt{-2})$.
