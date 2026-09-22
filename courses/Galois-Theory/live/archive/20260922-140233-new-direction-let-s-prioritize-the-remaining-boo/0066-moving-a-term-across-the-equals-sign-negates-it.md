---
kind: lesson
title: moving-a-term-across-the-equals-sign-negates-it
---
**The sign is wrong: $\overline{x^3} = \overline{x} - \overline{1}$, not $\overline{1} - \overline{x}$.**
You read the tail of $f$ off the page as $-x+1$ and copied it across unchanged.
A term moved across the equals sign changes sign. From
$\overline{x^3} - \overline{x} + \overline{1} = \overline{0}$, add $\overline{x}$
to both sides and subtract $\overline{1}$ from both sides: the right side is
$\overline{x} - \overline{1}$. Your version would say $x^3 + x - 1$ is a multiple
of $f$, and it is not.

The rest of the page is right. $F = \mathbb{Q}$, $f = x^3-x+1$, $n = 3$. And your
$\alpha$ is not a new object here: in $A$ the class $\overline{x}$ is itself a
root of $f$, because $f(\overline{x}) = \overline{f(x)} = \overline{0}$.

**Where this is going --- Problem 1(a).** $F$ a field, $f \in F[x]$ nonconstant of
degree $n$, $A = F[x]/(f)$; show $\dim_F A = n$. The basis is
$\overline{1}, \overline{x}, \dots, \overline{x^{n-1}}$, and the spanning half is
the half that needs $f$. Your corrected identity is the engine of it: it turns
$\overline{x^3}$ into something of degree below $3$, and one more turn of the same
crank handles $\overline{x^4}$.

What this uses:

- $F[x]$ --- polynomials in $x$ with coefficients in $F$.
- $(f)$ --- all multiples $qf$, $q \in F[x]$.
- $A = F[x]/(f)$ --- classes $\overline{g} = g + (f)$; $\overline{g} = \overline{h}$ iff $g-h$ is a multiple of $f$.
- $\overline{f} = \overline{0}$ --- the one relation, since $f - 0 = 1 \cdot f$.
- Classes multiply: $\overline{g}\,\overline{h} = \overline{gh}$, and add the same way.
- $\dim_F A$ --- the dimension of $A$ as a vector space over $F$.
- Spanning --- every element of $A$ is an $F$-combination of the listed classes.

**Your move, one thing only.** With $F = \mathbb{Q}$ and $f = x^3-x+1$, write
$\overline{x^4}$ as a rational combination of $\overline{1}$, $\overline{x}$ and
$\overline{x^2}$. Start from $\overline{x^4} = \overline{x} \cdot \overline{x^3}$
and use $\overline{x^3} = \overline{x} - \overline{1}$.
