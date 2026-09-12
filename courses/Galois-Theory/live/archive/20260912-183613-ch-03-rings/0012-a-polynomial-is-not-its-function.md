---
kind: note
title: No. A polynomial is not the function it gives you.
---

Direct answer to the bubble: **no.**

A polynomial in $R[x_1,\ldots,x_n]$ is a *formal* object — a finite list of coefficients from $R$, one per monomial. Two polynomials are equal exactly when their coefficients agree term by term. Nothing about values enters into it.

Every polynomial does *hand you* a function $R^n \to R$, by substituting elements of $R$ for the variables. But that is something a polynomial produces, not what it is, and the difference is not pedantry: the passage from polynomial to function loses information.

Here is the loss, concretely. Take $R = \mathbb{F}_2 = \{0,1\}$ and $n = 1$, and consider

$$p = x^2, \qquad q = x.$$

As functions on $\mathbb{F}_2$: $p(0) = 0 = q(0)$ and $p(1) = 1 = q(1)$ — **the same function**. As polynomials they are plainly different: different coefficients, different degrees. So the functions $R^n \to R$ form a coarser collection than $R[x_1,\ldots,x_n]$, and swapping one for the other changes the object.

It matters for the thing you got right below, too. $x_1$ has no inverse in $\mathbb{Z}[x_1,x_2]$ because **degrees add** — the degree of a product is the sum of the degrees, so nothing of degree $1$ can multiply up to the constant $1$. That is a fact about coefficients. It is invisible in the values.

**Both inverse answers are correct**, and $1/x_1$ is the right witness. You do not need the caveat: $x_1$ is an indeterminate, so it is never $0_R$. Still not written down: **what the domain of $\phi$ has to be.** That one is owed.

One flat correction. Your right-hand line now reads $a, b \in R[x_1,\ldots,x_n]$; last revision it read $F[x_1,\ldots,x_n]$, which was right. $F(x_1,\ldots,x_n)$ is *by definition* the field of fractions of $F[x_1,\ldots,x_n]$. Put the $F$ back.

**Your move.** Stay in $\mathbb{F}_2[x]$, one variable. Write down a polynomial that is **not** the zero polynomial but whose function sends every element of $\mathbb{F}_2$ to $0$.
