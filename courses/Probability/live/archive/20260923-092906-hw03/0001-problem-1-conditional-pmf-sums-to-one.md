---
kind: question
title: problem-1-conditional-pmf-sums-to-one
---
Homework 3 is eight problems from Chapter 3 of Ross, on conditional probability and conditional expectation: 1, 7, 9 or 10, 12, 22, 31, 37 and 40. We take them in that order, so Problem 1 is first. It is short, and it is the identity every later conditioning argument leans on.

---

**Exercise (Homework 3, Problem 1).**
If $X$ and $Y$ are both discrete, show that
$$\sum_{x} p_{X\mid Y}(x \mid y) \;=\; 1$$
for every value $y$ such that $p_Y(y) > 0$.

*Definitions / symbols used*
- **Joint pmf** $p(x,y) = P(X=x,\; Y=y)$: the probability that $X$ lands on $x$ and $Y$ lands on $y$ at the same time.
- **Marginal pmf of $Y$** $p_Y(y) = P(Y=y)$: the probability $Y$ lands on $y$, whatever $X$ did.
- **Conditional pmf** $p_{X\mid Y}(x \mid y) = \dfrac{p(x,y)}{p_Y(y)}$: the probability $X$ lands on $x$ once you already know $Y=y$. It is defined only when $p_Y(y) > 0$, which is why the problem says so.
- $\sum_x$ means: add over every value $X$ is allowed to take, with $y$ held fixed.

---

**Your turn.** One small thing first, on numbers.

Let $X$ take the values $1, 2, 3$ and let $Y$ take the values $1, 2$, with this joint pmf:

| $p(x,y)$ | $x=1$ | $x=2$ | $x=3$ |
|---|---|---|---|
| $y=1$ | $\tfrac18$ | $\tfrac18$ | $\tfrac18$ |
| $y=2$ | $\tfrac14$ | $\tfrac14$ | $\tfrac18$ |

Fix $y = 2$. Give me $p_Y(2)$ first, then the three numbers $p_{X\mid Y}(1\mid 2)$, $p_{X\mid Y}(2\mid 2)$ and $p_{X\mid Y}(3\mid 2)$.

Four numbers, no proof yet: $p_Y(2)$, and the three conditional probabilities $p_{X\mid Y}(x\mid 2)$ for $x = 1, 2, 3$.
