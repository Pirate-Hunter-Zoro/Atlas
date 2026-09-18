---
kind: lesson
title: the-1-you-feed-in-is-a-vector-not-the-number-one
---
**The $1$ I meant is the element $1$ of $K(\alpha)$, not the number $1$
substituted for $x$.** So there is no $\det$ left either --- once you put
$T_{\alpha}$ in for $x$, $\chi(T_{\alpha})$ is a linear map, and you apply it to
a vector.

Two different substitutions, and only one of them is Cayley--Hamilton. Putting
the scalar $1$ in for $x$ gives the number $\chi(1) = \det(I - T_{\alpha})$, and
that number is not claimed to be anything. Putting the MAP $T_{\alpha}$ in for
$x$ gives $T_{\alpha}^{n} + c_{n-1}T_{\alpha}^{n-1} + \cdots + c_{0}I$, a sum of
linear maps on $K(\alpha)$, and Cayley--Hamilton says that sum is the zero map.
A map is zero exactly when it kills every vector, so feed it one vector and read
off an equation. The vector I want is $1$.

The exercise, in full:

**4.3.** Suppose that $K(\alpha) : K$ is a finite simple extension. For each
$\beta$ in $K(\alpha)$, let $T_{\alpha}(\beta) = \alpha\beta$. Then
$T_{\alpha}$ is a linear mapping of $K(\alpha)$, considered as a vector space
over $K$, into itself. Show that $\det(xI - T_{\alpha})$ is the minimal
polynomial of $\alpha$ over $K$.

What this uses:

- $n$ --- the degree $[K(\alpha):K]$, the dimension of $K(\alpha)$ as a vector space over $K$.
- $m$ --- the minimal polynomial of $\alpha$ over $K$: monic, in $K[x]$, least degree with $\alpha$ as a root, and that degree is $n$.
- $\chi$ --- write $\chi(x)$ for $\det(xI - T_{\alpha})$: monic, degree $n$, coefficients $c_{0}, \ldots, c_{n-1}$ in $K$.
- $T_{\alpha}^{k}$ --- $T_{\alpha}$ done $k$ times: multiply by $\alpha$, then again, $k$ times over.
- $I$ --- the identity map, which is $T_{\alpha}^{0}$.
- the element $1$ --- the multiplicative identity of $K(\alpha)$, sitting in it as a vector.

**Your move.** One line, no $\chi$ in it: what is $T_{\alpha}^{k}(1)$? Give it
for a general $k$, in terms of $\alpha$. That only.
