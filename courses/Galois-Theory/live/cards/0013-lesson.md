---
kind: lesson
title: four-six-is-closed-now-stress-test-4-5
---
Correct, and complete apart from one line I have filled in for you. You picked
$\alpha = \ell$ with $\ell \notin K$, noted $K \subsetneq K(\alpha)$, and let
your own 4.1 finish it. That is the whole proof, and there is no contradiction
anywhere in it.

The line you left out is why $K(\alpha) \neq K$: $\alpha$ lies in $K(\alpha)$
by definition, and $\alpha \notin K$, so the two fields are not the same one.
Your "$[L:K] > 1$" earns a word too — $p$ is prime, so $p \geq 2$, so
$L \neq K$, so an $\ell$ in $L$ outside $K$ exists at all. That closes 4.6.

**Exercise 4.5.** *Suppose that $L(\alpha) : L : K$ and that $[L(\alpha):L]$
and $[L:K]$ are relatively prime. Show that the minimal polynomial of $\alpha$
over $L$ has its coefficients in $K$.*

Everything it uses:

- **$L(\alpha):L:K$** — a tower of extensions: $K \subseteq L \subseteq L(\alpha)$, each field a subfield of the next.
- **$L(\alpha)$** — the smallest subfield containing all of $L$ and also $\alpha$.
- **Minimal polynomial of $\alpha$ over $L$** — the monic polynomial in $L[x]$ of least degree having $\alpha$ as a root. Call it $m_L$.
- **Theorem 4.4** — $[L(\alpha):L]$ equals the degree of $m_L$.
- **Relatively prime** — greatest common divisor $1$.
- **Tower law** — $[L(\alpha):K] = [L(\alpha):L]\,[L:K]$, and the same for any tower.
- **What the conclusion asks** — that every coefficient of $m_L$ lies in the smaller field $K$.

**Your move.** Do not prove it yet. Test it once, on a tower I am handing you:
$K = \mathbb{Q}$, $L = \mathbb{Q}(2^{1/3})$, $\alpha = 2^{1/6}$. Take
$[\mathbb{Q}(2^{1/6}):\mathbb{Q}] = 6$ as given; you do not need to prove that
today. Tell me three things: $[L:K]$, then $[L(\alpha):L]$, then the minimal
polynomial of $\alpha$ over $L$ — and whether its coefficients lie in $K$.
