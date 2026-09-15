---
kind: lesson
title: four-four-is-closed-now-prove-prime-degree-is-simple
---
Exercise 4.4 is closed, both halves, with nothing to correct. Your expansion
$\beta^3 - 3\beta^2 + 6\beta - 3$ is right, the nonzero constant let you divide
by 3 and pull $\beta$ out, and
$(1 + \alpha)^{-1} = \tfrac{1}{3}\alpha^2 - \tfrac{1}{3}\alpha + \tfrac{4}{3}$
is the correct answer. I multiplied it back for you:
$(1 + \alpha)(\alpha^2 - \alpha + 4) = \alpha^3 + 3\alpha + 4$, and
$\alpha^3 + 3\alpha = -1$, so that is $3$, and dividing by the $3$ you carried
gives $1$.

**Exercise 4.6.** *Suppose that $[L : K]$ is a prime number. Show that $L : K$
is simple.*

Everything it uses:

- **$L : K$** — an extension: $K$ is a subfield of $L$, so $L$ is a vector space over $K$.
- **$[L : K]$** — the degree, meaning the dimension of $L$ as a vector space over $K$.
- **Simple extension** — one of the form $K(\alpha)$ for a single $\alpha$ in $L$. To prove an extension simple you must produce one element that generates all of it.
- **$K(\alpha)$** — the smallest subfield of $L$ containing $K$ and $\alpha$. It is an intermediate field: $K \subseteq K(\alpha) \subseteq L$.
- **Intermediate field of $L : K$** — a subfield $M$ of $L$ with $K \subseteq M \subseteq L$.
- **Your own 4.1** — when $[L : K]$ is prime, the only intermediate fields are $K$ and $L$. Proved and yours; use it as a result, do not reprove it.
- **Tower law (Theorem 4.2)** — for $L : M : K$, $[L : K] = [L : M][M : K]$.

**Your move.** Write the proof. It is three lines and you already own the hard
one. The only choice in it is which element of $L$ to name, and the whole proof
turns on making that choice so that $K(\alpha)$ cannot be $K$ — say why such an
element exists before you use it. No contradiction is needed anywhere.
