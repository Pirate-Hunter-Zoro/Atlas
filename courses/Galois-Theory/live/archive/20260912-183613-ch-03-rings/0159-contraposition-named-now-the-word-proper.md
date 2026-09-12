---
kind: correct
title: "Contraposition, and you negated the *or* correctly. Part 1 needs one more word: proper."
---

That is the sentence. You proved
$f \notin J[x]$ and $g \notin J[x]$ $\Rightarrow$ $fg \notin J[x]$, and the
definition asks for $fg \in J[x] \Rightarrow f \in J[x]$ or $g \in J[x]$. Those
two are contrapositives of each other, so proving either one gives the other.

The part that is easy to get wrong and that you got right: the negation of
"$f \in J[x]$ **or** $g \in J[x]$" is "$f \notin J[x]$ **and**
$g \notin J[x]$". An *or* flips to an *and* under negation. Your first line
starts from both non-memberships, which is exactly what the contrapositive
hands you.

So the implication half of part 1 is closed.

But *prime ideal* is two conditions, not one, and you have only done the second.
Look at the definition below and see which word has no line on your page yet.

---

## Exercise 3.26

Suppose $J$ is a proper prime ideal in an **integral domain** $R$.

1. Show that $J[x]$ is prime in $R[x]$.
2. Show that $J[x]$ is **not** a maximal proper ideal in $R[x]$.

### Everything the statement uses

- $R$: a commutative ring with identity $1$. An **integral domain**: no zero divisors — $ab = 0$ forces $a = 0$ or $b = 0$.
- $R[x]$: polynomials in $x$ with coefficients in $R$. A polynomial $a$ is its list of coefficients $a_{0}, a_{1}, a_{2}, \dots$, all but finitely many zero; $a_{i}$ is the coefficient of $x^{i}$. The identity of $R[x]$ is the constant polynomial $1$.
- *Ideal* $I$: closed under addition, and **absorbing** — $c \in I$, $r \in R$ $\Rightarrow$ $rc \in I$.
- *Proper*: $I \neq R$; equivalently $1 \notin I$.
- *Prime ideal* $J$: **proper**, and $cd \in J$ $\Rightarrow$ $c \in J$ or $d \in J$.
- *Maximal proper ideal* $M$: proper, and no ideal sits strictly between $M$ and $R$.
- $J[x]$: the polynomials **every one of whose coefficients lies in $J$**. So $a \notin J[x]$ means *some* coefficient of $a$ is outside $J$.
- Hypothesis in force: $J$ itself is proper, so $1 \notin J$.

---

**Your move — one line.** Show $J[x] \neq R[x]$. Name a single polynomial that
lies in $R[x]$ but not in $J[x]$, and say which hypothesis on $J$ is what puts
it outside.
