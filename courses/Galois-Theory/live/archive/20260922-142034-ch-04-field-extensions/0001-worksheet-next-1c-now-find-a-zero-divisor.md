---
kind: lesson
title: worksheet-next-1c-now-find-a-zero-divisor
---
The book is clear and the worksheet is all that is left. Chapter 4 is written
up ten of eleven, and 4.2 stays skipped as you asked. On the sheet "Field
Extensions and the Ring $F[x]$", Problems 3 and 6 are done and Problem 1 is
done but for part (c).

This sitting takes four, in this order: **1(c), 2(a), 2(c), 5**. 1(c) closes
Problem 1 out of the two parts you already proved. 2(a) is the one real idea on
the sheet --- a gcd does not change when you enlarge the field --- and 2(b)
falls out of it in a line. 2(c) is the tool Problems 4 and 5 both spend. 5 is
short once 1(c) is in hand. Problem 4 needs the formal derivative and goes next
sitting.

**Problem 1(c).** Let $F$ be a field and let $f \in F[x]$ be non-constant of
degree $n$. Set $A = F[x]/(f)$. Conclude that $A$ is a field if and only if $f$
is irreducible.

What this uses:

- irreducible --- $f$ is non-constant and cannot be written $f = gh$ with $g, h \in F[x]$ both of degree $\geq 1$.
- $A = F[x]/(f)$ --- the classes $\overline{g} = g + (f)$; $\overline{g} = \overline{0}$ exactly when $f \mid g$.
- field --- commutative ring, $\overline{1} \neq \overline{0}$, every non-zero element has an inverse.
- integral domain --- commutative ring, $\overline{1} \neq \overline{0}$, and $\overline{u}\,\overline{v} = \overline{0}$ forces $\overline{u} = \overline{0}$ or $\overline{v} = \overline{0}$.
- zero divisor --- a non-zero element whose product with some other non-zero element is $\overline{0}$.
- 1(a), yours --- $\dim_F A = n$, so $\overline{1} \neq \overline{0}$ since $n \geq 1$.
- 1(b), yours --- if $A$ is an integral domain then $A$ is a field.
- degrees add --- $\deg(gh) = \deg g + \deg h$ for non-zero $g, h$ over a field.
- every field is an integral domain.

**Your move.** Not 1(c) itself --- one concrete case of the direction that goes
wrong. Take $F = \mathbb{Q}$ and $f = x^{2} - 1$, which is $(x-1)(x+1)$ and so
is not irreducible, and let $A = \mathbb{Q}[x]/(x^{2}-1)$. Name two classes in
$A$, neither of them $\overline{0}$, whose product is $\overline{0}$, and say in
one line why their existence stops $A$ being a field.
