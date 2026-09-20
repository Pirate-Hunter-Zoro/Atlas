---
kind: question
title: problem-61-region-in-x-and-w
---
**That is (b), correct.** $\int_0^{y} \lambda^2 e^{-\lambda y}\,dx = \lambda^2 y e^{-\lambda y}$ — $x$ never appears in the integrand, so sweeping it from $0$ to $y$ just multiplies by the length $y$. And $y$ survives, as it must.

That answer has a name: it is the **gamma density with parameters $(2, \lambda)$** — put $n = 2$ into $\lambda e^{-\lambda t}(\lambda t)^{n-1}/(n-1)!$ and you get $\lambda^2 t e^{-\lambda t}$. Sensible: $Y$ is the sum of two exponential waits.

One notation fix, the same one twice. You wrote $f_Y(x,y)$ on the first and last lines. A marginal of $Y$ is a function of $y$ alone — $x$ was integrated away, so it cannot be an argument. Write $f_Y(y)$.

---

**Exercise (Ross, Ch. 2, Problem 61), restated in full.**
Let $X$ and $W$ be the working and subsequent repair times of a certain machine. Let $Y = X + W$ and suppose the joint probability density of $X$ and $Y$ is
$$f_{X,Y}(x,y) = \lambda^2 e^{-\lambda y}, \qquad 0 < x < y < \infty.$$

**(a)** Density of $X$. — done: $f_X(x) = \lambda e^{-\lambda x}$, $x > 0$.
**(b)** Density of $Y$. — done: $f_Y(y) = \lambda^2 y e^{-\lambda y}$, $y > 0$.
**(c)** Find the joint density of $X$ and $W$.
**(d)** Find the density of $W$.

*Definitions / symbols used*
- $W$ is the repair time, and $Y = X + W$ is the total. So $W = Y - X$ — repair time is total minus working time.
- **The region** $0 < x < y < \infty$: the joint density is $\lambda^2 e^{-\lambda y}$ on this set and $0$ everywhere else. A joint density is not complete without the set it lives on.
- **Change of variables**: to get $f_{X,W}$ from $f_{X,Y}$ you rewrite the *formula* in the new letters, multiply by a Jacobian factor, and rewrite the *region* in the new letters. Part (c) is those three jobs. You are doing the third one first.
- $\lambda$: a fixed positive constant.

---

**Your turn.** The region only — no density, no calculus, no Jacobian.

The old region is the pair of inequalities $0 < x$ and $x < y$. Substitute $y = x + w$ into both of them, and simplify. **What conditions on $x$ and $w$ come out?**
