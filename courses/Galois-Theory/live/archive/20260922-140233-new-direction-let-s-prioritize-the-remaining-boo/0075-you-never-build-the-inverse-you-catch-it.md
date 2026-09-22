---
kind: lesson
title: you-never-build-the-inverse-you-catch-it
---
**You don't build it. You prove it is already there.** There is no formula that
takes $\overline{r} = \overline{c_0 + c_1x + \cdots + c_{n-1}x^{n-1}}$ and hands
back its inverse --- and you never need one. The inverse is caught by counting
dimensions, which is exactly why 1(a) came first.

The shape of it: multiplication by $\overline{h}$ is an $F$-linear map
$T \colon A \to A$. If $T$ is injective, then because $A$ is a
finite-dimensional $F$-vector space of dimension $n$, rank--nullity makes $T$
surjective as well. Surjective means $\overline{1}$ is hit: some $\overline{u}$
has $\overline{h}\,\overline{u} = \overline{1}$. That $\overline{u}$ is the
inverse, and it exists without anybody writing its coefficients down.

Your division step is not wasted --- $\overline{h} = \overline{r}$ with
$\deg r < n$ is the standard representative, and it is what 1(a)'s basis is
about. It just isn't the road to the inverse.

Problem 1(b): $F$ a field, $f \in F[x]$ non-constant of degree $n$,
$A = F[x]/(f)$. Show that if $A$ is an integral domain, then $A$ is a field.

What this uses:

- integral domain --- a commutative ring with $1 \neq 0$ and no zero divisors: $\overline{u}\,\overline{v} = \overline{0}$ forces $\overline{u} = \overline{0}$ or $\overline{v} = \overline{0}$.
- field --- every non-zero element has a multiplicative inverse.
- $A = F[x]/(f)$ --- classes $\overline{g} = g + (f)$, equal exactly when the difference lies in $(f)$.
- $\dim_F A = n$ --- 1(a), closed last turn; $A$ is a finite-dimensional vector space over $F$.
- $T$ --- multiplication by $\overline{h}$, the map sending $\overline{u}$ to $\overline{h}\,\overline{u}$; it is $F$-linear, the same map as exercise 4.3.
- injective --- $T(\overline{u}) = T(\overline{v})$ forces $\overline{u} = \overline{v}$; equivalently the kernel is $\{\overline{0}\}$.
- rank--nullity --- an $F$-linear map from a finite-dimensional space to itself is injective exactly when it is surjective.

Fix $\overline{h} \in A$ with $\overline{h} \neq \overline{0}$, and let $T$ be
multiplication by $\overline{h}$.

**One line: why is $T$ injective? Name the hypothesis on $A$ that gives it, and
say what it rules out. Stop there --- the inverse comes for free after.**
