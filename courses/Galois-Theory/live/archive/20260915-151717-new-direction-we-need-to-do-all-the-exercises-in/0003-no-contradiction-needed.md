---
kind: lesson
title: no-contradiction-needed
---
---
kind: lesson
title: There is no contradiction to reach — use the element 1
---
You cannot reach the contradiction because there isn't one. Degree $1$
forces $L = K$ **directly**, in two lines, out of the very spanning
statement you already wrote. Drop the "suppose $\exists \ell_3 \notin K$"
frame entirely.

Your line $\ell_1 = k^{-1}\ell_3$ is true and it is a dead end: it
describes $\ell_1$ in terms of $\ell_3$, and you know nothing whatever
about $\ell_3$. You fed the spanning property an element you had no grip
on.

There is exactly one element of $L$ whose membership in $K$ you are sure
of before you start: $1$. It is in $L$, and it is in $K$, because $K$ is
a subfield of $L$ and every field contains $1$. Feed the spanning
property *that* one.

One more thing to fix in the frame. $K \subseteq L$ is given — $K$ is a
subfield of $L$. So proving $L = K$ needs only the other inclusion:
every $\ell \in L$ lies in $K$.

Words used above:

- **$[L:K]$** — the number of elements in a basis of $L$ as a vector space over $K$.
- **Spans** — every $\ell \in L$ is a sum of $K$-multiples of the set's members. With one member $\ell_1$, that sum is a single term: for every $\ell \in L$ there is $k \in K$ with $k\ell_1 = \ell$. This is your own line, and it is right.
- **Subfield** — $K \subseteq L$, closed under $+$, $\times$, negatives and inverses of nonzero elements, containing $0$ and $1$.

**Your move.** Take $[L:K] = 1$ with basis $\{\ell_1\}$, and apply your
spanning line to the single element $\ell = 1$. That gives some
$k_0 \in K$ with $k_0 \ell_1 = 1$.

Two things, one line each: why is $k_0 \neq 0$, and what does that
equation therefore tell you about $\ell_1$?

Answer those and $L = K$ falls out immediately, and then 4.1 is finished.
