---
kind: lesson
title: coordinates-go-down-a-column-not-across-a-row
---
**Both images are right and the matrix is their transpose.** You have
$T_{\alpha}(1) = \sqrt{2}$ and $T_{\alpha}(\sqrt{2}) = 2$, which is exactly the
content of the step. The convention is the only thing off: the coordinates of an
image go DOWN a column, not across a row.

$$T_{\alpha}(1) = 0 \cdot 1 + 1 \cdot \sqrt{2}, \text{ so the first column is } (0, 1)^{T}.$$
$$T_{\alpha}(\sqrt{2}) = 2 \cdot 1 + 0 \cdot \sqrt{2}, \text{ so the second column is } (2, 0)^{T}.$$

Top row $0, 2$; bottom row $1, 0$. Here it would not have bitten you, since a
matrix and its transpose have the same characteristic polynomial, but write it
the right way round now: in dimension $n$ the two are genuinely different
matrices.

The exercise, in full:

**4.3.** Suppose that $K(\alpha) : K$ is a finite simple extension. For each
$\beta$ in $K(\alpha)$, let $T_{\alpha}(\beta) = \alpha\beta$. Then
$T_{\alpha}$ is a linear mapping of $K(\alpha)$, considered as a vector space
over $K$, into itself. Show that $\det(xI - T_{\alpha})$ is the minimal
polynomial of $\alpha$ over $K$.

What this uses:

- minimal polynomial of $\alpha$ over $K$ --- the monic polynomial in $K[x]$ of least degree with $\alpha$ as a root; its degree is $n = [K(\alpha):K]$.
- $I$ --- the $n$ by $n$ identity matrix, ones down the diagonal and zeros elsewhere.
- $\det(xI - T_{\alpha})$ --- the characteristic polynomial: put $x$ down the diagonal, subtract the matrix, take the determinant of what is left. Monic of degree $n$, coefficients in $K$.
- determinant of a 2 by 2 matrix --- entries $a, b$ on top and $c, d$ below give $ad - bc$.

**Your move.** With that matrix for $T_{\alpha}$, form $xI - T_{\alpha}$ and
compute its determinant. One polynomial in $x$. That only.
