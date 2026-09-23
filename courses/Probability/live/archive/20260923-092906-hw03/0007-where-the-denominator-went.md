---
kind: question
title: where-the-denominator-went
---
You divided by nothing. $E[X \mid Y = y]$ integrates $x$ against the **conditional** density, and you integrated it against the **joint** density:
$$
E[X \mid Y = y] = \int_0^{\infty} x\,f_{X \mid Y}(x \mid y)\,dx = \int_0^{\infty} x\,\frac{f(x,y)}{f_Y(y)}\,dx .
$$
Your second line has $f(x,y)$ where $f(x,y)/f_Y(y)$ belongs. Everything after that line is correct, so you computed the numerator exactly and then stopped.

The missing factor is $f_Y(y)$, which is the integral from the last card. It is $e^{-y}$. Divide: $y e^{-y} / e^{-y} = y$. That is the answer.

Your $\int_0^{\infty} x e^{-x/y}\,dx = y^2$ is right, integration by parts and vanishing boundary term and all. The $-xye^{-x/y}$ term does go to $0$ as $x \to \infty$. One division is absent; no algebra is wrong.

---

**Exercise (Homework 3, Problem 12).**
The joint density of $X$ and $Y$ is
$$
f(x,y) = \frac{e^{-x/y}\,e^{-y}}{y}, \qquad 0 < x < \infty,\ \ 0 < y < \infty .
$$
Show that $E[X \mid Y = y] = y$.

*Definitions / symbols used*
- **Marginal density** $f_Y(y) = \int_{-\infty}^{\infty} f(x,y)\,dx$, the integral of the joint over all $x$.
- **Conditional density** $f_{X \mid Y}(x \mid y) = f(x,y)/f_Y(y)$, defined where $f_Y(y) > 0$.
- **Conditional expectation** $E[X \mid Y = y] = \int_{-\infty}^{\infty} x\,f_{X \mid Y}(x \mid y)\,dx$.
- $y$ is fixed throughout; every integral runs over $x$ alone, from $0$ to $\infty$.
- You already have $\int_0^{\infty} x e^{-x/y}\,dx = y^2$ and $f_Y(y) = e^{-y}$.

---

**Your turn.** Write the whole argument again, in order: $f_Y(y)$ first, then $f_{X \mid Y}(x \mid y)$, then the expectation integral. For the density $f(x,y) = e^{-x/y}e^{-y}/y$ on $0 < x < \infty$, $0 < y < \infty$, show that $E[X \mid Y = y] = y$.
