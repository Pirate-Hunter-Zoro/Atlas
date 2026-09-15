---
kind: lesson
title: both-cases-done-now-name-the-fields
---
Both cases are right, and that is the whole force of the exercise. Your
top block is the tower law $[L:K] = [L:M][M:K]$ with $p$ on the left, and
the only two factorisations of a prime into positive degrees underneath:
$1 \cdot p$ and $p \cdot 1$. Your lemma turns the first into $M = L$ and
the second into $M = K$. Your second block then checks both are
consistent, $[L:K] = [L:L][L:K]$ and $[L:K] = [L:K][K:K]$, because a
field has degree $1$ over itself.

What is missing is the answer. 4.1 asks which *fields* are intermediate,
so the answer is a list of fields, and your page ends on a list of degree
equations. The two lines $M = L$ and $M = K$ are the ones you worked for
and never wrote down.

One thing to settle before you write that list. Both $K$ and $L$ are
intermediate fields, trivially, since $K \subseteq K \subseteq L$ and
$K \subseteq L \subseteq L$. So the list has two entries — unless they
are the same field. Decide which, using $p$.

Everything it uses:

- **Extension $L:K$** — $L$ is a field, $K$ a subfield of it.
- **Degree $[L:K]$** — the dimension of $L$ as a vector space over $K$.
- **Intermediate field $M$** — a field with $K \subseteq M \subseteq L$.
- **Your lemma** — $[L:K] = 1$ forces $L = K$. Proved on your page.
- **Prime** — an integer $p \ge 2$; in particular $p \neq 1$.

**Your move.** One line: is $K = L$ possible here, and why not?
