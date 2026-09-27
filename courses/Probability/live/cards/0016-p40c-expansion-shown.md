---
kind: lesson
title: p40c-expansion-shown
---
**Done. Problem 40(c) now shows the expansion step by step.** The PDF is rebuilt: `homework/hw03/build/hw03.pdf`, 4 pages, 0 warnings.

Part (a) of the variance now reads, in order:

$$S = 0.5\,E[(2+X)^2] + 0.3\,E[(3+X)^2] + 0.2\cdot 0$$

$$(2+X)^2 = 4 + 2\cdot 2X + X^2 = 4 + 4X + X^2 \implies E[(2+X)^2] = 4 + 4\mu + S$$

$$(3+X)^2 = 9 + 2\cdot 3X + X^2 = 9 + 6X + X^2 \implies E[(3+X)^2] = 9 + 6\mu + S$$

$$S = 0.5(4 + 4\mu + S) + 0.3(9 + 6\mu + S) \iff S = 204, \quad \mathrm{Var}(X) = 204 - 9.5^2 = 113.75$$

Here $S = E[X^2]$ and $\mu = E[X] = 9.5$. The middle term of each square is written as $2\cdot 2X$ and $2\cdot 3X$, so the cross term is visible. That is the one place your page had $2X$ instead of $4X$.

Homework 3 is finished: all eight problems written up.
