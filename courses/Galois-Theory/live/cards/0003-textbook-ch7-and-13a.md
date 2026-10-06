---
kind: question
title: textbook-ch7-and-13a
---
I can't pick the textbook problems yet, because the textbook isn't in this workspace. The `textbook/` folder (where the course keeps its book) is empty, so I have no list of chapter 7 exercises to compare against the sheet. Choosing from memory would mean making up problem numbers.

Send photos of the chapter 7 exercise pages from the book (Garling, *A Course in Galois Theory*, "Splitting fields"). I'll check them against Problems 13–19 and add only the ones that cover something the sheet doesn't.

I'll guess at one gap so you know what to expect. The sheet uses splitting fields but never builds one from scratch. Problem 17 is the only one where you work with a splitting field, $x^4-2$, and it gives you the field to start with. The book's exercises probably cover what's missing: proving a splitting field exists and is unique up to isomorphism, and computing its degree.

Meanwhile, Problem 13(a) is still open.

**Problem 13(a).** Let $p$ be an odd prime, $\zeta = \zeta_p$, $K = \mathbb{Q}(\zeta)$ and $G = \mathrm{Gal}(K/\mathbb{Q})$. Show that $G$ is cyclic of order $p-1$.

**Your check.** Take $p = 5$. Which of $1, \zeta, \zeta^2, \zeta^3, \zeta^4$ can $\sigma(\zeta)$ be? Give a reason that rules out each one you exclude.

What you may use:

- $\zeta_n = e^{2\pi i/n}$: $\zeta_n^n = 1$, and no smaller positive power equals $1$.
- $\mathrm{Gal}(K/\mathbb{Q})$: the field automorphisms of $K$. Each one fixes every rational number.
- An automorphism fixing $\mathbb{Q}$ sends a root of a rational polynomial to another root of that same polynomial.
- An automorphism is injective, and $\sigma(\zeta^k) = \sigma(\zeta)^k$.
- $(\mathbb{Z}/p\mathbb{Z})^\times$: the nonzero residues mod $p$ under multiplication, a group of order $p-1$.

For $p = 5$: which of $1, \zeta, \zeta^2, \zeta^3, \zeta^4$ can $\sigma(\zeta)$ be, and why is each excluded one impossible?
