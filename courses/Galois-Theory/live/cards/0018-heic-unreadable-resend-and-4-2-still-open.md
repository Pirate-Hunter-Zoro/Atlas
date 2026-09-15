---
kind: lesson
title: heic-unreadable-resend-and-4-2-still-open
---
Those two photos came over as HEIC files, and this machine has no decoder for
that format, so I cannot see a single mark on them. Send them again as PNG or
JPEG and I will read them. The quickest route on an iPhone is to screenshot each
photo and send the screenshot instead — a screenshot is always a PNG.

Nothing is lost. 4.2 is still the open question, and if your page is short you
can type the answer instead of re-sending.

**Exercise 4.2.** Let $L : K$ be a finite extension. Let $K_1$ and $K_2$ be
intermediate fields with $L = K(K_1, K_2)$. Show that
$[L:K] \leq [K_1:K]\,[K_2:K]$.

What you need:

- $L : K$ — $K$ is a subfield of $L$; $L$ is then a vector space over $K$.
- $[L:K]$ — the dimension of $L$ as a vector space over $K$. Finite here.
- **intermediate field** — a subfield of $L$ that contains $K$.
- $K(K_1, K_2)$ — the smallest subfield of $L$ containing $K$, $K_1$ and $K_2$.
- **spanning bound** — if a set of $m$ elements spans a vector space, its dimension is at most $m$.
- **Tower law** — for $L : M : K$, $[L:K] = [L:M]\,[M:K]$.

**Your move.** One step, on numbers, not in general. Take $K = \mathbb{Q}$,
$K_1 = \mathbb{Q}(\sqrt{2})$, $K_2 = \mathbb{Q}(\sqrt{3})$, so
$L = \mathbb{Q}(\sqrt{2}, \sqrt{3})$. A basis of $K_1$ over $\mathbb{Q}$ is
$\{1, \sqrt{2}\}$ and a basis of $K_2$ over $\mathbb{Q}$ is $\{1, \sqrt{3}\}$.
Write down a finite set of elements of $L$, built only out of those four, that
spans $L$ over $\mathbb{Q}$ — and say how many elements are in it.
