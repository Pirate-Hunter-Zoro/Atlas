---
kind: lesson
title: the-degree-is-where-powers-of-beta-stop-being-new
---
Both right: $[\mathbb{Q}(\beta):\mathbb{Q}] = 3$, and the basis is
$\{1, \beta, \beta^2\}$.

Now your question, which is the one worth asking. The minimal polynomial's
degree is the number of basis elements because that degree is the exact point
where powers of $\beta$ stop being new. Division with remainder is what makes
that true.

Every element of $\mathbb{Q}(\beta)$ is a polynomial in $\beta$ — the fact you
worked out in 4.10. So take any polynomial $h$ in $\mathbb{Q}[x]$ and divide
$h(x)$ by $x^3 - 2$: that gives $h(x) = q(x)(x^3 - 2) + r(x)$ with $r$ of degree
at most $2$. Now substitute $\beta$. The middle term dies, because
$\beta^3 - 2 = 0$. So $h(\beta) = r(\beta)$, and every element of
$\mathbb{Q}(\beta)$ is $a + b\beta + c\beta^2$. Nothing above $\beta^2$ survives
the division.

That is the spanning half. Independence is the same fact read backwards. If
$a + b\beta + c\beta^2 = 0$ with $a, b, c$ not all zero, then $a + bx + cx^2$ is
a non-zero polynomial of degree at most $2$ with $\beta$ as a root — shorter
than the minimal polynomial, which is exactly what "minimal" forbids. So three
elements, and not two.

What it uses:

- $\beta$ — a root of $x^3 - 2$ over $\mathbb{Q}$, so $\beta^3 = 2$.
- Minimal polynomial of $\beta$ over $K$ — the monic polynomial in $K[x]$ of
  least degree with $\beta$ as a root.
- $K(\beta)$ — the smallest field containing both $K$ and $\beta$.
- Division with remainder in $K[x]$ — for any $h$ and non-zero $d$, there are
  $q$ and $r$ with $h = qd + r$ and $\deg r < \deg d$.
- Basis — a linearly independent spanning list; its length is the dimension
  $[M:L]$.

**Your move.** One reduction, by hand, using $\beta^3 = 2$ and nothing else.
Write $\beta^4$ in the form $a + b\beta + c\beta^2$ with $a, b, c$ rational.
