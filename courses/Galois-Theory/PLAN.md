# Plan

Chapter 5, *Tests for irreducibility*. Five book exercises, chosen by the
student: **5.4, 5.6, 5.7, 5.8, 5.10**. Nothing else in Chapter 5 is assigned;
5.1, 5.2, 5.3, 5.5, 5.9, 5.11 and 5.12 are out of scope and are not to be
taught or transcribed.

## Order of work

Taught in this order, which is not the order they are numbered in. The
write-up is in the book's order regardless.

1. **5.7** --- $x^n-p$ is irreducible in $\mathbb{Q}[x]$ for $p$ prime.
   Eisenstein's criterion applied directly, then Gauss' lemma to get from
   $\mathbb{Z}[x]$ to $\mathbb{Q}[x]$. The warm-up: it fixes the three
   Eisenstein conditions in place before anything is asked of them.
2. **5.6** --- Eisenstein read backwards: $p\mid f_i$ for $1\le i\le n$,
   $p\nmid f_0$, $p^2\nmid f_n$. Same theorem applied to the reversed
   polynomial $x^n f(1/x)$.
3. **5.8** --- $[A:\mathbb{Q}]=\infty$, where $A$ is the field of real
   algebraic numbers. Needs 5.7 in hand: it supplies an element of degree $n$
   over $\mathbb{Q}$ for every $n$.
4. **5.10** --- $x^5-4x+2$ and $x^4-4x+2$ are irreducible over
   $\mathbb{Q}(i)$. Both are Eisenstein at $2$ over $\mathbb{Z}$, so the work
   is the tower argument: $[\mathbb{Q}(i):\mathbb{Q}]=2$ rules out a root or a
   factorization of the wrong degree.
5. **5.4** --- $f-yg$ is irreducible in $K(y)[x]$ when $f,g$ are relatively
   prime in $K[x]$. Last, and the hardest: it reads $K(y)[x]$ through
   $K[y][x]$, uses Gauss' lemma over the integral domain $K[y]$, and turns on
   $f-yg$ being degree $1$ in $y$.

## Write-up

One file: `chapters/ch05-tests-for-irreducibility/homework/ch05-homework.tex`.
`board hw use ch05` pins a sitting to it.

The file currently holds a single placeholder problem labelled `05.1` with an
empty solution region. That placeholder is wrong for this direction and is
replaced by the five assigned problems, labelled `05.4`, `05.6`, `05.7`,
`05.8`, `05.10`, in that order.

A statement is transcribed and a solution region filled in the same turn the
answer is agreed --- not at the end of the sitting. The student's own argument
goes in, in their steps and their order. `board hw file <label>` puts the
handwriting beside it and `board hw build` compiles the set.
`board hw status` reads the `% ===== SOLUTION <label> =====` markers: one
problem environment per label, each opener matched by its closer, or the
report is wrong.

## What is closed

Chapter 4 is finished and is not this chapter's business. The field-extensions
worksheet under `homework/worksheet-field-extensions/` is a separate set and is
not in scope here.
