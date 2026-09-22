---
kind: lesson
title: the-two-minus-signs-multiply-to-plus-two
---
**The determinant is $x^{2} - 2$, not $x^{2} + 2$.** Everything above that line
is right: the matrix is now $[[0,2],[1,0]]$ with the images down columns, and
$xI - T_{\alpha}$ is exactly what you wrote.

The slip is one sign. With $a = x$, $b = -2$, $c = -1$, $d = x$, the product
$bc$ is $(-2)(-1) = +2$. Then $ad - bc$ subtracts that: $x^{2} - 2$.

And $x^{2} - 2$ is the minimal polynomial of $\sqrt{2}$ over $\mathbb{Q}$. The
$n = 2$ case is done. Now the reason it was never a coincidence.

The exercise, in full:

**4.3.** Suppose that $K(\alpha) : K$ is a finite simple extension. For each
$\beta$ in $K(\alpha)$, let $T_{\alpha}(\beta) = \alpha\beta$. Then
$T_{\alpha}$ is a linear mapping of $K(\alpha)$, considered as a vector space
over $K$, into itself. Show that $\det(xI - T_{\alpha})$ is the minimal
polynomial of $\alpha$ over $K$.

What this uses:

- $m$ --- the minimal polynomial of $\alpha$ over $K$: monic, in $K[x]$, least degree with $\alpha$ as a root, and that degree is $n = [K(\alpha):K]$.
- $\chi$ --- write $\chi(x)$ for $\det(xI - T_{\alpha})$. Monic, degree $n$, coefficients in $K$.
- Cayley--Hamilton --- a square matrix satisfies its own characteristic polynomial: $\chi(T_{\alpha})$ is the ZERO linear map on $K(\alpha)$.
- $\chi(T_{\alpha})$ --- substitute the map into the polynomial: if $\chi(x) = x^{n} + c_{n-1}x^{n-1} + \cdots + c_{0}$, this means $T_{\alpha}^{n} + c_{n-1}T_{\alpha}^{n-1} + \cdots + c_{0}I$.
- $T_{\alpha}^{k}$ --- $T_{\alpha}$ applied $k$ times, which is multiplication by $\alpha^{k}$.
- the zero map sends every vector to $0$, including the basis vector $1$.

**Your move.** Cayley--Hamilton hands you that $\chi(T_{\alpha})$ is the zero
map. Feed it the single element $1$ of $K(\alpha)$ and write down what comes
out. One equation, no $T$ in it. That only.
