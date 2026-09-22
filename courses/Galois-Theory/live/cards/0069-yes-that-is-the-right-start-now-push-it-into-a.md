---
kind: lesson
title: yes-that-is-the-right-start-now-push-it-into-a
---
**Yes, that is right so far** --- with one word to add. Division with remainder
allows $r = 0$, and $\deg r < \deg f$ says nothing in that case, because the zero
polynomial has no degree. So the statement you want is: there are $q, r \in F[x]$
with $g = qf + r$ and either $r = 0$ or $\deg r < n$. Everything else on the page
is exactly the setup, and you stopped in the right place to ask.

Now spend it. You have an equation in $F[x]$, and the thing you care about lives
in $A$. Apply the bar to both sides of $g = qf + r$, use that bars respect sums and
products, and use the one relation $\overline{f} = \overline{0}$. One term dies.
What is $\overline{g}$ equal to?

Problem 1(a): $F$ a field, $f \in F[x]$ non-constant of degree $n$, $A = F[x]/(f)$;
show $\overline{1}, \overline{x}, \dots, \overline{x^{n-1}}$ is a basis of $A$ over
$F$, so $\dim_F A = n$.

What this uses:

- $F[x]$ --- polynomials in $x$ with coefficients in $F$; $x$ is an indeterminate, never an element of $F$.
- $(f)$ --- all multiples $qf$ with $q \in F[x]$.
- $A = F[x]/(f)$ --- classes $\overline{g} = g + (f)$, equal exactly when the difference is a multiple of $f$.
- $\overline{f} = \overline{0}$ --- the one relation in $A$.
- Arithmetic on representatives: $\overline{g} + \overline{h} = \overline{g+h}$, $\overline{g}\,\overline{h} = \overline{gh}$, and $c \cdot \overline{g} = \overline{cg}$ for $c \in F$.
- Division with remainder --- for $g \in F[x]$ and non-constant $f$ there are $q, r$ with $g = qf + r$ and $r = 0$ or $\deg r < \deg f$.
- Spanning --- every element of $A$ is an $F$-combination of the listed classes.

**So: bar both sides of $g = qf + r$ and tell me what $\overline{g}$ equals in $A$.**
