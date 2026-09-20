---
kind: question
title: problem-61-integrate-in-x-not-y
---
---
kind: question
title: problem-61-integrate-in-x-not-y
---
**You integrated the wrong variable.** Line one says $dx$. Line two says $dy$ — and from there the whole page is part (a) again: the same substitution $u = -\lambda y$, the same $\lambda[e^u]$, an answer in the shape of the exponential *distribution function* rather than a density.

Two tells that it cannot be right, both worth learning to spot:

- **The variable of integration must disappear.** You are computing $f_Y(y)$, a function of $y$ alone. If you integrate $dy$, $y$ is used up and cannot survive to the answer — yet your answer still has $y$ in it. The thing you sweep is $x$; the thing that survives is $y$.
- **$\lambda(1 - e^{-\lambda y})$ does not integrate to $1$.** It rises to $\lambda$ and stays there, so its area over $(0,\infty)$ is infinite. That is $\lambda$ times the exponential *cdf*, not any density.

Your limits, though, were right: $0$ to $y$. You read the region correctly. You just swept it with the wrong letter.

---

**Exercise (Ross, Ch. 2, Problem 61), restated in full.**
Let $X$ and $W$ be the working and subsequent repair times of a certain machine. Let $Y = X + W$ and suppose the joint probability density of $X$ and $Y$ is
$$f_{X,Y}(x,y) = \lambda^2 e^{-\lambda y}, \qquad 0 < x < y < \infty.$$

**(a)** Find the density of $X$. — done: $f_X(x) = \lambda e^{-\lambda x}$, $x > 0$.
**(b)** Find the density of $Y$.
**(c)** Find the joint density of $X$ and $W$.
**(d)** Find the density of $W$.

*Definitions / symbols used*
- **Marginal density** $f_Y$: integrate the joint density over all values of the *other* variable — here that is $x$: $f_Y(y) = \int_{-\infty}^{\infty} f_{X,Y}(x,y)\,dx$. Written correctly it has one argument, $f_Y(y)$, not two.
- **The region** $0 < x < y < \infty$: with $y$ held fixed, these are the bounds on $x$ — from $0$ up to $y$.
- $\lambda$: a fixed positive constant, not a variable.
- **Density**: nonnegative, and integrates to $1$ over the set where it lives.
- **Exponential density**: $\lambda e^{-\lambda t}$, $t > 0$. Its cdf is $1 - e^{-\lambda t}$.
- **Gamma density** with parameters $(n, \lambda)$: $\dfrac{\lambda e^{-\lambda t}(\lambda t)^{n-1}}{(n-1)!}$, $t > 0$. For $n = 1$ it is the exponential.

---

**Your turn.** One thing only, and there is no substitution in it.

Hold $y$ fixed. Look at the integrand $\lambda^2 e^{-\lambda y}$ and ask: **where does $x$ appear in it?** Then evaluate $\displaystyle\int_0^{y} \lambda^2 e^{-\lambda y}\,dx$ and tell me what you get.
