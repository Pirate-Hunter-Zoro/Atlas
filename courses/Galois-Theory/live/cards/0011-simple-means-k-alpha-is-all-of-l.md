---
kind: lesson
title: simple-means-k-alpha-is-all-of-l
---
Yes to your last guess: simple means $L = K(\alpha)$ for one single $\alpha$.
That is the whole definition. Your other two guesses are both wrong, and wrong
in the same way.

$\alpha$ is an element of $L$, not of $K$. It may sit anywhere in $L$, and
choosing it is the only real move in 4.6.

$K(\alpha)$ is not $\{k\alpha : k \in K\}$. That set is not a field: it has no
$1$ in it and it is not closed under multiplication. $K(\alpha)$ is the
smallest subfield of $L$ containing every element of $K$ and also $\alpha$. So
it is closed under addition, subtraction, multiplication and inverses of
nonzero elements, and it holds all of $K$, not just multiples of $\alpha$.

"Generates all of $L$" means exactly $K(\alpha) = L$: every element of $L$ is
reachable from $K$ and $\alpha$ using those four operations.

You have already built one of these. In 4.4, $K = \mathbb{Q}$ and $\alpha$ is a
root of $x^3 + 3x + 1$, and $\mathbb{Q}(\alpha) = \{a + b\alpha + c\alpha^2 :
a, b, c \in \mathbb{Q}\}$. Your own
$(1 + \alpha)^{-1} = \tfrac13\alpha^2 - \tfrac13\alpha + \tfrac43$ is an
element of it, and it is not a rational multiple of $\alpha$.

**Your move.** Same 4.4 setup: $K = \mathbb{Q}$, $\alpha^3 + 3\alpha + 1 = 0$.
Is the number $1$ an element of $\{k\alpha : k \in \mathbb{Q}\}$? Answer yes or
no, and name the one computation that settles it. You did that computation two
cards ago.

What the question uses:

- **$\{k\alpha : k \in \mathbb{Q}\}$** — the set of rational multiples of $\alpha$, nothing else in it.
- **$\alpha^{-1}$** — the element of $\mathbb{Q}(\alpha)$ with $\alpha \cdot \alpha^{-1} = 1$; you found it as $-\alpha^2 - 3$.
- **$\mathbb{Q}$** — the rationals. A rational multiple means $k$ is a fraction of integers, not any element of $\mathbb{Q}(\alpha)$.

Then 4.6 comes back, restated in full.
