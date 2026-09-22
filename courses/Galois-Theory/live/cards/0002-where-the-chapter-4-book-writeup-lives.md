---
kind: lesson
title: where-the-chapter-4-book-writeup-lives
---
They are written up, just not in the file the board has open. The book
exercises live at `chapters/ch04-field-extensions/homework/ch04-homework.tex`,
and the compiled PDF sits beside it at
`chapters/ch04-field-extensions/build/ch04-homework.pdf`, 5 pages, built
2026-09-19. It holds Problems 04.1 through 04.11, each with its own solution
region. Ten are filled. 04.2 is empty, as you asked.

Two sets are open this chapter, and that is why one looked missing. The
worksheet is at `homework/worksheet-field-extensions/`, and this sitting is
bound to that file, so the board's own status line reports the worksheet's 8 of
8 and never mentions the book.

**Problem 1(c), still open.** Let $F$ be a field, let $f \in F[x]$ be
non-constant of degree $n$, and set $A = F[x]/(f)$. Conclude that $A$ is a
field if and only if $f$ is irreducible.

What it uses:

- irreducible --- $f$ is non-constant and is not $gh$ with $g,h \in F[x]$ both of degree $\geq 1$.
- $A = F[x]/(f)$ --- classes $\overline{g} = g + (f)$, with $\overline{g} = \overline{0}$ exactly when $f \mid g$.
- field --- commutative ring, $\overline{1} \neq \overline{0}$, every non-zero element invertible.
- integral domain --- commutative ring, $\overline{1} \neq \overline{0}$, no zero divisors.
- zero divisor --- a non-zero element whose product with some non-zero element is $\overline{0}$.
- 1(a), yours --- $\dim_F A = n$, so $\overline{1} \neq \overline{0}$.
- 1(b), yours --- if $A$ is an integral domain then $A$ is a field.
- degrees add --- $\deg(gh) = \deg g + \deg h$ for non-zero $g,h$ over a field.
- every field is an integral domain.

**Your move.** Not 1(c) itself yet --- one concrete case of the direction that
fails. Take $F = \mathbb{Q}$ and $f = x^{2} - 1$, which factors as $(x-1)(x+1)$
and so is not irreducible, and let $A = \mathbb{Q}[x]/(x^{2}-1)$. Name two
classes in $A$, neither of them $\overline{0}$, whose product is $\overline{0}$,
and say in one line why their existence stops $A$ being a field.
