---
kind: question
title: "An existence claim is paid with a *witness*. Here is one: $g = x$."
---

Your aside, first — everything else waits.

> *Aside: $g(x)$ exists because suppose all $g \in R[x] \setminus J[x]$ had
> constant $1$…*

You are stuck because contradiction is the long road. An existential claim —
"there is a $g$ with such-and-such" — is discharged by **naming one object and
checking it has the property**. No supposing, no negating.

**Take $g = x$.** Two checks, both one line:

- $x \notin J[x]$. Membership in $J[x]$ demands **every** coefficient lie in
  $J$. The coefficient of $x^1$ in $x$ is $1$, and $1 \notin J$ because $J$ is
  proper: an ideal containing $1$ contains $r = r \cdot 1$ for every $r \in R$,
  so it would be all of $R$.
- Its constant term is $0$, so it satisfies the side condition you wrote on
  the page.

Your contradiction route would get there too, but notice where it lands: the
negation of "every $g$ has constant term $1$" is "**some** $g$ does not" — which
is the witness you were trying to avoid producing. Cheaper to produce it.

And a named $g$ buys you something an assumed $g$ never does: you can compute
with it.

---

## Exercise 3.26, part 2 — still open

Let $J$ be a proper prime ideal in an integral domain $R$. Show that $J[x]$ is
**not** a maximal proper ideal in $R[x]$: produce an ideal $I$ with

$$J[x] \;\subsetneq\; I \;\subsetneq\; R[x].$$

### Everything the question below uses

- $R[x]$: polynomials in $x$ with coefficients in $R$. For $f \in R[x]$, $f_i$
  is the coefficient of $x^i$; $f_0$ is the **constant term**.
- $J[x]$: the polynomials **every one of whose coefficients lies in $J$**.
- $I_g = \{\, a(x) + g(x)r(x) \;:\; a \in J[x],\ r \in R[x] \,\}$ — your set,
  with the $g$ named. Fixed here at $g = x$: $I_x$.
- *Proper*: $I \neq R[x]$; equivalently $1 \notin I$.
- *Ideal*: closed under subtraction and absorbs multiplication by all of
  $R[x]$. You proved $I_g$ has both, for every $g$ — that is banked.
- $1$ as a polynomial means the constant polynomial $1$: constant term $1$,
  every other coefficient $0$.

---

**Your move.** Fix $g = x$. Take a general element of $I_x$, namely
$a(x) + x\,r(x)$ with $a \in J[x]$ and $r \in R[x]$.

Write down its **constant term** — one expression, naming which coefficient of
which polynomial it is. Then say which subset of $R$ every constant term of
every element of $I_x$ is forced to sit in.

One line each. Multiplying out is not required; think about what $x \cdot r(x)$
contributes to $x^0$.
