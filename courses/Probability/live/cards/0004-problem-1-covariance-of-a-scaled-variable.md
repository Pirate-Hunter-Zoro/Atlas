---
kind: question
title: Problem 1 – Covariance of a scaled variable
---

Correct, and more than I asked for. You proved the whole first identity by expanding the square, and every line of it holds: $-2cX\,E(cX)$ really does become $-2c^2X\,E(X)$, $(cE(X))^2$ really is $c^2(E(X))^2$, and pulling $c^2$ out of all three terms leaves $E\!\left[(X-E(X))^2\right]$ exactly. $\operatorname{Var}(cX)=c^2\operatorname{Var}(X)$ is yours.

One bookkeeping note, not a maths error. Your first line reads
$$\operatorname{Var}(cX) = c^2\operatorname{Var}(X) = c^2\left(E\!\left[(X-\mu_X)^2\right]\right),$$
which asserts the thing you are about to prove. Your actual proof starts on the second line and never uses it. Write that first line as a heading — "to show:" — or drop it, so the chain below stands alone.

You skipped the deviation step I asked for, so here it is, because the other two identities are one line each with it and painful without it:
$$\mu_{cX} = E[cX] = cE[X] = c\mu_X \qquad\Longrightarrow\qquad cX - \mu_{cX} = c(X - \mu_X).$$
Scaling $X$ by $c$ scales its deviation from the mean by $c$. That is the whole content of part one, and it is what your $c^2$ was.

---

**Exercise (Homework 2, Problem 1, continued).**
Let $X$, $Y$ and $Z$ be random variables and let $c$ be a number. Prove that
$$\operatorname{Cov}(cX, Y) = c\operatorname{Cov}(X, Y),$$
$$\operatorname{Cov}(X+Y, Z) = \operatorname{Cov}(X, Z) + \operatorname{Cov}(Y, Z).$$

*Definitions / symbols used*
- **Expectation** $E[X]$: the mean of $X$. Write $\mu_X = E[X]$.
- **Linearity of expectation**: $E[aX + bY] = aE[X] + bE[Y]$ for numbers $a,b$. (You may use it; Problem 2 is where you prove it.)
- **Covariance**: $\operatorname{Cov}(X, Y) = E\!\left[(X - \mu_X)(Y - \mu_Y)\right]$.
- **Deviation under scaling** (just established): $cX - \mu_{cX} = c(X - \mu_X)$.
- **$c$**: a constant, not random. $E[c] = c$.

---

**Your turn — the first identity only.**

Prove $\operatorname{Cov}(cX, Y) = c\operatorname{Cov}(X, Y)$.

Start from the definition of $\operatorname{Cov}(cX,Y)$, substitute the deviation fact for the first factor, and pull the constant out through $E$. Three lines at most. Leave $\operatorname{Cov}(X+Y,Z)$ alone for now.
