---
kind: wrong
title: neither-summand-is-1-does-not-make-the-sum-not-1
---
---
kind: wrong
title: "Everything except one line is banked. \"Neither summand is $1$\" still does not make the sum $\\neq 1$."
---

The new properness line:

> *$a(x) + x r(x) \neq 1$ for all $r \in R[x]$ since neither $a(x)$ nor
> $x r(x)$ contain the constant $1$.*

**Two things can each fail to be $1$ and still add to $1$.** In $\mathbb{Z}$:
$3 \neq 1$, $-2 \neq 1$, and $3 + (-2) = 1$. "Neither piece is the thing" is
never a reason the sum is not the thing. You replaced one fact about the whole
polynomial with another fact about the whole polynomial.

What actually saves you is sharper, and it is two separate facts about the
$x^0$ slot alone:

1. $x r(x)$ has constant term **exactly $0$** — not merely "not $1$". That is
   why it cannot interfere at all.
2. $a_0$ is not merely "not $1$" by inspection: $a \in J[x]$, so $a_0 \in J$,
   and $1 \notin J$ because $J$ is proper.

Neither of those is on your page. Everything else is: the ideal computation,
$J[x] \subseteq I$ by $r = 0$, and $x \in I$ with $x \notin J[x]$ — all banked,
none of it to be redone.

*Pen, not maths: you wrote "$I$ is a proper ideal of $R$" where you mean
$R[x]$, "subideal" where you mean ideal, and $g(x)$ without ever saying
$g = x$. I will fix those in the write-up.*

---

## Exercise 3.26, part 2 — still open

Let $J$ be a proper prime ideal in an integral domain $R$. Show that $J[x]$ is
**not** a maximal proper ideal in $R[x]$: produce an ideal $I$ with

$$J[x] \subsetneq I \subsetneq R[x].$$

Your $I = \{ a(x) + x r(x) : a \in J[x], r \in R[x] \}$ is the right object,
and $I \neq R[x]$ is the only thing left.

### Everything the question below uses

- $R[x]$: polynomials in $x$ with coefficients in $R$. For $f \in R[x]$, $f_i$
  is the coefficient of $x^i$; $f_0$ is the **constant term**.
- Two polynomials are equal exactly when they agree **coefficient by
  coefficient**. So $f = 1$ means $f_0 = 1$ and $f_i = 0$ for every $i \geq 1$.
- The constant polynomial $1$: its $x^0$ coefficient is $1$, every other
  coefficient is $0$.
- $J[x]$: the polynomials **every one of whose coefficients lies in $J$**. So
  $a \in J[x]$ gives $a_0 \in J$.
- *Proper*: $J \neq R$; equivalently $1 \notin J$, since an ideal containing
  $1$ contains every $r = r \cdot 1$.
- Multiplying by $x$ shifts every coefficient up one place: if $g = x r$, then
  $g_0 = 0$ and $g_{i+1} = r_i$.

---

**Your move.** Argue by contradiction, and only about the $x^0$ slot.

Suppose $a(x) + x r(x) = 1$ for some $a \in J[x]$ and some $r \in R[x]$. **Take
the $x^0$ coefficient of both sides and write down the equation that results**
— an equation between two elements of $R$, with no $x$ anywhere in it.

Then say, in one further line, which of the two facts above that equation
contradicts.

Two lines. Do not multiply anything out.
