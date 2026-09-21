---
kind: correct
title: problem-7-done-now-problem-9
---
Both boxes are right: $E[X \mid Y = 2] = 1.8$ and $E[X \mid Y = 2,\, Z = 1] = 1$.

You never wrote $p_Y(2)$ down on its own, but it is inside your "normalized" step: $\tfrac{1}{16}$ and $\tfrac{4}{16}$ over their total $\tfrac{5}{16}$ give $0.2$ and $0.8$. That total is exactly the marginalisation you proved in Problem 1, now with numbers in it. The second part you read straight off the cells — $y=2, z=1$ leaves $p(1,2,1)=\tfrac{1}{16}$ and $p(2,2,1)=0$, so $X=1$ carries all the mass and the average of a constant is that constant. "Only possibility" is the right reason.

Problem 7 is now typeset in `homework/hw03/hw03.tex` with your working, and your page is filed beside it.

---

**Exercise (Homework 3, Problem 9).**
Show, in the discrete case, that if $X$ and $Y$ are independent then
$$
E[X \mid Y = y] = E[X] \qquad \text{for all } y .
$$

*Definitions / symbols used*
- **Independence (discrete)**: $p(x,y) = p_X(x)\,p_Y(y)$ for every pair $(x,y)$ — this is given here, unlike in Problem 1.
- **Joint pmf** $p(x,y) = P(X=x,\,Y=y)$.
- **Marginal pmf** $p_X(x) = \sum_y p(x,y)$, and likewise $p_Y(y) = \sum_x p(x,y)$.
- **Conditional pmf** $p_{X \mid Y}(x \mid y) = p(x,y)/p_Y(y)$, defined when $p_Y(y) > 0$.
- **Conditional expectation** $E[X \mid Y = y] = \sum_x x\,p_{X \mid Y}(x \mid y)$.
- **Expectation** $E[X] = \sum_x x\,p_X(x)$.
- $y$ is fixed throughout; the sums run over $x$ alone.

---

**Your turn.** One line, before the proof. Under independence, $p_{X \mid Y}(x \mid y)$ is equal to which of these three?

$$
\text{(a)}\ \ p_X(x)\,p_Y(y) \qquad \text{(b)}\ \ p_X(x) \qquad \text{(c)}\ \ \frac{p_X(x)}{p_Y(y)}
$$

Pick one and name the cancellation that gets you there.

Then the exercise itself: show that if $X$ and $Y$ are discrete and independent, $E[X \mid Y = y] = E[X]$ for every $y$ with $p_Y(y) > 0$.
