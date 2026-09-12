---
kind: wrong
title: $(u)$ is proper and contains $u$ — both right. You are stuck because you are trying to prove something false.
---

Your first two moves are the proof. $I = \{ux : x \in R\}$ is proper — $1 \notin
I$, because $1 = ux$ would make $u$ invertible, which is exactly what you
assumed away (that is your card 0112). And $u \in I$ by $x = 1$. Both correct.

Then you wrote "to show it is maximal" and got stuck. You got stuck because
$(u)$ **is usually not maximal**, so no argument was going to work.

In $\mathbb{Z}$, take $u = 4$. It is not invertible, and $(4)$ is proper. But

$$(4) \subset (2) \subset \mathbb{Z},$$

so there is an ideal strictly between $(4)$ and the whole ring: $(4)$ is not
maximal. Your $I' $ exists, and $R \subseteq I'$ is false for it.

Nothing is lost. You were never asked to *build* a maximal ideal. You were asked
to produce one, and there is a theorem whose entire job is handing you one.

---

## Exercise 3.25 (what remains)

Let $R$ be a ring. Show that an element of $R$ is **invertible if and only if it
is contained in no maximal proper ideal of $R$**.

$\Rightarrow$ is closed (card 0143). What is left, by contraposition:

**Suppose $u$ is not invertible. Produce a maximal proper ideal of $R$ that
contains $u$.**

### Everything the statement uses

- $R$: a commutative ring with identity $1$.
- *Invertible* ($u$ is a **unit**): there is $v \in R$ with $uv = 1$.
- *Ideal* $I \subseteq R$: closed under addition, and **absorbing** — if $a \in I$ and $r \in R$ then $ra \in I$.
- *Proper* ideal: $I \neq R$.
- *Maximal proper ideal* $M$: $M$ is proper, and no ideal sits strictly between $M$ and $R$.
- *Principal ideal* $(u) = \{ux : x \in R\}$ — your $I$. It is an ideal, and $u = 1 \cdot u \in (u)$.
- **Your card 0112:** $(c) = R$ if and only if $c$ is a unit.
- **Theorem 3.14** (Garling, via Zorn's lemma): *every proper ideal of $R$ is contained in some maximal proper ideal of $R$.*

---

**Your move.** Keep your first two lines exactly as they are. Delete everything
from "to show it is maximal" onward and replace it with two sentences:

1. Apply Theorem 3.14 to $I$. Say what it gives you and name it.
2. Say why that object contains $u$.

Step 2 is the one people skip. The theorem hands you a maximal ideal containing
$I$ — it says nothing about $u$ directly, and you have to close that gap
yourself.
