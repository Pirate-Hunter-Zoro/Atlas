---
kind: lesson
title: Cycle notation, and what conjugation does
---

A cycle is a list of where things go, read as a loop.

- $(1\,2)$ sends $1 \mapsto 2$, $2 \mapsto 1$, and leaves $3$ alone. A **transposition**.
- $(1\,2\,3)$ sends $1 \mapsto 2$, $2 \mapsto 3$, $3 \mapsto 1$. Nothing is fixed.

Anything not named in the cycle is fixed. That is the whole convention.

**Inverses.** Undoing a loop means walking it backwards, so $(1\,2\,3)^{-1} = (1\,3\,2)$. A transposition is its own inverse: $(1\,2)^{-1} = (1\,2)$.

**Products.** $\sigma\tau$ is composition of functions, so by the usual convention $\tau$ acts first and $\sigma$ second. You compute it one point at a time: take a number, push it through the right-hand factor, push the result through the left-hand factor, write down where it ended up. Do that for all three points and read off the cycle.

**Conjugation** is the expression $ghg^{-1}$: undo $g$, do $h$, redo $g$. It is the single operation the next three exercises all run on, which is why we are checking it on the smallest possible case first.

**Your move:** in $S_3$, with $h = (1\,2)$ and $g = (1\,2\,3)$, compute $ghg^{-1}$ as a cycle, and give its order.
