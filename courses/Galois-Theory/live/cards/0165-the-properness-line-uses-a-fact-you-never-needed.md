---
kind: wrong
title: the-properness-line-uses-a-fact-you-never-needed
---
---
kind: wrong
title: "Ideal, containment, and strictness all land. The properness line leans on $a(x) \\neq 1$, which is not what saves you."
---

Three of the four things are closed, and closed properly:

- **$I$ is an ideal.** Your absorption computation is right, and the regrouping
  $h(a + xr) = ha + x(rh)$ puts the answer back in the stated form.
- **$J[x] \subseteq I$.** The margin note is correct: $r = 0$.
- **$J[x] \subsetneq I$.** $x \in I$ with $a = 0$, $r = 1$, and $x \notin J[x]$
  because its $x^1$ coefficient is $1 \notin J$ — which you banked in your
  first line.

That leaves $1 \notin I$. Here is the line:

> *$a(x) + x r(x) \neq 1$ $\forall r \in R[x]$ since $a(x) \neq 1$ and
> $x r(x)$ is either $0$ or degree $> 0$.*

**That inference is not valid.** In $\mathbb{Z}[x]$, take $a(x) = 1 + x$ and
$r(x) = -1$. Then $a(x) \neq 1$, and $x r(x) = -x$ has degree $1$, so both of
your hypotheses hold — and $a(x) + x r(x) = 1$ anyway. A polynomial can differ
from $1$ and still be dragged to $1$ once something cancels its higher terms.

So $a \neq 1$ is the wrong fact about $a$. You have a much stronger one and did
not spend it: $a \in J[x]$. That is the fact the whole proof turns on, and it is
about a **single coefficient**, not about the whole polynomial. This is the
second time you have reached for a statement about all of $g$, or all of $a$,
where the argument only ever needed the $x^0$ slot.

---

## Exercise 3.26, part 2 — still open

Let $J$ be a proper prime ideal in an integral domain $R$. Show that $J[x]$ is
**not** a maximal proper ideal in $R[x]$: produce an ideal $I$ with

$$J[x] \subsetneq I \subsetneq R[x].$$

Your $I = \{ a(x) + x r(x) : a \in J[x], r \in R[x] \}$ is the right object,
and only $I \neq R[x]$ is left to argue.

### Everything the question below uses

- $R[x]$: polynomials in $x$ with coefficients in $R$. For $f \in R[x]$, $f_i$
  is the coefficient of $x^i$; $f_0$ is the **constant term**.
- $J[x]$: the polynomials **every one of whose coefficients lies in $J$**. So
  $a \in J[x]$ gives you $a_i \in J$ for every $i$ — in particular $a_0 \in J$.
- *Proper*: $J \neq R$; equivalently $1 \notin J$, since an ideal containing $1$
  contains $r = r \cdot 1$ for every $r \in R$.
- *Ideal*: closed under subtraction, absorbs multiplication by all of $R[x]$.
  Yours has both — banked.
- $1$ as a polynomial: constant term $1$, every other coefficient $0$. So two
  polynomials are equal exactly when they agree coefficient by coefficient.

---

**Your move.** One question, and it is the coefficient one.

Take a general $a(x) + x r(x) \in I$, with $a \in J[x]$ and $r \in R[x]$. Write
down its **constant term**: one expression, naming which coefficient of which
polynomial it is. Then name the subset of $R$ that every constant term of every
element of $I$ is forced to lie in.

Two lines. Nothing needs multiplying out — ask only what $x \cdot r(x)$ can
contribute to the $x^0$ slot.
