---
kind: lesson
title: x-times-x-squared-is-still-x-cubed
---
**That equation is true in $\mathbb{Q}[x]$ and does no work in $A$.**
$x^3 = x \cdot x^2$ holds before you quotient by anything; it says nothing about
$A = \mathbb{Q}[x]/(x^3-x+1)$. And "using only the classes of $1$, $x$, $x^2$"
asks for a *linear combination* --- rational numbers times those three classes,
added --- not a product of them. A product of basis vectors is not a vector-space
expression.

**The one fact that makes $A$ smaller than $\mathbb{Q}[x]$.** Two polynomials
name the same class in $A$ exactly when their difference is a multiple of
$f = x^3 - x + 1$. Take $g = f$ and compare it with $0$: their difference is
$f = 1 \cdot f$, a multiple of $f$. So the class of $f$ in $A$ is the class of
$0$. That single equation is the whole content of the quotient, and every
computation in $A$ comes out of it.

What this uses:

- $\mathbb{Q}[x]$ --- polynomials in $x$ with rational coefficients.
- $(f)$ --- all multiples $qf$ with $q \in \mathbb{Q}[x]$.
- $A = \mathbb{Q}[x]/(f)$ --- classes $g + (f)$; two polynomials give the same class iff their difference is a multiple of $f$.
- The class map is a ring homomorphism: the class of $g+h$ is the sum of the classes, and the class of $gh$ is the product of the classes.

**Your move, one thing only.** In $A$ you have
$$\overline{x^3 - x + 1} = \overline{0}.$$
Split the left side across the $+$ and $-$ signs and rearrange it to read
$\overline{x^3} = \ \cdots$, with the right side a rational combination of
$\overline{1}$, $\overline{x}$ and $\overline{x^2}$. Write that right side.
