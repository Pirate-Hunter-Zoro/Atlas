---
kind: question
title: problem-61-working-and-repair-times
---
**Problem 37 is done, all of it.** All three $X_i \le 0.5$, independence turns that into a product, the product is $x \cdot x \cdots x = x^n$, and differentiating gives $f_M(x) = n x^{n-1}$ on $(0,1)$. The sketch is right too: steeper near $1$ as $n$ grows, because the maximum of many draws piles up near the top of the interval.

Next on the sheet: problem **61**. This is the first *joint density* problem. Everything you did on problem 2 with a joint pmf — sum over the other variable to get the marginal — happens here with an integral instead of a sum, and the entire difficulty is the region the density lives on.

---

**Exercise (Ross, Ch. 2, Problem 61).**
Let $X$ and $W$ be the working and subsequent repair times of a certain machine. Let $Y = X + W$ and suppose that the joint probability density of $X$ and $Y$ is
$$f_{X,Y}(x,y) = \lambda^2 e^{-\lambda y}, \qquad 0 < x < y < \infty.$$

**(a)** Find the density of $X$.
**(b)** Find the density of $Y$.
**(c)** Find the joint density of $X$ and $W$.
**(d)** Find the density of $W$.

*Definitions / symbols used*
- **Joint density** $f_{X,Y}$: the continuous analogue of a joint pmf. Probabilities are areas under it — $P\{(X,Y) \in A\} = \iint_A f_{X,Y}(x,y)\,dx\,dy$. It is **zero** everywhere outside the stated region $0 < x < y < \infty$.
- **Marginal density** $f_X$: obtained by integrating the joint density over all values of the *other* variable, $f_X(x) = \int_{-\infty}^{\infty} f_{X,Y}(x,y)\,dy$. Same move as the row sum you used on problem 2, with $\int dy$ in place of $\sum_{x_2}$.
- **The region** $0 < x < y < \infty$: $x$ is positive and $y$ is larger than $x$. This is forced by the story — $Y = X + W$ is the working time plus a repair time, so $Y$ is always bigger than $X$.
- $\lambda$: a fixed positive constant, not a variable.
- **Exponential density** $\lambda e^{-\lambda t}$ for $t > 0$: a density on the positive half-line. Worth recognising when it falls out of your integral.

---

**Your turn.** One thing, no integration, no answer.

Part (a) wants $f_X(x)$, which means integrating $f_{X,Y}(x,y)$ over $y$ with $x$ held fixed. The limits are the whole problem.

**Fix a particular $x$, say $x = 3$. Over exactly which $y$ values is $f_{X,Y}(3,y)$ nonzero?** State the lower limit and the upper limit of the $y$ integral, and say what in the region $0 < x < y < \infty$ forces each one.
