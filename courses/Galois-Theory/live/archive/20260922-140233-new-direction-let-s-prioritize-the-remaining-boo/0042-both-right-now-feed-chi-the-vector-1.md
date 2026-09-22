---
kind: lesson
title: both-right-now-feed-chi-the-vector-1
---
**Both right.** $T_{\alpha}(1) = \sqrt{2}$ and $T_{\alpha}(T_{\alpha}(1)) = 2$.
Notice what those two answers are: $\sqrt{2}$ is $\alpha^{1}$ and $2$ is
$\alpha^{2}$. Applying $T_{\alpha}$ to the vector $1$ exactly $k$ times gives
you the element $\alpha^{k}$. That is the whole bridge between the matrix and
the field.

Now use it on $\chi$. In this case $\chi(x) = x^{2} - 2$, so $\chi(T_{\alpha})$
means the map $T_{\alpha}^{2} - 2I$, where $I$ is the identity map. Feed that
map the vector $1$ and simplify, using the two answers you just wrote.

The exercise, in full:

**4.3.** Suppose that $K(\alpha) : K$ is a finite simple extension. For each
$\beta$ in $K(\alpha)$, let $T_{\alpha}(\beta) = \alpha\beta$. Then
$T_{\alpha}$ is a linear mapping of $K(\alpha)$, considered as a vector space
over $K$, into itself. Show that $\det(xI - T_{\alpha})$ is the minimal
polynomial of $\alpha$ over $K$.

What this uses:

- $T_{\alpha}$ --- the map "multiply by $\alpha$", from $K(\alpha)$ to itself.
- $T_{\alpha}^{k}$ --- $T_{\alpha}$ done $k$ times over; it sends $1$ to $\alpha^{k}$.
- $I$ --- the identity map, which sends every vector to itself.
- $\chi$ --- short for $\det(xI - T_{\alpha})$: monic, degree $n$.
- $\chi(T_{\alpha})$ --- the polynomial $\chi$ with the map $T_{\alpha}$ put in place of $x$; a constant term $c$ becomes $cI$. It is a map, not a number.
- $n$ --- the degree $[K(\alpha):K]$, the dimension of $K(\alpha)$ over $K$.
- $m$ --- the minimal polynomial of $\alpha$ over $K$: monic, in $K[x]$, least degree with $\alpha$ as a root, and that degree is $n$.
- the concrete case, already yours: $K = \mathbb{Q}$, $\alpha = \sqrt{2}$, basis $(1, \sqrt{2})$, $T_{\alpha} = [[0,2],[1,0]]$, $\chi(x) = x^{2} - 2$.

**Your move.** In the $\sqrt{2}$ case: apply the map $T_{\alpha}^{2} - 2I$ to
the vector $1$ and say what you get. One element of $\mathbb{Q}(\sqrt{2})$.
