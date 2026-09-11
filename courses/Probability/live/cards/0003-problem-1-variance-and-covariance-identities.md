---
kind: question
title: Problem 1 – Variance and covariance identities
---
$5/16$ is right. $\binom{5}{3}=10$, $(1/2)^3(1/2)^2 = 1/32$, and $10/32 = 5/16$. Nothing to fix.

That coin question was a warm-up, not the assignment. Here is the real Problem 1 from the sheet.

---

**Exercise (Homework 2, Problem 1).**
Let $X$, $Y$ and $Z$ be random variables and let $c$ be a number. Prove that
$$\operatorname{Var}(cX) = c^2\operatorname{Var}(X),$$
$$\operatorname{Cov}(cX, Y) = c\operatorname{Cov}(X, Y),$$
$$\operatorname{Cov}(X+Y, Z) = \operatorname{Cov}(X, Z) + \operatorname{Cov}(Y, Z).$$

*Definitions / symbols used*
- **Expectation** $E[X]$: the mean of $X$. Write $\mu_X = E[X]$.
- **Linearity of expectation**: $E[aX + bY] = aE[X] + bE[Y]$ for numbers $a,b$. (You may use this; Problem 2 is where you prove it.)
- **Variance**: $\operatorname{Var}(X) = E\!\left[(X - \mu_X)^2\right]$.
- **Covariance**: $\operatorname{Cov}(X, Y) = E\!\left[(X - \mu_X)(Y - \mu_Y)\right]$.
- **$c$**: a constant, not random. $E[c] = c$.

---

**Your turn — one line only, not the whole proof.**

All three identities turn on the same small fact: what happens to the *deviation from the mean* when you scale $X$ by $c$.

Let $W = cX$. Write down $\mu_W = E[W]$ in terms of $\mu_X$, and then write the deviation
$$W - \mu_W$$
in terms of $c$ and $X - \mu_X$.

That is the whole answer I want. Two short expressions.
