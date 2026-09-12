---
kind: wrong
title: "Ideal, and $J[x] \\subseteq I$ — both land. One line is false, and *your own last answer* is the counterexample."
---

You skipped the pick and proved it in general. Most of it survives.

**Right:** $I$ absorbs multiplication, and you did it for a general $g$ again.
Picking $r = 0$ gives $J[x] \subseteq I$. Picking $a = 0,\ r = 1$ gives
$g \in I$, and $g \notin J[x]$ by choice — so $J[x] \subsetneq I$, strictly.
That is two of the three claims, closed.

**The false line** is the properness one:

> $g(x)r(x) \neq 1$ for all $r(x) \in R[x]$, since $R[x]$ contains only
> polynomials. So $1 \notin I$.

Two separate problems, and only the second is fatal.

1. An element of $I$ is $a(x) + g(x)r(x)$, not $g(x)r(x)$. Ruling out
   $gr = 1$ does not rule out $a + gr = 1$.
2. You opened with "given $\exists\, g \in R[x] \setminus J[x]$" — an
   **arbitrary** $g$ outside $J[x]$. Card 0161 was two different $g$'s for
   exactly this reason, and you got it right there.

---

## Exercise 3.26, part 2 — still open

Let $J$ be a proper prime ideal in an integral domain $R$. Show that $J[x]$ is
**not** a maximal proper ideal in $R[x]$: produce an ideal $I$ with

$$J[x] \;\subsetneq\; I \;\subsetneq\; R[x].$$

### Everything the question below uses

- $R[x]$: polynomials in $x$ with coefficients in $R$; $a_i$ is the coefficient of $x^i$, $a_0$ the **constant term**.
- $J[x]$: the polynomials **every one of whose coefficients lies in $J$**.
- $I_g = \{\, a(x) + g(x)r(x) \;:\; a \in J[x],\ r \in R[x] \,\}$ — your set, with the $g$ named.
- *Proper*: $I \neq R[x]$; equivalently $1 \notin I$, since an ideal containing $1$ contains every $f = f \cdot 1$.
- Here: $R = \mathbb{Z}$, $J = (3)$, so $J[x]$ is the polynomials all of whose coefficients are multiples of $3$.

---

**Your move.** One line, and you have already written it once.

In $\mathbb{Z}[x]$ with $J = (3)$, take $g = 3x + 1$ — which *is* in
$\mathbb{Z}[x] \setminus J[x]$, so your "given" allows it. Write down one
element of $I_{3x+1}$ that equals $1$: name the $a(x) \in J[x]$ and the
$r(x) \in \mathbb{Z}[x]$.

Then say, in one sentence, what that does to a proof that starts "given
**any** $g \notin J[x]$".
