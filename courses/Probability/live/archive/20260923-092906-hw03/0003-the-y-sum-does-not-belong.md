---
kind: question
title: the-y-sum-does-not-belong
---
Dropping independence was the right move, and the replacement is a genuine identity: $p(x,y) = p_X(x)\,p_{Y\mid X}(y\mid x)$ holds for every joint pmf. What breaks the line is the $\sum_y$ you put next to it.

In Problem 1, $y$ is fixed. It is one particular value, handed to you, with $p_Y(y) > 0$. The left side sums over $x$ alone. Your second line sums over $x$ and $y$ both, so the two sides are no longer the same quantity — over the table below, the left is 3 terms and the right is 6.

The denominator stops the last step as well. In $\sum_y p_X(x)\,p_{Y\mid X}(y\mid x) \big/ p_Y(y)$, the $p_Y(y)$ underneath moves as $y$ moves, so it cannot sit outside the sum, and $\sum_y p_{Y\mid X}(y\mid x) = 1$ never gets used. "$x$ has to occur with some $y$" is a true sentence. It is not the one this proof needs.

The one it needs is still unused: with $y$ held fixed, $p_Y(y)$ is itself a sum over $x$.

---

**Exercise (Homework 3, Problem 1).**
If $X$ and $Y$ are both discrete, show that
$$\sum_{x} p_{X\mid Y}(x \mid y) \;=\; 1$$
for every value $y$ with $p_Y(y) > 0$. No independence assumed.

*Definitions / symbols used*
- **Joint pmf** $p(x,y) = P(X=x,\; Y=y)$: the chance $X$ lands on $x$ and $Y$ lands on $y$ together.
- **Marginal pmf of $X$** $p_X(x) = P(X=x)$: the chance $X$ lands on $x$, whatever $Y$ did.
- **Marginal pmf of $Y$** $p_Y(y) = P(Y=y)$, likewise.
- **Conditional pmf** $p_{X\mid Y}(x\mid y) = \dfrac{p(x,y)}{p_Y(y)}$, defined only when $p_Y(y) > 0$.
- **Chain rule** $p(x,y) = p_X(x)\,p_{Y\mid X}(y\mid x)$: always true, no assumption.
- **$y$ is fixed**: the claim is about one value of $y$ at a time, so nothing in the proof sums over $y$.

---

**Your turn.** One row of the table.

| $p(x,y)$ | $x=1$ | $x=2$ | $x=3$ |
|---|---|---|---|
| $y=1$ | $\tfrac18$ | $\tfrac18$ | $\tfrac18$ |
| $y=2$ | $\tfrac14$ | $\tfrac14$ | $\tfrac18$ |

Fix $y = 2$ and add the three joint probabilities along that row: $p(1,2) + p(2,2) + p(3,2)$.

Give me that total, and tell me which of the quantities in the list above it is equal to.
