---
kind: lesson
title: Chapter 4: the whole run, and the first exercise
---
Chapter 4 has **eleven** exercises and we are doing all of them. This
sitting takes four: **4.1, 4.4, 4.6, 4.5**, in that order.

That is not the printed order. 4.1 and 4.6 are the same tower-law idea
twice, so they belong together. 4.4 is the only exercise in the chapter
where you *compute* with a minimal polynomial instead of talking about
one. 4.5 then uses the minimal polynomial abstractly, which is easier
once you have pushed one around by hand. Left for later sittings: 4.2
and 4.3, then 4.7 through 4.11. 4.3 is the hardest in the chapter and
goes last.

**Exercise 4.1.** *Suppose that $[L:K]$ is a prime number. What fields
are there intermediate between $L$ and $K$?*

The question wants a complete list, and a proof that nothing else can
occur.

Everything 4.1 uses:

- **Extension $L:K$** — $L$ is a field and $K$ is a subfield of it.
- **Theorem 4.1** — $L$ is a vector space over $K$: add inside $L$, scale by elements of $K$.
- **Degree $[L:K]$** — the dimension of that vector space. A positive integer, or infinite.
- **Intermediate field $M$** — a field with $K \subseteq M \subseteq L$. Then $L:M$ and $M:K$ are extensions in their own right.
- **Tower law (Theorem 4.2)** — for $L : M : K$, $[L:K] = [L:M]\,[M:K]$.
- **Prime** — an integer $p \ge 2$ whose only positive divisors are $1$ and $p$.
- A degree is never $0$, because a field contains $1 \neq 0$.

**Your move.** Take $[L:K] = 7$, and let $M$ be any intermediate field,
$K \subseteq M \subseteq L$.

Write the tower law equation for this $M$, then list every possible pair
of values $([L:M], [M:K])$.

Two numbers per pair, and there are not many pairs. Nothing about fields
yet — this is arithmetic.
