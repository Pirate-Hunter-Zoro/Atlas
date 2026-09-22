---
kind: lesson
title: x-fourth-lands-now-1a-whole
---
**$\overline{x^4} = \overline{x^2} - \overline{x}$ is right, and the route is right:
$\overline{x}\cdot\overline{x^3}$, then substitute.** The crank turned. Drop the last
link of your chain, though --- you closed it with $= x^4$, which sends you back to
where you started. The chain ended at $\overline{x^2} - \overline{x}$.

One thing to tighten, and it is the whole point of 1(a). Keep the bars on. Written
bare, $x^3 = x - 1$ is an equation in $\mathbb{Q}[x]$, and there it is false: $x^3 - x + 1$
is not the zero polynomial. It is true in $A$, as $\overline{x^3} = \overline{x} - \overline{1}$.
Which ring the equality lives in is the thing 1(a) is asking you to keep track of.

**Problem 1(a), whole.** Let $F$ be a field and $f \in F[x]$ nonconstant of degree $n$,
and let $A = F[x]/(f)$. Show that $\dim_F A = n$ --- that is, show that
$\overline{1}, \overline{x}, \dots, \overline{x^{n-1}}$ is a basis of $A$ as a vector
space over $F$. There are two halves: those $n$ classes span $A$, and they are linearly
independent over $F$.

What this uses:

- $F[x]$ --- polynomials in $x$ with coefficients in $F$.
- $\deg$ --- the degree of a nonzero polynomial; nonconstant means $n \geq 1$.
- $(f)$ --- all multiples $qf$, $q \in F[x]$.
- $A = F[x]/(f)$ --- classes $\overline{g} = g + (f)$; $\overline{g} = \overline{h}$ iff $g - h$ is a multiple of $f$.
- $\overline{f} = \overline{0}$ --- the one relation, since $f - 0 = 1 \cdot f$.
- Classes add and multiply on representatives: $\overline{g} + \overline{h} = \overline{g+h}$, $\overline{g}\,\overline{h} = \overline{gh}$.
- $A$ is a vector space over $F$: $c \cdot \overline{g} = \overline{cg}$ for $c \in F$.
- Spanning --- every element of $A$ is an $F$-combination of the listed classes.
- Linearly independent --- the only $F$-combination of them equal to $\overline{0}$ is the one with every coefficient $0$.
- Division with remainder in $F[x]$ --- for any $g$ and nonconstant $f$ there are $q, r \in F[x]$ with $g = qf + r$ and either $r = 0$ or $\deg r < \deg f$.

**So: prove that $\overline{1}, \overline{x}, \dots, \overline{x^{n-1}}$ span $A$ over $F$
and are linearly independent over $F$, hence $\dim_F A = n$.** Take the spanning half
first if you want a foothold; it is your $x^4$ computation with $n$ in place of $3$.
