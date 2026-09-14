---
kind: question
title: problem-61-exponent-is-a-product
---
**You asked for help, so here it is, at the one line where it went wrong.**

$$\int_0^\infty \lambda^2 e^{-(x+w)\lambda}\,dx \;=\; \int_0^\infty \lambda^2 e^{-x\lambda}\,dx \;+\; \int_0^\infty \lambda^2 e^{-w\lambda}\,dx \qquad \textbf{— no.}$$

A sum **in the exponent** is a **product** of exponentials, never a sum of them:
$$e^{a+b} = e^a \cdot e^b .$$
Check it with numbers: $e^{1+1} = e^2 \approx 7.39$, while $e^1 + e^1 \approx 5.44$. Different. Everything after that line on your page is chasing a wrong object, which is why it turned into an improper integral with a $-\infty$ limit and a boundary term that wouldn't die. Nothing wrong with your substitution work; it was aimed at the wrong integrand.

---

**(c) is correct.** $f_{X,W}(x,w) = \lambda^2 e^{-\lambda(x+w)}$, and your region reasoning — $x < y$ becomes $w > 0$ — is right. Two things you did silently and should say out loud once: the other inequality $0 < x$ is untouched by the substitution, so the region is $x > 0$ **and** $w > 0$, with no link between them; and the Jacobian of $(x,y) \mapsto (x, y-x)$ is $1$, which is why the formula carried over with no extra factor. A change of variables without a stated Jacobian is an incomplete answer even when the Jacobian is $1$.

---

**Exercise (Ross, Ch. 2, Problem 61), restated in full.**
Let $X$ and $W$ be the working and subsequent repair times of a certain machine. Let $Y = X + W$ and suppose the joint probability density of $X$ and $Y$ is
$$f_{X,Y}(x,y) = \lambda^2 e^{-\lambda y}, \qquad 0 < x < y < \infty.$$

**(a)** Density of $X$ — done: $f_X(x) = \lambda e^{-\lambda x}$, $x > 0$.
**(b)** Density of $Y$ — done: $f_Y(y) = \lambda^2 y e^{-\lambda y}$, $y > 0$.
**(c)** Joint density of $X$ and $W$ — done: $f_{X,W}(x,w) = \lambda^2 e^{-\lambda(x+w)}$ on $x > 0$, $w > 0$.
**(d)** Find the density of $W$.

*Definitions / symbols used*
- **Marginal density.** $f_W(w) = \int_{-\infty}^{\infty} f_{X,W}(x,w)\,dx$ — integrate the joint density over every value of the *other* variable. Here the joint density is $0$ unless $x > 0$, so the live limits are $0$ to $\infty$.
- **Law of exponents.** $e^{a+b} = e^a e^b$. A constant factor — constant *with respect to the variable being integrated* — comes out in front of the integral.
- $\lambda$: a fixed positive constant.
- The answer should be a function of $w$ alone. If an $x$ survives, something is wrong.

---

**Your turn. One line, no integration yet.**

Write $\lambda^2 e^{-\lambda(x+w)}$ as a **product of two factors**: one that involves only $x$, one that involves only $w$. Put the $\lambda^2$ wherever you like.

**Which factor is the constant when you integrate $dx$?**
