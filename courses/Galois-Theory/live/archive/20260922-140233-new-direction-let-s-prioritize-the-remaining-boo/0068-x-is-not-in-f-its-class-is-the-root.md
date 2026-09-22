---
kind: lesson
title: x-is-not-in-f-its-class-is-the-root
---
**No: $x \notin F$, so undo that circled note.** $F$ sits inside $F[x]$ as the
constants, and $x$ is not a constant. The element you want lives one floor up, in
$A$, and it is $\overline{x}$. And $\overline{x}$ *is* a root of $f$ there --- that
is the fact you were reaching for, and it is worth writing down: $f(\overline{x}) =
\overline{f} = \overline{0}$.

The rest of the line is the right idea. Every power $\overline{x}^k$ with $k \geq n$
does collapse into $\overline{1}, \dots, \overline{x^{n-1}}$, and that collapse is
why they span. But "can be rewritten" is the claim, not the proof. One tool does it
in a line, and it is the last definition below.

**One step.** Let $\overline{g}$ be any element of $A$, with $g \in F[x]$. Divide $g$
by $f$: there are $q, r \in F[x]$ with $g = qf + r$ and $r = 0$ or $\deg r < n$. Now
push that equation down into $A$, using $\overline{f} = \overline{0}$, and simplify.
What is $\overline{g}$ equal to?

Problem 1(a), for context: $F$ a field, $f \in F[x]$ nonconstant of degree $n$, $A =
F[x]/(f)$; show $\overline{1}, \overline{x}, \dots, \overline{x^{n-1}}$ is a basis of
$A$ over $F$, so $\dim_F A = n$.

What this uses:

- $F[x]$ --- polynomials in $x$ with coefficients in $F$; $x$ is an indeterminate, not an element of $F$.
- $(f)$ --- all multiples $qf$ with $q \in F[x]$.
- $A = F[x]/(f)$ --- classes $\overline{g} = g + (f)$, with $\overline{g} = \overline{h}$ exactly when $g - h$ is a multiple of $f$.
- $\overline{f} = \overline{0}$ --- the one relation in $A$.
- Arithmetic on representatives: $\overline{g} + \overline{h} = \overline{g+h}$ and $\overline{g}\,\overline{h} = \overline{gh}$.
- Scalars: $c \cdot \overline{g} = \overline{cg}$ for $c \in F$.
- Spanning --- every element of $A$ is an $F$-combination of the listed classes.
- Division with remainder in $F[x]$ --- for any $g$ and nonconstant $f$ there are $q, r$ with $g = qf + r$ and $r = 0$ or $\deg r < \deg f$.

**So: take $\overline{g} \in A$, write $g = qf + r$ by division with remainder, and
tell me what $\overline{g}$ equals in $A$.**
