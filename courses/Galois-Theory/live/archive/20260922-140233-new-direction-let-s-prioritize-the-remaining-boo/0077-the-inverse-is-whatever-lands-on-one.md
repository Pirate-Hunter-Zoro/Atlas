---
kind: lesson
title: the-inverse-is-whatever-lands-on-one
---
**Because "inverse" is not an object you have to see --- it is a name for
anything satisfying one equation.** $\overline{u}$ is called $\overline{h}^{-1}$
exactly when $\overline{h}\,\overline{u} = \overline{1}$. Nothing else. So to
prove $\overline{h}^{-1}$ exists you do not have to produce coefficients; you
have to produce *some* element whose product with $\overline{h}$ is
$\overline{1}$. Surjectivity produces elements. That is the whole connection.

Delete the right half of your bubble. You wrote $\overline{h}\,\overline{\ell} =
\overline{g} \iff \overline{\ell} = \overline{h}^{-1}\overline{g}$, and that
arrow divides by $\overline{h}$ --- it uses the inverse you are trying to build.
The left half, $\forall \overline{g}\ \exists \overline{\ell}$, is the real
statement, and it is enough on its own.

Injectivity is done and correct. Two housekeeping marks on it: your last two
clauses are in the wrong order --- the domain hypothesis gives you
$\overline{g_1} - \overline{g_2} = \overline{0}$ first, and $\overline{g_1} =
\overline{g_2}$ follows --- and the "both sides are not $\overline{0}$" line is
still on the page and still unused.

Problem 1(b): $F$ a field, $f \in F[x]$ non-constant of degree $n$,
$A = F[x]/(f)$. Show that if $A$ is an integral domain, then $A$ is a field.

What this uses:

- field --- every non-zero element has a multiplicative inverse.
- inverse of $\overline{h}$ --- an element $\overline{u} \in A$ with $\overline{h}\,\overline{u} = \overline{1}$.
- integral domain --- commutative ring, $\overline{1} \neq \overline{0}$, and $\overline{u}\,\overline{v} = \overline{0}$ forces $\overline{u} = \overline{0}$ or $\overline{v} = \overline{0}$.
- $A = F[x]/(f)$ --- classes $\overline{g} = g + (f)$, equal exactly when the difference lies in $(f)$.
- $\dim_F A = n$ --- 1(a), which you closed; $A$ is a finite-dimensional $F$-vector space.
- $T$ --- multiplication by $\overline{h}$, sending $\overline{u} \mapsto \overline{h}\,\overline{u}$; $F$-linear, and you have just shown it injective.
- rank--nullity --- an $F$-linear map from a finite-dimensional space to itself is injective exactly when it is surjective.
- surjective --- every element of $A$ is $T(\overline{\ell})$ for some $\overline{\ell} \in A$.

So $T$ is surjective. Its statement is: for every $\overline{g} \in A$ there is
an $\overline{\ell}$ with $\overline{h}\,\overline{\ell} = \overline{g}$. You
only need it for one $\overline{g}$.

**One line. Which single $\overline{g}$ do you feed it, and what equation does
the $\overline{\ell}$ that comes back satisfy? Stop there.**
