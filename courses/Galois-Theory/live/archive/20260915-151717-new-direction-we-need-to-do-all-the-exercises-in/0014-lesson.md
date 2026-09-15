---
kind: lesson
title: which-degree-is-which-and-what-over-L-means
---
$[L:K] = 3$ and $[L(\alpha):L] = 2$, and here is how you get each one.

You get $[L:K]$ from a minimal polynomial. $[\mathbb{Q}(2^{1/3}):\mathbb{Q}]$
is the degree of the minimal polynomial of $2^{1/3}$ over $\mathbb{Q}$, which
is $x^3 - 2$: it is monic, it kills $2^{1/3}$, and it is irreducible over
$\mathbb{Q}$ by Eisenstein at the prime $2$ — the prime divides the lower
coefficients $0, 0, -2$, does not divide the leading $1$, and $2^2$ does not
divide the constant $-2$. Degree $3$, so $[L:K] = 3$.

You get the other one by division. The tower law says
$[\mathbb{Q}(2^{1/6}):\mathbb{Q}] = [L(\alpha):L]\,[L:K]$, and you were handed
the left side as $6$. So $6 = [L(\alpha):L] \cdot 3$, giving
$[L(\alpha):L] = 2$. That is the general move: one degree from an irreducible
polynomial, the other by dividing it out of the tower.

Now your second question. **Over $L$** names the field the coefficients are
allowed to come from, and nothing else. So $m_L$, the minimal polynomial of
$\alpha$ over $L$, is the monic polynomial of least degree whose coefficients
all lie in $L$ and which has $\alpha$ as a root.

Compare the two. Over $\mathbb{Q}$ the minimal polynomial of $2^{1/6}$ is
$x^6 - 2$, degree $6$. Over $L = \mathbb{Q}(2^{1/3})$ you may also use
$2^{1/3}$ itself inside the coefficients, so a shorter polynomial becomes
available, and Theorem 4.4 says exactly how short: its degree is
$[L(\alpha):L]$, which you just found is $2$.

What you need:

- $L = \mathbb{Q}(2^{1/3})$ — every number of the form $a + b\,2^{1/3} + c\,2^{2/3}$ with $a, b, c$ rational.
- $\alpha = 2^{1/6}$ — the positive real sixth root of $2$.
- **Monic** — leading coefficient $1$.
- **Theorem 4.4** — $[L(\alpha):L]$ equals the degree of $m_L$.
- **Eisenstein** — if a prime divides every coefficient but the leading one, and its square misses the constant term, the polynomial is irreducible over $\mathbb{Q}$.

**Your move.** Write down $m_L$: monic, degree $2$, coefficients in $L$, with
$2^{1/6}$ as a root. Then tell me whether every one of its coefficients lies in
$K = \mathbb{Q}$.
