---
kind: lesson
title: zero-is-right-now-chi-has-a-root-and-so-does-m
---
**Zero, and your matrix square is the reason.** You squared
$[[0,2],[1,0]]$ and got $[[2,0],[0,2]]$, which is $2I$, so $T_{\alpha}^{2} - 2I$
is the zero map and sends every vector to $0$. Read through the bridge
$T_{\alpha}^{k}(1) = \alpha^{k}$, that same line says $\alpha^{2} - 2 = 0$,
i.e. $\chi(\alpha) = 0$.

Now drop the $\sqrt{2}$ and do it for general $n$. Cayley--Hamilton says
$\chi(T_{\alpha})$ is the zero map for *every* square matrix, so you never have
to square anything again. Feed the zero map the vector $1$: each
$T_{\alpha}^{k}$ sends $1$ to $\alpha^{k}$, and a constant term $c$ acts as
$cI$, which sends $1$ to $c$. So $\chi(T_{\alpha})(1)$ is the element
$\chi(\alpha)$, and it is $0$.

So $\chi$ is a polynomial over $K$ with $\alpha$ as a root. You already have
another one: $m$.

The exercise, in full:

**4.3.** Suppose that $K(\alpha) : K$ is a finite simple extension. For each
$\beta$ in $K(\alpha)$, let $T_{\alpha}(\beta) = \alpha\beta$. Then
$T_{\alpha}$ is a linear mapping of $K(\alpha)$, considered as a vector space
over $K$, into itself. Show that $\det(xI - T_{\alpha})$ is the minimal
polynomial of $\alpha$ over $K$.

What this uses:

- $T_{\alpha}$ --- the map "multiply by $\alpha$", from $K(\alpha)$ to itself.
- $I$ --- the identity map; in $\chi$ a constant term $c$ becomes $cI$.
- $\chi$ --- short for $\det(xI - T_{\alpha})$, the characteristic polynomial: monic, in $K[x]$, degree $n$.
- Cayley--Hamilton --- $\chi(T_{\alpha})$ is the zero map.
- $\chi(\alpha) = 0$ --- just established, in general.
- $m$ --- the minimal polynomial of $\alpha$ over $K$: monic, in $K[x]$, of least degree with $\alpha$ as a root.
- $n$ --- the degree $[K(\alpha):K]$, and also $\deg m$.
- monic --- leading coefficient $1$.

**Your move.** $\chi$ and $m$ both lie in $K[x]$ and both have $\alpha$ as a
root, and $m$ is the one of least degree. What does that force about $m$ and
$\chi$? One sentence.
