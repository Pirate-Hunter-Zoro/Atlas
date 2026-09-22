---
kind: lesson
title: nothing-is-assumed-algebraic-is-one-of-two-cases
---
Nothing is being assumed — that is a case split, and you were handed the short
half of it first. $\gamma$ is one element of $K(\alpha,\beta)$. Over $K$ every
element is either algebraic or transcendental, and there is no third option,
because *transcendental over $K$* is defined as *not algebraic over $K$*. To
show no $\gamma$ at all generates $K(\alpha,\beta)$ you must kill both kinds of
$\gamma$. The algebraic kind dies in two lines from facts already on the board,
so it goes first. The transcendental kind is the real work, and it is the next
question.

One word in your copy of the statement: $\alpha \notin K$ **but algebraic over
$K$**, not *in* $K$. Both prepositions appear in that one line and they do
different jobs — *in* is membership, *over* names the field the coefficients
come from.

**Exercise 4.10.** Suppose $K(\alpha, \beta) : K$ is an extension, that $\alpha$
is algebraic over $K$ but not in $K$, and that $\beta$ is transcendental over
$K$. Show that $K(\alpha, \beta) : K$ is not simple.

**Your move**, still the algebraic half. Suppose $\gamma \in K(\alpha, \beta)$
with $K(\gamma) = K(\alpha, \beta)$, and suppose $\gamma$ is algebraic over $K$.
One of 4.10's hypotheses breaks. Name which one, and give the chain of two facts
that breaks it. You proved both facts already. Two sentences is enough.

What it uses:

- $L : K$ an extension — $K$ is a subfield of the field $L$.
- $K(\alpha, \beta)$ — the smallest subfield of $L$ containing $K$, $\alpha$ and $\beta$.
- Simple extension — $L : K$ is simple when $L = K(\gamma)$ for some single $\gamma \in L$.
- Algebraic over $K$ — a root of some non-zero polynomial in $K[x]$.
- Transcendental over $K$ — not algebraic over $K$: no non-zero polynomial in $K[x]$ has it as a root.
- $[L:K]$ — the dimension of $L$ as a vector space over $K$.
- The degree fact — if $\gamma$ is algebraic over $K$ then $[K(\gamma):K]$ is finite, with basis $1, \gamma, \dots, \gamma^{n-1}$ for $n$ the least degree of a non-zero polynomial in $K[x]$ killing $\gamma$.
- The membership fact — every element of a finite extension of $K$ is algebraic over $K$.
