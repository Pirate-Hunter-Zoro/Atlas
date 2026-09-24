---
kind: question
title: ch05-054-unit-not-one
---
That is the argument, and the shape is right: $a \mid f$, $a \mid -g$, so $a$ is a common divisor. One word in it is wrong, and it is the word the whole contradiction hangs on.

You assumed $a, b \neq 1$. What irreducibility actually gives you is $a, b$ not units. Those are different. Take $K = \mathbb{Q}$ and $a = 2$: then $a \neq 1$, and $f = 2b_0$, $g = -2b_1$ is a perfectly fine factorisation of $f - yg$. Nothing has gone wrong — $2$ is a common divisor of $f$ and $g$, and $f, g$ are still coprime. So "$f$ and $g$ have a common factor, hence not coprime" does not follow from $a \neq 1$ alone.

(Also, $\mathbb{Q}[x]$ on your fourth line should be $K[x]$ — $K$ is an arbitrary field here.)

Everything it uses:

- $K$ — an arbitrary field, not $\mathbb{Q}$.
- unit of $K[x]$ — a nonzero constant, i.e. an element of $K^\times$. Nothing of degree $\geq 1$ is a unit.
- relatively prime, $\gcd(f,g) = 1$ — every common divisor of $f$ and $g$ in $K[x]$ is a unit.
- irreducible — $f - yg$ is not a unit, and in any factorisation $f-yg = ab$ one of $a, b$ is a unit.
- what you have — $a \in K[x]$ with $ab_1 = -g$ and $ab_0 = f$.

So: your hypothesis should read "$a$ is not a unit", not "$a \neq 1$". With that hypothesis, finish the line. $a$ divides $f$ and $a$ divides $g$, and $f, g$ are coprime — what does that force $a$ to be, and where is the contradiction?
