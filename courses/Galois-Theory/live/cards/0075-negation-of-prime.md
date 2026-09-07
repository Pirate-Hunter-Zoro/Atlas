---
kind: wrong
title: Right strategy. The slash on $bc$ is upside down.
---

The strategy is right — contrapositive, and the machine you build is the
$\mathbb{Z}/(6)$ rung in general form. But look at what you assumed:

> $\exists\, b, c \in R$ s.t. $a \nmid bc$, but $a \nmid b$ and $a \nmid c$.

All three slashed. Then three lines later:

> $(b+(a))(c+(a)) = bc + (a) = (a)$ since $a \nmid bc$.

That step is false as written. $bc + (a)$ is the zero class exactly when
$a \mid bc$ — rung one — so with $a \nmid bc$ your product is *not* zero and
nothing follows. The two lines cannot both hold, and one of them has the slash
in the wrong place.

Which one is fixed by the definition, not by choice: go back to what "$a$ is
prime" asserts and negate it carefully. It is an implication, and the negation
of an implication does not slash both sides.

(Also, your last word: $R/(a)$ having zero divisors makes it not an *integral
domain*. Whether it is a field is a different question and not one 3.11 asks.)

---

**Your move.** One line, no proof. Write out precisely:

> $a$ is not prime $\iff$ there exist $b, c \in R$ such that \_\_\_\_.

Fill the blank with the three conditions on $b$ and $c$, slashes where they
belong.
