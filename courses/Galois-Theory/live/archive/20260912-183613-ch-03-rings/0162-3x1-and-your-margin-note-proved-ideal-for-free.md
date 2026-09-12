---
kind: correct
title: "$3x+1$, with $a = -3x$ and $r = 1$. And your margin note proved *ideal* for free."
---

Right. $I_{3x+1} = \mathbb{Z}[x]$, because $-3x + (3x+1)\cdot 1 = 1$, and $-3x$
does lie in $J[x] = (3)[x]$.

The margin note is worth more than the answer. You checked that
$\{a + gr : a \in J[x],\ r \in R[x]\}$ absorbs multiplication and stays of that
form — and you checked it for a **general** $g$, not just for $3x+1$. So the
absorption half of "$I_g$ is an ideal" is done, once, for every $g$ at the same
time. Do not prove it again below.

The other candidate is the one that matters. $I_x$ was **not** everything —
and that is precisely the ideal part 2 is asking you for.

---

## Exercise 3.26, part 2

Let $J$ be a proper prime ideal in an integral domain $R$. Show that $J[x]$ is
**not** a maximal proper ideal in $R[x]$: produce an ideal $I$ with

$$J[x] \;\subsetneq\; I \;\subsetneq\; R[x].$$

**The candidate**, in general $R$ now, is the one you already built with $g = x$:

$$I \;=\; \{\, a(x) + x\,r(x) \;:\; a \in J[x],\ r \in R[x] \,\}.$$

Three things make that work: $I$ is an ideal (**granted** — your margin note),
$J[x] \subsetneq I$, and $I \subsetneq R[x]$. Two left.

### Everything the question below uses

- $R[x]$: polynomials in $x$ with coefficients in $R$; $a_i$ is the coefficient of $x^i$, $a_0$ the **constant term**.
- $J[x]$: the polynomials **every one of whose coefficients lies in $J$**.
- $I$: the set displayed above — a thing in $J[x]$, plus $x$ times anything at all.
- $\subsetneq$ (**strict** inclusion): every element of the left side is in the right side, **and** some element of the right side is not in the left side. Two claims; the second is the one people forget.
- *Proper*: $J \neq R$; equivalently $1 \notin J$, since an ideal containing $1$ contains every $r = r\cdot 1$.
- Here: $R = \mathbb{Z}$, $J = (3)$, so $J[x]$ is the polynomials all of whose coefficients are multiples of $3$, and $1 \notin J$.

---

**Your move.** Only the second claim of $J[x] \subsetneq I$ — the forgettable one.
In $\mathbb{Z}[x]$ with $J = (3)$, exactly one of these four is in $I$ but **not**
in $J[x]$:

$$3 \qquad x \qquad 3x \qquad 3x^{2} + 3$$

Name it, and say which coefficient of it fails to lie in $(3)$.
