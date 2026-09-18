---
kind: lesson
title: chi-has-degree-n-and-so-does-m
---
**Degree $n$, where $n = [K(\alpha):K]$.** $\chi$ is $\det(xI - T_{\alpha})$, and
$T_{\alpha}$ is a linear map of an $n$-dimensional $K$-vector space, so its matrix
is $n \times n$. The determinant of $xI$ minus an $n \times n$ matrix is always
monic of degree $n$. And $m$ has degree $n$ too --- that is the fact that gave you
the basis $1, \alpha, \dots, \alpha^{n-1}$ in the first place.

For "how to prove $\chi(\alpha) = 0$ in general": Cayley--Hamilton, which says
$\chi(T_{\alpha})$ is the zero map for every square matrix, so you never square
anything. Feed that zero map the vector $1$. Each $T_{\alpha}^{k}$ sends $1$ to
$\alpha^{k}$, and a constant term $c$ acts as $cI$, sending $1$ to $c$. So
$\chi(T_{\alpha})(1)$ is the field element $\chi(\alpha)$, and it is $0$.

One clerical slip: you wrote $\chi(x) = T_x^2 - 2I$. $\chi$ is a polynomial in
$x$, here $x^2 - 2$; $T_{\alpha}^2 - 2I = 0$ is the matrix statement it came from.

The exercise, in full:

**4.3.** Suppose that $K(\alpha) : K$ is a finite simple extension. For each
$\beta$ in $K(\alpha)$, let $T_{\alpha}(\beta) = \alpha\beta$. Then $T_{\alpha}$
is a linear mapping of $K(\alpha)$, considered as a vector space over $K$, into
itself. Show that $\det(xI - T_{\alpha})$ is the minimal polynomial of $\alpha$
over $K$.

What this uses:

- $n$ --- the degree $[K(\alpha):K]$, the dimension of $K(\alpha)$ over $K$.
- $\chi$ --- short for $\det(xI - T_{\alpha})$: monic, in $K[x]$, degree $n$.
- $m$ --- the minimal polynomial of $\alpha$ over $K$: monic, in $K[x]$, of least degree among polynomials with $\alpha$ as a root; $\deg m = n$.
- monic --- leading coefficient $1$.
- $\chi(\alpha) = 0$ and $m(\alpha) = 0$ --- both established.

**Your move.** $\chi$ and $m$ are both monic, both of degree $n$, both in $K[x]$,
and both kill $\alpha$. Subtract: look at $\chi - m$. What is its degree, what
does it do to $\alpha$, and what does $m$ being of least degree then force it to
be? One sentence.
