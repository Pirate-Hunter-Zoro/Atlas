---
kind: question
title: independence-is-not-given
---
Yes, there is more to it: independence is not given, and the table below does not have it. Problem 1 says only that $X$ and $Y$ are discrete. The identity has to hold for every joint pmf, including ones where $X$ and $Y$ lean on each other hard, so a proof that uses independence proves a special case.

Your second line is where it enters. $\sum_x p_{X\mid Y}(x\mid y) = \sum_x p_X(x)$ is true exactly when $p_{X\mid Y}(x\mid y) = p_X(x)$, which is the definition of independence. Without it, $p_{X\mid Y}(x\mid 2)$ and $p_X(x)$ are different numbers.

The step that actually carries the proof is one you have not used yet: $p_Y(y)$ is itself a sum over $x$.

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
- **$X$ and $Y$ independent** means $p(x,y) = p_X(x)\,p_Y(y)$ for every pair. This is an extra assumption, not a fact.

---

**Your turn.** One number, to see the assumption break.

| $p(x,y)$ | $x=1$ | $x=2$ | $x=3$ |
|---|---|---|---|
| $y=1$ | $\tfrac18$ | $\tfrac18$ | $\tfrac18$ |
| $y=2$ | $\tfrac14$ | $\tfrac14$ | $\tfrac18$ |

Add the $x=1$ column to get $p_X(1)$. Add the $y=2$ row to get $p_Y(2)$. Multiply them.

Give me $p_X(1)$, $p_Y(2)$, and the product $p_X(1)\,p_Y(2)$, and say whether that product equals the $1/4$ sitting in the table at $p(1,2)$.
