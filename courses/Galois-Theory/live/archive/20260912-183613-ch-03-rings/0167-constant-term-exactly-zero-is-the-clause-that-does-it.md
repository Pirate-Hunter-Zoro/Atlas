---
kind: correct
title: "\"$xr(x)$ contains no constants unless it is $0$\" is the clause that does it. 3.26 is closed."
---

You did not write the $x^0$ equation I asked for. You wrote the fact that makes
it true, which is the part I could not supply for you:

> *$xr(x)$ contains no constants unless it is $0$.*

That is the sharp version — constant term **exactly $0$**, not merely "not
$1$". With it, the objection from last card dies: $3 + (-2) = 1$ needs both
pieces to push something into the $x^0$ slot, and $xr(x)$ pushes nothing. So
the constant term of $a(x) + xr(x)$ is $a_0$ alone, $a_0 \in J$, and $1 \notin
J$. That one substitution is the line I am writing into the proof; the two
facts it stands on are both yours.

**Exercise 3.26 is closed, both parts.** $I$ is an ideal, $J[x] \subseteq I$
at $r = 0$, $x \in I \setminus J[x]$, and $1 \notin I$ — so
$J[x] \subsetneq I \subsetneq R[x]$ and $J[x]$ is not maximal.

*Pen, not maths, and I am fixing all three in the write-up: "proper ideal of
$R$" where you mean $R[x]$, "subideal" where you mean ideal, and $g(x)$ used
in the last two lines without ever being defined as $g = x$.*

---

## The sheet is down to one. Exercise 3.2

> Suppose that $R$ is an integral domain, with field of fractions $F$. Show
> that the field of fractions of $R[x_1, \ldots, x_n]$ can be identified
> naturally with $F(x_1, \ldots, x_n)$.

We will run it at $n = 1$ first: the field of fractions of $R[x]$ is
$F(x)$. Nothing about the argument changes for more variables.

### Everything the question uses

- **Integral domain**: a ring in which $rs = 0$ forces $r = 0$ or $s = 0$.
- **Field of fractions $F$ of an integral domain $R$**: the field of formal
  fractions $r/s$ with $r, s \in R$ and $s \neq 0$, where $r/s = r'/s'$ means
  $rs' = r's$. $R$ sits inside it as the fractions $r/1$. Example:
  $\mathbb{Q}$ is the field of fractions of $\mathbb{Z}$.
- $R[x]$: polynomials in $x$ with coefficients in $R$. It is again an integral
  domain when $R$ is — Garling proves this in §3.2, and you may use it.
- So **$\mathrm{Frac}(R[x])$** means: ratios $p(x)/q(x)$ of two polynomials
  with coefficients **in $R$**, $q \neq 0$.
- **$F(x)$** means $\mathrm{Frac}(F[x])$: ratios $P(x)/Q(x)$ of two polynomials
  with coefficients **in $F$**, $Q \neq 0$.
- The two differ only in where the coefficients are allowed to live.
  $\mathrm{Frac}(R[x]) \subseteq F(x)$ is free, since $R \subseteq F$. The
  content is the other direction.
- **"Identified naturally"** means: a field isomorphism between them that
  leaves every element of $R[x]$ where it is.

---

**Your move.** One concrete instance, in $\mathbb{Q}(x)$, with $R =
\mathbb{Z}$ and $F = \mathbb{Q}$. Take

$$\frac{\tfrac{1}{2}x + \tfrac{1}{3}}{x - \tfrac{5}{7}}.$$

**Rewrite it as a ratio of two polynomials whose coefficients are all
integers**, so that it visibly lies in $\mathrm{Frac}(\mathbb{Z}[x])$.

One line. You are allowed to multiply top and bottom by the same nonzero
thing; say what you multiplied by.
