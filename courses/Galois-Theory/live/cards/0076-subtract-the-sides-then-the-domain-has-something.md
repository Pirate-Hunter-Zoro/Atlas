---
kind: lesson
title: subtract-the-sides-then-the-domain-has-something-to-bite
---
**Subtract.** The integral domain hypothesis only ever speaks about a product
that *equals zero*, and your equation $\overline{h}\,\overline{g_1} =
\overline{h}\,\overline{g_2}$ has no zero in it. Move everything to one side and
factor: $\overline{h}\,(\overline{g_1} - \overline{g_2}) = \overline{0}$. Now
the hypothesis has something to bite on.

That is the whole trick for injectivity of a linear map, every time: never
compare two inputs, subtract them and show the difference is $\overline{0}$.

Your "if $\overline{g_1}, \overline{g_2} \neq \overline{0}$ both sides are not
$\overline{0}$" is true and it is not going anywhere --- it tells you about the
two sides, when you need to produce a product that IS zero. The WLOG about
degrees below $n$ is also fine and also unused; degrees of representatives never
enter this argument. Drop both lines.

Problem 1(b): $F$ a field, $f \in F[x]$ non-constant of degree $n$,
$A = F[x]/(f)$. Show that if $A$ is an integral domain, then $A$ is a field.

What this uses:

- integral domain --- commutative ring, $\overline{1} \neq \overline{0}$, no zero divisors: $\overline{u}\,\overline{v} = \overline{0}$ forces $\overline{u} = \overline{0}$ or $\overline{v} = \overline{0}$.
- field --- every non-zero element has a multiplicative inverse.
- $A = F[x]/(f)$ --- classes $\overline{g} = g + (f)$, equal exactly when the difference lies in $(f)$.
- $\dim_F A = n$ --- 1(a), which you closed; $A$ is a finite-dimensional $F$-vector space.
- $T$ --- multiplication by $\overline{h}$, sending $\overline{u} \mapsto \overline{h}\,\overline{u}$; $F$-linear.
- injective --- the only $\overline{u}$ with $T(\overline{u}) = \overline{0}$ is $\overline{u} = \overline{0}$.
- rank--nullity --- an $F$-linear map from a finite-dimensional space to itself is injective exactly when it is surjective.

Fixed: $\overline{h} \in A$, $\overline{h} \neq \overline{0}$, and $T$ is
multiplication by $\overline{h}$.

**One line. You now have $\overline{h}\,(\overline{g_1} - \overline{g_2}) =
\overline{0}$ with $\overline{h} \neq \overline{0}$. What does the integral
domain hypothesis force, and why does that make $T$ injective? Stop there.**
