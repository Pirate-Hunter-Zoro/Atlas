---
kind: note
title: $R/(1)$ is not $\{0,1\}$ — it has one element
---

Fair question, and the answer is that $R/(1)$ is smaller than you think.

Two classes are equal when their difference is in the ideal: $b + (a) = c + (a)$
exactly when $a \mid b - c$. Take $a = 1$, $b = 1$, $c = 0$. Then $1 \mid 1$,
so
$$1 + (1) = 0 + (1).$$
The class of $1$ *is* the class of $0$. Since $(1) = R$, every element of $R$
sits in that one class, and $R/(1)$ has exactly **one** element — the zero
ring, not $\{0, 1\}$. Your $\{0,1\}$ has two distinct elements in it, and that
is the thing that does not exist here.

And the zero ring is not an integral domain, because the definition demands
$1 \neq 0$ — which in $R/(a)$ is exactly the condition you proved from *$a$ is
not a unit* twenty minutes ago. So $a = 1$ is no counterexample: the hypothesis
"$R/(a)$ is an integral domain" already excludes it.

That is not a detour. It is one of the two things the converse needs.

---

**Your move.** Prove it in that direction:

> If $R/(a)$ is an integral domain, then $a$ is not a unit.

Contrapositive is allowed and is probably easier: suppose $a$ *is* a unit, and
show $R/(a)$ fails to be an integral domain. What is $(a)$ when $a$ is a unit?
