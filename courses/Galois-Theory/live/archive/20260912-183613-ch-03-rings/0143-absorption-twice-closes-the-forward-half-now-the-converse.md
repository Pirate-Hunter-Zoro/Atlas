---
kind: correct
title: Absorption twice, and $I \subseteq R$ for free. Forward half closed — now the converse.
---

Both inclusions land. $xu \in I$ by absorption, then $(xu)u^{-1} = x \in I$ by
absorption again, so $R \subseteq I$; and $I \subseteq R$ because an ideal *of*
$R$ is a subset of $R$. Hence $I = R$.

And your parenthetical is the right observation, not a dodge: maximality is
never used. A maximal proper ideal is *proper*, so $u$ lying in one would force
that proper ideal to equal $R$. The forward direction is closed.

(Your two inclusion labels are swapped — the block headed $\subseteq$ is the
proof of $R \subseteq I$. Pen, not mathematics. I will set it straight in the
write-up.)

---

## Exercise 3.25 (the half that remains)

Let $R$ be a ring. Show that an element of $R$ is **invertible if and only if it
is contained in no maximal proper ideal of $R$**.

You have proved $\Rightarrow$. What is left is $\Leftarrow$: **if $u$ lies in no
maximal proper ideal of $R$, then $u$ is invertible.**

### Everything the statement uses

- $R$: a commutative ring with identity $1$.
- *Invertible* ($u$ is a **unit**): there is $v \in R$ with $uv = 1$.
- *Ideal* $I \subseteq R$: closed under addition, and **absorbing** — if $a \in I$ and $r \in R$ then $ra \in I$.
- *Proper* ideal: $I \neq R$.
- *Maximal proper ideal* $M$: $M$ is proper, and no ideal sits strictly between it and $R$.
- *Principal ideal* $(u) = \{ru : r \in R\}$, the multiples of $u$. It is an ideal, and $u \in (u)$ because $u = 1 \cdot u$.
- **Your card 0112:** $(c) = R$ if and only if $c$ is a unit.
- **Theorem 3.14** (Garling, by Zorn's lemma): *every proper ideal of $R$ is contained in some maximal proper ideal of $R$.* This is the direction that needs it.

---

**Your move.** Prove the $\Leftarrow$ direction. It is cleaner by
contraposition, so this is what I am asking for:

**Suppose $u$ is not invertible. Produce a maximal proper ideal of $R$ that
contains $u$.**

Three moves, and you already own two of them: build an ideal out of $u$, say why
it is proper, then hand it to Theorem 3.14. The last step is the one people
forget — the theorem gives you a maximal ideal containing *that ideal*, and you
still have to say why it therefore contains $u$.
