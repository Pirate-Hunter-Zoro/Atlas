---
kind: question
title: Prime ideals are primality with the element thrown away. But 3.25 wants *maximal*, and those are not the same word.
---

**Short answer: because "prime" is the property that makes factorization
unique, and the ideal version of it survives in rings where the element version
has nothing to stand on.**

You already proved the bridge. Your **exercise 3.14** says: a non-zero $c \in R$
is a prime *element* if and only if $(c)$ is a prime *ideal*. So for principal
ideals, "prime ideal" says nothing new — it is $p \mid ab \Rightarrow p \mid a$
or $p \mid b$, rewritten as $ab \in (p) \Rightarrow a \in (p)$ or $b \in (p)$.

The payoff is that the rewritten version no longer mentions $p$. In a ring where
ideals are *not* all principal — and $\mathbb{Z} + i\sqrt{5}\,\mathbb{Z}$ from
your 3.12 is exactly one, where $2 + i\sqrt{5}$ is irreducible but not prime —
there is no element to carry the property, and the ideal carries it instead.
That is the whole reason Chapter 3 keeps translating element facts into ideal
facts.

Second payoff, and the one you will meet again: quotients.

| ideal $J \subseteq R$ | what $R/J$ is |
|---|---|
| $J$ prime | an integral domain (your **3.11**, with $J = (a)$) |
| $J$ maximal proper | a field |

Two different words, two different quotients. Every maximal proper ideal is
prime; the converse fails — $(0) \subset \mathbb{Z}$ is prime (a product of
non-zero integers is non-zero) and very much not maximal. Proving one such
failure is the second half of **3.26**, the last exercise on the sheet.

Which is the thing to be careful about right now: **3.25 says nothing about
prime ideals.** It wants a maximal proper ideal, and the theorem that hands you
one is Theorem 3.14 of the text — not your exercise 3.14. Same number, unrelated
statements.

---

## Exercise 3.25 (what remains)

Let $R$ be a ring. Show that an element of $R$ is **invertible if and only if it
is contained in no maximal proper ideal of $R$**.

$\Rightarrow$ is closed (your card 0143). What is left, by contraposition:

**Suppose $u \in R$ is not invertible. Produce a maximal proper ideal of $R$
that contains $u$.**

What you have on the page already, and it is right (card 0144):

- $I = (u) = \{ux : x \in R\}$ is an ideal.
- $I$ is **proper**: $1 \in I$ would give $ux = 1$, making $u$ invertible.
- $u \in I$, by taking $x = 1$.

And what you should *not* try: $I$ itself is usually **not** maximal — $(4)
\subset (2) \subset \mathbb{Z}$.

### Everything the statement uses

- $R$: a commutative ring with identity $1$.
- *Invertible* ($u$ is a **unit**): there is $v \in R$ with $uv = 1$.
- *Ideal* $I \subseteq R$: closed under addition, and **absorbing** — $a \in I$, $r \in R$ $\Rightarrow$ $ra \in I$.
- *Proper*: $I \neq R$.
- *Maximal proper ideal* $M$: proper, and no ideal sits strictly between $M$ and $R$.
- *Principal ideal* $(u) = \{ux : x \in R\}$.
- **Prime ideal** (not needed here, for contrast only): proper, and $ab \in J \Rightarrow a \in J$ or $b \in J$.
- **Your card 0112:** $(c) = R$ if and only if $c$ is a unit.
- **Theorem 3.14 of the text** (Zorn's lemma): *every proper ideal of $R$ is contained in some maximal proper ideal of $R$.* It gives you the ideal. You do not build it.

---

**Your move — one thing only.** Apply Theorem 3.14 to $I$ and call what it gives
you $M$. You now want $u \in M$, and you are not going to prove that by
computing anything: it follows from two facts you already have, put side by
side.

**Name those two facts.** One is on your page from card 0144; the other is the
part of Theorem 3.14's conclusion you have not used yet. Just the two, in
words — no proof.
