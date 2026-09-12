---
kind: correct
title: $p = x+2$, $q = 2x$. Correct — and that was the proof in miniature.
---

Correct. $\dfrac{\tfrac12 x + 1}{x} = \dfrac{x+2}{2x}$, and the check is the relation you wrote earlier: $(\tfrac12 x + 1)\cdot 2x = x \cdot (x+2)$, both sides $x^2 + 2x$. Same class, and now both entries sit in $\mathbb{Z}[x]$.

The step that carried it: you multiplied numerator and denominator by $2$ — the denominator of the offending coefficient. Nothing else happened.

That move is not a trick for this example. It is the whole of the hard direction of 3.2. Everything up to now was setting up the two ends of $\phi$; you are now inside the proof.

To see why, notice what you have just shown: an element of $\mathbb{Q}(x)$, written with rational coefficients, *is* an element of $\operatorname{Frac}(\mathbb{Z}[x])$ — it was only the choice of representative that made it look otherwise. That is surjectivity of $\phi$, in the case $R = \mathbb{Z}$, $n = 1$, for one element.

So the next thing is to do it for every element, and the only question is whether the multiplier always exists.

**Your move.** Take an arbitrary $a/b \in \mathbb{Q}(x)$, with $a, b \in \mathbb{Q}[x]$ and $b \neq 0$. Name the integer $d$ you would multiply numerator and denominator by — and say why such a $d$ always exists, whatever $a$ and $b$ are.
