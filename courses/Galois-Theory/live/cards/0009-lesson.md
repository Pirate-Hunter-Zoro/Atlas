---
kind: lesson
title: yes-finite-and-the-1-beta-shape-is-only-because-the-degree-is-2
---
Yes to the first question, half to the second. $\beta$ algebraic over $K$ does
make $[K(\beta):K]$ finite — that is exactly the theorem your proof leans on, and
your reason is the right one. But "the vectors are $k$ or $k\beta$" holds only
because $\sqrt{2}$ has degree $2$. For a general algebraic $\beta$ the list is
longer.

Here is the finiteness, since you asked for it. Among all non-zero $h \in K[x]$
with $h(\beta) = 0$ there is one of least degree; call that degree $n$. Then $1,
\beta, \beta^2, \dots, \beta^{n-1}$ is a basis of $K(\beta)$ over $K$, so
$[K(\beta):K] = n$, finite. Spanning is division with remainder: divide any
polynomial in $\beta$ by $h$ and the remainder has degree below $n$. So the
general element is $k_0 + k_1\beta + \dots + k_{n-1}\beta^{n-1}$.

For $\beta = \sqrt{2}$ the least degree is $2$, from $x^2 - 2$. So $n = 2$, the
basis is $1, \sqrt{2}$, and your $k + k'\beta$ shape is correct in this case.

**Your move.** Your coordinates for $\gamma = 1 + \sqrt{2}$ are right: $1\cdot 1
+ 1\cdot\sqrt{2}$. Now do $\gamma^2$. Expand $(1+\sqrt{2})^2$ and collect it as
$a + b\sqrt{2}$ with $a, b \in \mathbb{Q}$. Then you have three vectors $1,
\gamma, \gamma^2$ in a $2$-dimensional $\mathbb{Q}$-vector space, so they are
dependent: find rationals $c_0, c_1, c_2$, not all zero, with $c_0 + c_1\gamma +
c_2\gamma^2 = 0$, and write down the polynomial in $\mathbb{Q}[x]$ that this
gives you with $\gamma$ as a root.

What it uses:

- $\mathbb{Q}(\sqrt{2})$ — the smallest subfield of $\mathbb{R}$ containing $\mathbb{Q}$ and $\sqrt{2}$; every element is $a + b\sqrt{2}$ with $a, b \in \mathbb{Q}$.
- $[K(\beta):K]$ — the dimension of $K(\beta)$ as a vector space over $K$.
- Basis — a list whose $K$-combinations give every element of the space, each in exactly one way.
- Linearly dependent over $\mathbb{Q}$ — some $\mathbb{Q}$-combination equals $0$ with the coefficients not all $0$.
- Algebraic over $K$ — a root of some non-zero polynomial in $K[x]$.
- Division with remainder in $K[x]$ — any $g$ can be written $qh + r$ with $r$ of degree below that of $h$.

Two rationals as the coefficients, and a degree-$2$ polynomial at the end.
