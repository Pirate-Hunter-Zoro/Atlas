---
kind: lesson
title: surjectivity-is-free-you-already-proved-it
---
**You are not stuck --- you are trying to prove something you already own.**
Surjectivity of $T$ needs no argument of its own here. It falls out of the
injectivity you just proved, by rank--nullity: an $F$-linear map from a
finite-dimensional $F$-vector space to *itself* is injective exactly when it is
surjective. $T$ goes from $A$ to $A$, and $\dim_F A = n$ by 1(a). So the line
"Let $\overline{g_2} \in A$, show $\exists\, \overline{g_1}$" has nothing to go
under it. Injective, same space, finite dimension, done.

And your bubble already holds the finish: feed $\overline{1}$, get a
$\overline{g}$ with $\overline{h}\,\overline{g} = \overline{1}$. That is the
right element to feed and the right conclusion.

Three lines on the page do no work for 1(b) --- $h = gf + r$, $r \neq 0$, and
$r = \sum_{i=0}^{n-1} c_i x^i$. That was the attempt to build the inverse by
hand, and you are not building it.

Problem 1(b), whole. $F$ a field, $f \in F[x]$ non-constant of degree $n$,
$A = F[x]/(f)$. Show that if $A$ is an integral domain, then $A$ is a field.

What this uses:

- field --- commutative ring, $\overline{1} \neq \overline{0}$, and every non-zero element has a multiplicative inverse.
- inverse of $\overline{h}$ --- an element $\overline{u} \in A$ with $\overline{h}\,\overline{u} = \overline{1}$.
- integral domain --- commutative ring, $\overline{1} \neq \overline{0}$, and $\overline{u}\,\overline{v} = \overline{0}$ forces $\overline{u} = \overline{0}$ or $\overline{v} = \overline{0}$.
- $A = F[x]/(f)$ --- classes $\overline{g} = g + (f)$, with $\overline{g_1} = \overline{g_2}$ exactly when $g_1 - g_2 \in (f)$.
- $\dim_F A = n$ --- 1(a), which you closed: the classes of $1, x, \dots, x^{n-1}$ are an $F$-basis of $A$.
- $T$ --- multiplication by $\overline{h}$, sending $\overline{u} \mapsto \overline{h}\,\overline{u}$; $F$-linear.
- rank--nullity --- an $F$-linear map from a finite-dimensional space to itself is injective exactly when it is surjective.

**Write out 1(b) whole now, start to finish: fix a non-zero $\overline{h}$ in
$A$, define $T$, show it injective, get surjective, feed it $\overline{1}$,
conclude that $A$ is a field. Five or six lines.**
