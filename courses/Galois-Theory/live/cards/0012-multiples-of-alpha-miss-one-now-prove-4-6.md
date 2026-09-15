---
kind: lesson
title: multiples-of-alpha-miss-one-now-prove-4-6
---
Correct, and your reason is better than the one I was expecting. You went
straight at it: $\alpha$ is a root of an irreducible cubic over $\mathbb{Q}$,
so $\alpha \notin \mathbb{Q}$, and $k\alpha = 1$ would force
$\alpha = k^{-1} \in \mathbb{Q}$.

One line was missing and I have supplied it: $k^{-1}$ only exists for
$k \neq 0$, so the case $k = 0$ has to be handled on its own, and it dies at
once because $0 \cdot \alpha = 0 \neq 1$. With that, $1$ is not in
$\{k\alpha : k \in \mathbb{Q}\}$, the set has no multiplicative identity, and
it is not a field. That is the gap between it and $K(\alpha)$.

**Exercise 4.6.** *Suppose that $[L : K]$ is a prime number. Show that
$L : K$ is simple.*

Everything it uses:

- **$L : K$** — an extension: $K$ is a subfield of $L$, so $L$ is a vector space over $K$.
- **$[L : K]$** — the degree, meaning the dimension of $L$ as a vector space over $K$.
- **Simple extension** — one of the form $K(\alpha)$ for a single $\alpha$ in $L$. To prove an extension simple you must produce one element that generates all of it.
- **$K(\alpha)$** — the smallest subfield of $L$ containing all of $K$ and also $\alpha$. It is an intermediate field: $K \subseteq K(\alpha) \subseteq L$.
- **Intermediate field of $L : K$** — a subfield $M$ of $L$ with $K \subseteq M \subseteq L$.
- **Your own 4.1** — when $[L : K]$ is prime, the only intermediate fields are $K$ and $L$. Proved, and yours; use it as a result, do not reprove it.
- **Degree $1$** — $[M : K] = 1$ holds exactly when $M = K$.

**Your move.** Write the proof. Three lines. The only choice in it is which
element of $L$ to name; name it so that $K(\alpha)$ cannot be $K$, and say why
an element like that exists before you use it. No contradiction anywhere.
