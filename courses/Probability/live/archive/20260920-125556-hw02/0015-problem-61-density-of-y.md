---
kind: question
title: problem-61-density-of-y
---
**(a) is right.** $f_X(x) = \lambda e^{-\lambda x}$. The limit is $x$ this time, the substitution is clean, and flipping $\int_{-\lambda x}^{-\infty}$ to $\int_{-\infty}^{-\lambda x}$ is exactly what absorbs the minus sign from $dy = -du/\lambda$. One stray mark: the line before that still reads $e^{-u}$, and you wrote $e^{u}$ on the next line. The second one is the correct one — with $u = -\lambda y$, $e^{-\lambda y} = e^{u}$.

**Two things you were asked for and did not say.** It holds for $x > 0$ — a density is not stated without the set it lives on. And its name: that is the **exponential density with rate $\lambda$**. So the working time is exponential, and $\lambda^2 e^{-\lambda y}$ on that wedge was hiding an ordinary exponential all along.

---

**Exercise (Ross, Ch. 2, Problem 61), restated in full.**
Let $X$ and $W$ be the working and subsequent repair times of a certain machine. Let $Y = X + W$ and suppose the joint probability density of $X$ and $Y$ is
$$f_{X,Y}(x,y) = \lambda^2 e^{-\lambda y}, \qquad 0 < x < y < \infty.$$

**(a)** Find the density of $X$. — done: $f_X(x) = \lambda e^{-\lambda x}$, $x > 0$.
**(b)** Find the density of $Y$.
**(c)** Find the joint density of $X$ and $W$.
**(d)** Find the density of $W$.

*Definitions / symbols used*
- **Joint density** $f_{X,Y}$: $P\{(X,Y) \in A\} = \iint_A f_{X,Y}(x,y)\,dx\,dy$. It is **zero** everywhere outside the stated region $0 < x < y < \infty$.
- **Marginal density** $f_Y$: integrate the joint density over all values of the *other* variable, $f_Y(y) = \int_{-\infty}^{\infty} f_{X,Y}(x,y)\,dx$. The limits that matter are wherever the integrand is nonzero.
- **The region** $0 < x < y < \infty$: $x$ is positive, and $y$ is larger than $x$. Now you are holding $y$ fixed and sweeping $x$, so read the same two inequalities as bounds on $x$.
- $\lambda$: a fixed positive constant, not a variable.
- **Exponential density**: $\lambda e^{-\lambda t}$ for $t > 0$.
- **Gamma density** with parameters $(n, \lambda)$: $\dfrac{\lambda e^{-\lambda t}(\lambda t)^{n-1}}{(n-1)!}$ for $t > 0$. For $n = 1$ it is the exponential.

---

**Your turn.** Part (b).

Compute $f_Y(y) = \int f_{X,Y}(x,y)\,dx$, choosing the limits yourself from the region with $y$ held fixed. State $f_Y(y)$ and the $y$ for which it holds, and tell me which named density it is.
