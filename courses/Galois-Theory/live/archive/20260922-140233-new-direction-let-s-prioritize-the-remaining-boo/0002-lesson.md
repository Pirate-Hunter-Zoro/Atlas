---
kind: lesson
title: the-reversal-fact-free-now-answer-4-9
---
Take the fact for free. Suppose $1/\pi$ were a root of $c_0 + c_1x + \cdots +
c_nx^n$, rationals not all zero. Put $x = 1/\pi$ and multiply the whole equation
by $\pi^n$: you get $c_0\pi^n + c_1\pi^{n-1} + \cdots + c_n = 0$. So $\pi$ is a
root of the reversed polynomial $c_n + c_{n-1}x + \cdots + c_0x^n$, whose
coefficients are the same list read backwards, so it is not the zero polynomial
either. But $\pi$ is transcendental, so no such polynomial exists. Hence $1/\pi$
is transcendental over $\mathbb{Q}$ as well.

That is the only ingredient 4.9 needs. Now the exercise itself.

**Exercise 4.9.** *Suppose that $a$ and $b$ are complex numbers which are
transcendental over $\mathbb{Q}$. Is $ab$ transcendental over $\mathbb{Q}$?*

Answer yes or no, and prove it. One counterexample settles a no.

Everything 4.9 uses:

- $\mathbb{Q}$ — the rational numbers; $a$ and $b$ live in $\mathbb{C}$.
- $\mathbb{Q}[x]$ — polynomials in $x$ with rational coefficients.
- **algebraic over $\mathbb{Q}$** — a root of some polynomial over $\mathbb{Q}$ that is not the zero polynomial.
- **transcendental over $\mathbb{Q}$** — not algebraic: no non-zero rational polynomial has it as a root.
- $\pi$ — transcendental over $\mathbb{Q}$ (Lindemann, 1882); quote it freely.
- $1/\pi$ — transcendental over $\mathbb{Q}$, by the paragraph above.
- $ab$ — the ordinary product of two complex numbers.
- **counterexample** — one pair $a, b$, each transcendental, whose product is *not* transcendental.

**Your move.** Give the yes or no, and the pair of numbers that proves it. Say in
one sentence why their product is algebraic over $\mathbb{Q}$ — name a non-zero
rational polynomial it is a root of.
