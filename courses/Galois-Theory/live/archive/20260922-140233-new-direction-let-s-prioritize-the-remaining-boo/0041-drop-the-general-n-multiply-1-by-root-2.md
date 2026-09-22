---
kind: lesson
title: drop-the-general-n-multiply-1-by-root-2
---
**Drop the general $n$ and do this in the $\sqrt{2}$ case you already
finished.** The step is one multiplication, and the top line on your page
("all those coefficients must be zero") is leftover 4.7 --- that problem is
closed, so ignore it.

Here is the case you built two cards ago: $K = \mathbb{Q}$,
$\alpha = \sqrt{2}$, basis $(1, \sqrt{2})$. In it, $T_{\alpha}$ is one thing
only: it takes an element of $\mathbb{Q}(\sqrt{2})$ and gives back
$\sqrt{2}$ times that element. No $x$ in it, no determinant in it. The matrix
$[[0,2],[1,0]]$ is just that map written in the basis.

So take the element $1$ of $\mathbb{Q}(\sqrt{2})$ and multiply it by
$\sqrt{2}$. Then take your answer and multiply that by $\sqrt{2}$ too.

The exercise, in full:

**4.3.** Suppose that $K(\alpha) : K$ is a finite simple extension. For each
$\beta$ in $K(\alpha)$, let $T_{\alpha}(\beta) = \alpha\beta$. Then
$T_{\alpha}$ is a linear mapping of $K(\alpha)$, considered as a vector space
over $K$, into itself. Show that $\det(xI - T_{\alpha})$ is the minimal
polynomial of $\alpha$ over $K$.

What this uses:

- $T_{\alpha}$ --- the map "multiply by $\alpha$", from $K(\alpha)$ to itself.
- $T_{\alpha}^{k}$ --- $T_{\alpha}$ done $k$ times over.
- the element $1$ --- the multiplicative identity of $K(\alpha)$, sitting inside it as a vector.
- $n$ --- the degree $[K(\alpha):K]$, the dimension of $K(\alpha)$ over $K$.
- $m$ --- the minimal polynomial of $\alpha$ over $K$: monic, in $K[x]$, least degree with $\alpha$ as a root, and that degree is $n$.
- $\chi$ --- short for $\det(xI - T_{\alpha})$: monic, degree $n$.
- the concrete case, already yours: $K = \mathbb{Q}$, $\alpha = \sqrt{2}$, basis $(1, \sqrt{2})$, $T_{\alpha} = [[0,2],[1,0]]$, $\chi(x) = x^{2} - 2$.

**Your move.** In the $\sqrt{2}$ case: what is $T_{\alpha}(1)$, and what is
$T_{\alpha}$ of that answer? Two elements of $\mathbb{Q}(\sqrt{2})$, written
plainly. No $\chi$, no determinant.
