---
kind: lesson
title: p40c-done-hw03-complete
---
**Yes, the concept is right, and $\mathrm{Var}(X) = \tfrac{17}{4}$ days$^2$.** You skipped my sub-question and went straight to the distribution of $X$. That route is cleaner, and every probability in it is right.

Your table under model (b), where he never repeats a door:

| $x$ | paths | $P(X = x)$ |
|---|---|---|
| 5 | 1,2,3 or 2,1,3 | $\tfrac13$ |
| 2 | 1,3 | $\tfrac16$ |
| 3 | 2,3 | $\tfrac16$ |
| 0 | 3 | $\tfrac13$ |

The plug and chug:

$$S = E[X^2] = \tfrac13\cdot 25 + \tfrac16\cdot 4 + \tfrac16\cdot 9 = \tfrac{50}{6} + \tfrac{13}{6} = \tfrac{63}{6} = \tfrac{21}{2}.$$

$$\mathrm{Var}(X) = S - \mu^2 = \tfrac{21}{2} - \tfrac{25}{4} = \tfrac{17}{4}.$$

The same table also checks your mean: $\tfrac{5}{3} + \tfrac{2}{6} + \tfrac{3}{6} = \tfrac52$. It matches.

This fixes last turn's error without you having to name it. Summing $x^2\,P(X=x)$ squares each value before averaging. Squaring the conditional mean did it the other way round.

**Homework 3 is finished.** Problem 40 was the last of the eight. The file `homework/hw03/hw03.tex` now holds your model (b) argument in part (c), with your page filed beside it and the PDF rebuilt.
