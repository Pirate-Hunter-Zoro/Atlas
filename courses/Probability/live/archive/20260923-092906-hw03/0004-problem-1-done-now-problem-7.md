---
kind: correct
title: problem-1-done-now-problem-7
---
That is the proof, finished and correct. You dropped the stray $\sum_y$, pulled $1/p_Y(y)$ out of the sum because $y$ is fixed, and then recognised $\sum_x p_X(x)\,p_{Y\mid X}(y\mid x) = p_Y(y)$ — the marginal of $Y$, rebuilt from the joint. That last equality was the step missing from both earlier attempts. Your $\therefore$ is earned.

Problem 1 is now typeset in `homework/hw03/hw03.tex` with your argument in the solution region, and your page is filed beside it.

---

**Exercise (Homework 3, Problem 7).**
The joint probability mass function of $X$, $Y$, $Z$ is

$$
\begin{array}{ll}
p(1,1,1) = \tfrac{1}{8}, & p(2,1,1) = \tfrac{1}{4},\\[2pt]
p(1,1,2) = \tfrac{1}{8}, & p(2,1,2) = \tfrac{3}{16},\\[2pt]
p(1,2,1) = \tfrac{1}{16}, & p(2,2,1) = 0,\\[2pt]
p(1,2,2) = 0, & p(2,2,2) = \tfrac{1}{4}.
\end{array}
$$

Find $E[X \mid Y = 2]$ and $E[X \mid Y = 2,\, Z = 1]$.

*Definitions / symbols used*
- **Joint pmf** $p(x,y,z) = P(X=x,\,Y=y,\,Z=z)$: the chance all three land on those values at once.
- **Marginal pmf of $Y$** $p_Y(y) = \sum_{x}\sum_{z} p(x,y,z)$: fix $y$, add every cell that has it.
- **Conditional pmf** $p_{X\mid Y}(x\mid y) = p_{X,Y}(x,y)/p_Y(y)$, defined when $p_Y(y) > 0$.
- **Conditional expectation** $E[X \mid Y = y] = \sum_{x} x\,p_{X\mid Y}(x\mid y)$: the average of $X$ over only those outcomes where $Y = y$.
- $X$ takes the values $1$ and $2$ here, and so do $Y$ and $Z$.

---

**Your turn.** The denominator, and nothing else.

Four of those eight entries have $y = 2$. Name them and add them, to get $p_Y(2)$.

Give me the four probabilities you used and the total.
