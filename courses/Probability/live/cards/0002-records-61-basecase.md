---
kind: question
title: records-61-basecase
---
Yes on the base case --- it finishes, and you are one substitution from it. The induction is a legal road but an expensive one, and there is a route to all of (a) with no integral at all; that is where we go after this.

Your base case, unstuck. In $\int_{-\infty}^{\infty}\!\int_{-\infty}^{x_2} f(x_1)f(x_2)\,dx_1\,dx_2$ the inner integral does not need $f$ to be known. It is
$$\int_{-\infty}^{x_2} f(x_1)\,dx_1 = F(x_2),$$
the cumulative distribution function of $X_1$. So the whole thing is $\int_{-\infty}^{\infty} F(x)f(x)\,dx$, and $F$ is still unknown --- but $F$ is its own substitution.

One flag on the inductive step so you do not build on it: the first term multiplies $\frac1n \cdot \frac{n-1}{n}$, which treats $\{X_{n+1} > \max(X_1,\ldots,X_{n-1})\}$ and $\{X_n \le \max(X_1,\ldots,X_{n-1})\}$ as independent. They are not --- both look at the same $\max$. Leave it; we will not need it.

Everything this step uses:

- $f$: the common density of the $X_i$, whatever it is.
- $F$: the cumulative distribution function, $F(x) = P\{X_1 \le x\}$.
- $F'(x) = f(x)$, so $du = f(x)\,dx$ under the substitution $u = F(x)$.
- $F$ runs from $0$ to $1$: $F(-\infty) = 0$ and $F(\infty) = 1$. Those are the new limits.
- $\int_0^1 u\,du$ is an ordinary power-rule integral.

Substitute $u = F(x)$ in $\int_{-\infty}^{\infty} F(x)f(x)\,dx$ and evaluate it. What number do you get?
