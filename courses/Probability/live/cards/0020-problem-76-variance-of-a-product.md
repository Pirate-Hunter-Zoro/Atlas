---
kind: question
title: problem-76-variance-of-a-product
---
**Correct. Problem 61 is done.**

You rebuilt (c) and (d) with the $\lambda$ carried through the limit — $x=0 \Rightarrow u=-\lambda w$, $x\to\infty \Rightarrow u\to-\infty$, limits flipped — and landed on $f_W(w)=\lambda e^{-\lambda w}$, $w>0$. Then the factorization:

$$f_X(x)f_W(w) = \lambda e^{-\lambda x}\cdot\lambda e^{-\lambda w} = \lambda^2 e^{-\lambda(x+w)} = f_{X,W}(x,w) \quad\Longrightarrow\quad X \perp W.$$

Verdict right. Two notes, both small. You wrote $f_X(x)f_W(x)$ on the last line — the second argument is $w$. And you skipped the region half: the factorization alone is not the whole test. Here $\{x>0,\ w>0\}$ *is* a rectangle, so nothing breaks, and that is exactly the contrast with $X$ and $Y=X+W$, whose region $0<x<y$ is not one. Say the region out loud next time you claim independence.

---

**Exercise (Ross, Ch. 2, Problem 76).**
Let $X$ and $Y$ be independent random variables with means $\mu_x$, $\mu_y$ and variances $\sigma_x^2$, $\sigma_y^2$. Show that

$$\mathrm{Var}(XY) \;=\; \sigma_x^2\sigma_y^2 \;+\; \mu_y^2\sigma_x^2 \;+\; \mu_x^2\sigma_y^2.$$

*Definitions / symbols used*
- $\mathrm{Var}(Z) = E[(Z-\mu_Z)^2]$, and equivalently $\mathrm{Var}(Z) = E[Z^2] - (E[Z])^2$.
- $E[X]=\mu_x$, $E[Y]=\mu_y$, $\mathrm{Var}(X)=\sigma_x^2$, $\mathrm{Var}(Y)=\sigma_y^2$.
- **Independence, the tool you just proved.** $X$ and $Y$ independent means $f_{X,Y}(x,y)=f_X(x)f_Y(y)$ on a rectangular region — and the consequence you get to use is that expectation splits across a product: $E[XY]=E[X]E[Y]$.
- $XY$ is itself a random variable; $\mathrm{Var}(XY)$ means the variance of that one variable, **not** anything about $\mathrm{Var}(X)$ times $\mathrm{Var}(Y)$.

---

**Your turn. One line, and a name.**

The proof runs through $E[(XY)^2] = E[X^2Y^2]$. Write down what $E[X^2Y^2]$ equals in terms of $E[X^2]$ and $E[Y^2]$ — and name the property of $X$ and $Y$ that entitles you to it.
