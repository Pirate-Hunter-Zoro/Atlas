---
kind: lesson
title: 4-11-is-closed-now-4-3-multiplication-by-alpha
---
**That is the contradiction, and 4.11 is closed.** $g = 0$ is the impossible
half of it: $f = 0$ on its own is no crime, but every element of $K(t)$ is a
quotient with a non-zero denominator. So no $h \in L$ has $\tau(h) = t$, the map
$\tau$ is not onto, and Theorem 4.8 fails the moment "algebraic" is dropped.
Your argument is typeset in the chapter write-up now, in your steps, with page
29 filed beside it.

Last one in the chapter, and the hardest:

**4.3.** Suppose that $K(\alpha) : K$ is a finite simple extension. For each
$\beta$ in $K(\alpha)$, let $T_{\alpha}(\beta) = \alpha\beta$. Then
$T_{\alpha}$ is a linear mapping of $K(\alpha)$, considered as a vector space
over $K$, into itself. Show that $\det(xI - T_{\alpha})$ is the minimal
polynomial of $\alpha$ over $K$.

What this uses:

- simple --- $K(\alpha)$ is generated over $K$ by the one element $\alpha$.
- finite --- $K(\alpha)$ has finite dimension $n = [K(\alpha):K]$ as a vector space over $K$.
- minimal polynomial of $\alpha$ over $K$ --- the monic polynomial in $K[x]$ of least degree having $\alpha$ as a root. Its degree is exactly $n$.
- $T_{\alpha}$ --- multiplication by $\alpha$. It is $K$-linear because $\alpha(\beta + \gamma) = \alpha\beta + \alpha\gamma$ and $\alpha(k\beta) = k(\alpha\beta)$ for $k \in K$.
- matrix of a linear map in a basis --- column $j$ is the image of the $j$th basis vector, written out in that same basis.
- $\det(xI - T_{\alpha})$ --- the characteristic polynomial: put $x$ down the diagonal, subtract the matrix, take the determinant. Monic of degree $n$, coefficients in $K$.

Before the general proof, one concrete case. Take $K = \mathbb{Q}$ and
$\alpha = \sqrt{2}$, so $n = 2$ and $(1, \sqrt{2})$ is a basis of
$\mathbb{Q}(\sqrt{2})$ over $\mathbb{Q}$.

**Your move.** Write $T_{\alpha}(1)$ and $T_{\alpha}(\sqrt{2})$ each as a
rational combination of $1$ and $\sqrt{2}$, and from those give the $2 \times 2$
matrix of $T_{\alpha}$ in the basis $(1, \sqrt{2})$. That only.
