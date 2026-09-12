---
kind: note
title: Skipped, so 3.8 stands as granted. Two left — here is 3.25, and one direction of it.
---

3.8 is off the board. Two exercises remain on the sheet: **3.25** and **3.26**.
3.25 is first, and its easy direction is a two-line application of something you
already proved in 3.14.

---

## Exercise 3.25

Let $R$ be a ring. Show that an element of $R$ is **invertible if and only if it
is contained in no maximal proper ideal of $R$**.

### Everything the statement uses

- $R$: a commutative ring with identity $1$.
- *Invertible* ($u$ is a **unit**): there is $v \in R$ with $uv = 1$.
- *Ideal* $I \subseteq R$: closed under addition, and **absorbing** — if $a \in I$ and $r \in R$ then $ra \in I$. (Card 0136: absorption.)
- *Proper* ideal: $I \neq R$.
- *Maximal proper ideal* $M$: $M$ is proper, and no ideal sits strictly between it and $R$ — if $I$ is an ideal with $M \subseteq I \subseteq R$, then $I = M$ or $I = R$.
- *Principal ideal* $(a) = \{ra : r \in R\}$, the multiples of $a$. It is the smallest ideal containing $a$.
- **Your card 0112:** $(c) = R$ if and only if $c$ is a unit.
- **Your card 0133:** every ideal contains $0$. So $I = R$ exactly when $1 \in I$.
- **Theorem 3.14** (Garling, proved for you by Zorn's lemma): *every proper ideal of $R$ is contained in some maximal proper ideal of $R$.* You will need this for the other direction, not this one.

---

**Your move.** One direction only, and it is the forward one.

**Let $u \in R$ be invertible, and let $I$ be any ideal of $R$ with $u \in I$.
Prove $I = R$. Then conclude that $u$ lies in no maximal proper ideal.**

Note what the claim you are proving is *not*: it is not about maximal ideals
specifically. A unit escapes **every** proper ideal, and maximal ones are proper.
The tool is absorption — $u$ is in $I$, and you have something you are allowed to
multiply it by.
