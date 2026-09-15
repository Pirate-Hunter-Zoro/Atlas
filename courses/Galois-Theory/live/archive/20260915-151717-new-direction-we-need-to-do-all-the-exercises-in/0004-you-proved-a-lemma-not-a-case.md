---
kind: lesson
title: You proved a lemma, not a case
---
Both lines are right, and the degree-$1$ case is finished. $k_1 \neq 0$
because $k_1 = 0$ would give $k_1\ell_1 = 0$, not $1$ — exactly your
reason. Then $k_1\ell_1 = 1$ says $k_1 = \ell_1^{-1}$, so
$\ell_1^{-1} \in K$, so $\ell_1 \in K$ because $K$ is closed under
inverses of nonzero elements. Your last three lines close it: any
$\ell \in L$ is $k\ell_1$ for some $k \in K$, and $K$ is closed under
multiplication, so $\ell \in K$. With $K \subseteq L$ given, $L = K$.

One notation fix. $k_1$ names three different scalars on your page: the
general coefficient, the particular one with $k_1\ell_1 = 1$, and then
the coefficient of a general $\ell$. Give the middle one its own name.

Now the part worth seeing. Nothing in that proof used any fact about $L$
and $K$ beyond "$K$ is a subfield of $L$". You did not prove a case of
4.1. You proved a lemma, for every extension: $[L:K] = 1$ forces
$L = K$. It applies to both factors of the tower, so the second one
costs you no new work.

**Exercise 4.1.** *Suppose that $[L:K]$ is a prime number. What fields
are there intermediate between $L$ and $K$?*

Give the complete list, and the proof that nothing else can occur. Write
it for a general prime $p$, not just $7$.

Everything it uses:

- **Extension $L:K$** — $L$ is a field and $K$ is a subfield of it.
- **Degree $[L:K]$** — the dimension of $L$ as a vector space over $K$.
- **Intermediate field $M$** — a field with $K \subseteq M \subseteq L$; then $L:M$ and $M:K$ are extensions in their own right.
- **Tower law** — for $L : M : K$, $[L:K] = [L:M]\,[M:K]$.
- **Prime** — an integer $p \ge 2$ whose only positive divisors are $1$ and $p$.
- A degree is never $0$, because a field contains $1 \neq 0$.
- **Your lemma** — $[L:K] = 1$ forces $L = K$. Proved above, on your page.

**Your move.** The whole exercise, written out.
