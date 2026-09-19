---
kind: lesson
title: the-subscript-is-over-q-3c-closed-now-problem-1a
---
**3(c) is proved, and $2 \nmid 3$ is the right thing to end on.** The assumption,
3(a), the two degrees, the contradiction --- the whole shape is there.

**One subscript is wrong.** You wrote $\deg m_{\alpha,\mathbb{Q}(\sqrt[3]{2})}$
divides $3$. The minimal polynomial in 3(a) is taken over the BOTTOM field, so it
is $m_{\alpha,\mathbb{Q}}$. Over the top field the statement is empty: every
$\alpha \in \mathbb{Q}(\sqrt[3]{2})$ is a root of $x - \alpha$, a polynomial with
coefficients in $\mathbb{Q}(\sqrt[3]{2})$, so that degree is always $1$ and
"$1 \mid 3$" rules nothing out. With $K = \mathbb{Q}(\sqrt[3]{2})$ and
$F = \mathbb{Q}$ your numbers are $2$ and $3$, and $2 \nmid 3$ lands.
worksheet-field-extensions.tex now carries 3(c) with $\mathbb{Q}$ as the
subscript.

**Problem 1, "Quotients of $F[x]$", part (a).** Let $F$ be a field and let
$f \in F[x]$ be nonconstant of degree $n$. Set $A = F[x]/(f)$. Show that
$\dim_F A = n$.

What this uses:

- $F[x]$ --- polynomials in one variable $x$ with coefficients in $F$.
- $(f)$ --- the set of all multiples $qf$, $q \in F[x]$; an ideal of $F[x]$.
- $A = F[x]/(f)$ --- the quotient ring. Its elements are classes $g + (f)$, and two polynomials name the same class exactly when their difference is a multiple of $f$.
- $\dim_F A$ --- the dimension of $A$ as a vector space over $F$, with $F$ sitting inside $A$ as the constant polynomials.
- Division algorithm in $F[x]$ --- for any $g$ and nonconstant $f$ there are unique $q, r$ with $g = qf + r$ and either $r = 0$ or $\deg r < \deg f$.

**Your move, one thing only.** Take $F = \mathbb{Q}$ and $f = x^3 - x + 1$, so
$n = 3$. Inside $A$, write the class of $x^3$ using only the classes of $1$, $x$
and $x^2$.
