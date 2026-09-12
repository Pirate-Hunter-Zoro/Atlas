---
kind: question
title: problem-61-the-lower-limit-is-x
---
**"Where did I fuck up?" — line 2. Your lower limit is $0$; it should be $x$.**

You wrote $\int_0^\infty \lambda^2 e^{-\lambda y}\,dy$. But $f_{X,Y}(x,y)$ is **not** $\lambda^2 e^{-\lambda y}$ for every $y > 0$ — it is that only where $0 < x < y$, and it is **zero** everywhere else. With $x$ held fixed, $y$ values below $x$ are outside the region, so the integrand there is $0$ and they contribute nothing. The integral starts where the region starts, at $y = x$:
$$f_X(x) = \int_x^\infty \lambda^2 e^{-\lambda y}\,dy.$$
That is the whole content of the question I asked, and it is why I asked it before any integrating. An $x$ has to survive into the answer — otherwise $f_X$ would be a constant, which no density on $(0,\infty)$ can be.

**Second, smaller slip, or you will get $\infty$ again.** You set $u = -\lambda y$ and then wrote the integrand as $e^{-u}$. If $u = -\lambda y$ then $e^{-\lambda y} = e^{u}$, not $e^{-u}$ — you negated twice. That double negation is what produced the divergence, not the limits. Don't substitute at all here: an antiderivative of $\lambda^2 e^{-\lambda y}$ with respect to $y$ is $-\lambda e^{-\lambda y}$, by inspection.

---

**Exercise (Ross, Ch. 2, Problem 61), restated in full.**
Let $X$ and $W$ be the working and subsequent repair times of a certain machine. Let $Y = X + W$ and suppose the joint probability density of $X$ and $Y$ is
$$f_{X,Y}(x,y) = \lambda^2 e^{-\lambda y}, \qquad 0 < x < y < \infty.$$

**(a)** Find the density of $X$.
**(b)** Find the density of $Y$.
**(c)** Find the joint density of $X$ and $W$.
**(d)** Find the density of $W$.

*Definitions / symbols used*
- **Joint density** $f_{X,Y}$: probabilities are volumes under it, $P\{(X,Y) \in A\} = \iint_A f_{X,Y}(x,y)\,dx\,dy$. It is **zero** everywhere outside the stated region $0 < x < y < \infty$.
- **Marginal density** $f_X$: integrate the joint density over all values of the *other* variable, $f_X(x) = \int_{-\infty}^{\infty} f_{X,Y}(x,y)\,dy$. The limits that matter are wherever the integrand is nonzero.
- **The region** $0 < x < y < \infty$: $x$ is positive, and $y$ is larger than $x$. Forced by the story — $Y = X + W$ is working time plus repair time, so $Y$ exceeds $X$.
- $\lambda$: a fixed positive constant, not a variable.
- **Exponential density**: $\lambda e^{-\lambda t}$ for $t > 0$. Recognise it when it falls out.

---

**Your turn.** Just part (a), with the corrected lower limit.

Evaluate $\int_x^\infty \lambda^2 e^{-\lambda y}\,dy$ and state $f_X(x)$, saying for which $x$ it holds. Then tell me what familiar density it is.
