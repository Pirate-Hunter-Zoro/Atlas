---
kind: question
title: problem-1-covariance-splits-over-a-sum
---
Correct, all five lines, and nothing wasted. $\mu_{cX}=c\mu_X$ went in, $c$ came out through $E$, done. You also took the bookkeeping note: the identity now sits at the top labelled **Prove:**, and the chain below stands on its own. That is exactly the shape a proof should have.

One naming point, free of charge. Your third line, $E[c(X-\mu_X)(Y-\mu_Y)]\to cE[(X-\mu_X)(Y-\mu_Y)]$, is *linearity of expectation* in its one-variable form: a constant multiple comes out of $E$. It is the same tool you will use on the next identity, only with a sum instead of a product.

---

**Exercise (Homework 2, Problem 1, continued).**
Let $X$, $Y$ and $Z$ be random variables. Prove that
$$\operatorname{Cov}(X+Y,\;Z) \;=\; \operatorname{Cov}(X,Z) + \operatorname{Cov}(Y,Z).$$

*Definitions / symbols used*
- **Expectation** $E[X]$: the mean of $X$. Write $\mu_X = E[X]$.
- **Covariance**: $\operatorname{Cov}(X,Y) = E\!\left[(X-\mu_X)(Y-\mu_Y)\right]$.
- **Linearity of expectation**: $E[aX+bY] = aE[X]+bE[Y]$ for numbers $a,b$. You may use it here; Problem 2 is where you prove it.
- **$\mu_{X+Y}$**: the mean of the single random variable $X+Y$. By linearity, $\mu_{X+Y}=\mu_X+\mu_Y$.

---

**Your turn.**

Prove it. Start from $\operatorname{Cov}(X+Y,Z)=E\!\left[\big((X+Y)-\mu_{X+Y}\big)(Z-\mu_Z)\right]$.

Your first job is the same one $\mu_{cX}=c\mu_X$ did last time: rewrite $(X+Y)-\mu_{X+Y}$ so that $X$'s deviation and $Y$'s deviation appear separately. Then multiply out against $(Z-\mu_Z)$ and split the expectation.
