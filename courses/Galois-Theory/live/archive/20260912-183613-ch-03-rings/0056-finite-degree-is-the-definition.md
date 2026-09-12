---
kind: note
title: Since the definition. Finite degree is what "polynomial" means.
---

Yes — $f$ and $g$ have finite degree, and nothing imposed that on them. It is
what being an element of $K[x]$ *is*.

Look at the problem's own first line: $f = a_{0} + a_{1}x + \cdots +
a_{n}x^{n}$. The $n$ is already there. $K[x]$ is the set of **finite** sums
$\sum_{i} a_{i}x^{i}$ — equivalently, coefficient sequences $(a_{0}, a_{1},
\dots)$ in which only finitely many $a_{i}$ are non-zero. That is why
$\deg h$ — the largest $i$ with $a_{i} \neq 0$ — exists at all: there are only
finitely many non-zero ones to pick a largest from. The object that *does* allow
infinitely many non-zero coefficients is the formal power series ring
$K[[x]]$, and $\Phi$ is not defined on it.

You already said this yourself two pages ago: *you can't just have $\delta_{0},
\delta_{1}, \delta_{2}, \dots$ — that's an infinite polynomial.* Correct. Same
fact, and it applies to $h$ as much as to that product.

**And here is what I think you are actually objecting to.** Degree is not
*bounded* over $K[x]$. There is no ceiling; $K[x]$ contains polynomials of every
degree you like. What is true is that each individual polynomial has its own
finite degree. The argument needs only the second, and never asks how big $n$ is
— $n$ is whatever $h$'s degree happens to be, and you neither choose it nor need
to know it.

(The zero polynomial is the one exception: no non-zero coefficient, so no
largest index, so no degree. Irrelevant here — it is the case you are trying to
land on.)

---

**Your move.** Two objects, written in $\mathbb{Q}$-coefficients:
$$A = 1 + x + x^{2} + x^{3} + \cdots \quad\text{(every coefficient } 1),
\qquad B = x^{1000000}.$$
Say which of $A$, $B$ lies in $\mathbb{Q}[x]$, and give the degree of the one
that does.
