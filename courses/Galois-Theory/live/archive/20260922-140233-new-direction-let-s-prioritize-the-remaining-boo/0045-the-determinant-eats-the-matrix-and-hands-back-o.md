---
kind: lesson
title: the-determinant-eats-the-matrix-and-hands-back-one-polynomial
---
**A determinant turns a matrix into a single element, so $\det(xI - T_{\alpha})$
is one polynomial, never a matrix.** The matrix goes in at the top; one thing in
$K[x]$ comes out at the bottom.

Watch it happen on your own case. With $K = \mathbb{Q}$ and $\alpha = \sqrt{2}$,
the matrix $xI - T_{\alpha}$ has top row $x$, $-2$ and bottom row $-1$, $x$. Its
determinant is $x \cdot x - (-2)(-1) = x^2 - 2$. Rational coefficients, one
variable, degree $2$. Nothing matrix-shaped survives the determinant, because
the determinant is a sum of products of entries and each entry is in $K[x]$.

So $\chi(x) = x^2 - 2$, with a plain $2$. The $2I$ belongs to a different
sentence. Feed $\chi$ the *matrix* $T_{\alpha}$ and you get the matrix
$T_{\alpha}^2 - 2I$, which is the zero matrix. Feed $\chi$ the *field element*
$\alpha$ and you get the number $\alpha^2 - 2$, which is $0$ in $\mathbb{Q}$.
One polynomial, two things you are allowed to substitute into it, two different
kinds of zero.

What this uses:

- $K[x]$ --- polynomials in $x$ with coefficients in the field $K$.
- $T_{\alpha}$ --- multiplication by $\alpha$, a linear map of $K(\alpha)$ over $K$, written as a matrix in the basis $1, \alpha, \dots, \alpha^{n-1}$.
- $xI - T_{\alpha}$ --- the matrix with $x$ down the diagonal and the entries of $T_{\alpha}$ subtracted; its entries live in $K[x]$.
- $\chi$ --- short for $\det(xI - T_{\alpha})$.
- column convention --- column $j$ of the matrix holds the coordinates of the image of the $j$-th basis vector.

**Your move.** Take $K = \mathbb{Q}$ and $\alpha = 2^{1/3}$, so $n = 3$ and the
basis is $1, \alpha, \alpha^2$. Multiplication by $\alpha$ sends $1 \mapsto
\alpha$, $\alpha \mapsto \alpha^2$, and $\alpha^2 \mapsto 2$, which makes
$T_{\alpha}$ the matrix with columns $(0,1,0)$, $(0,0,1)$, $(2,0,0)$. Write down
$xI - T_{\alpha}$ and take its determinant. Which element of $\mathbb{Q}[x]$ do
you get, and what is its degree?
