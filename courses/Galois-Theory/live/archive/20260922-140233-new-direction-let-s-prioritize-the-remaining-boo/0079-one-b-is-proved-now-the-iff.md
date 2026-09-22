---
kind: lesson
title: one-b-is-proved-now-the-iff
---
**That is 1(b), proved.** Fix $\overline{h} \neq \overline{0}$, multiply by it,
show injective, get surjective free, feed $\overline{1}$: the inverse drops out.
The line that carries the whole thing is $\overline{h}(\overline{g_1} -
\overline{g_2}) = \overline{0}$ forcing $\overline{g_1} = \overline{g_2}$ --- that
is the only place "integral domain" is used, and it is the right place.

One clause does nothing: "if $\overline{g_1}, \overline{g_2} \neq 0$, both sides
are not $0$." You do not need either side non-zero, and the case $\overline{g_1} =
\overline{0}$ is not excluded --- the subtraction handles every case at once. Three
lines at the top are also dead: $h = gf + r$, $r \neq 0$, $r = \sum c_i x^i$. They
are the leftover attempt to build the inverse by hand.

The write-up says $\dim_F A = n$ by 1(a) where you wrote "finite dimensional", and
calls $T$ $F$-linear, since rank--nullity needs both.

Problem 1(c), whole. $F$ a field, $f \in F[x]$ non-constant of degree $n$, $A =
F[x]/(f)$. Conclude that $A$ is a field if and only if $f$ is irreducible.

What this uses:

- irreducible --- $f$ is non-constant and cannot be written $f = gh$ with $g, h \in F[x]$ both of degree $\geq 1$.
- $A = F[x]/(f)$ --- classes $\overline{g} = g + (f)$; $\overline{g} = \overline{0}$ exactly when $f \mid g$.
- field --- commutative ring, $\overline{1} \neq \overline{0}$, every non-zero element has an inverse.
- integral domain --- commutative ring, $\overline{1} \neq \overline{0}$, and $\overline{u}\,\overline{v} = \overline{0}$ forces $\overline{u} = \overline{0}$ or $\overline{v} = \overline{0}$.
- 1(a), yours --- $\dim_F A = n$, so $\overline{1} \neq \overline{0}$ since $n \geq 1$.
- 1(b), yours --- if $A$ is an integral domain then $A$ is a field.
- degrees add --- $\deg(gh) = \deg g + \deg h$ for non-zero $g, h$ over a field.
- every field is an integral domain.

Two directions, and neither is long. Both start by picking a product that is
$\overline{0}$ in $A$ and reading it back in $F[x]$ as $f \mid gh$.

**Show that $A$ is a field if and only if $f$ is irreducible. Take the two
directions separately and say which of the facts above each one spends.**
