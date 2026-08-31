---
kind: question
title: The skeleton is right — one line is backwards, and one claim is assumed
---

The shape is right and the ending is right. $P(\bigcup E_i) = P(\bigcup F_i) = \sum P(F_i)$ by axiom 3, then trade up to $\sum P(E_i)$. That is the proof.

**Backwards symbol.** You wrote

$$\text{Since } \forall i,\ F_i \subseteq E_i,\quad P(F_i) \ge P(E_i),$$

and monotonicity says the opposite: $F_i \subseteq E_i$ gives $P(F_i) \le P(E_i)$. The very next clause on your page uses the correct direction, so the pen went the wrong way, not the head. Turn it round.

**The claim you assumed.** This is the real one. You opened with

> each $F_i \subseteq E_i$ and is defined such that $\bigcup_{i=1}^{n} E_i = \bigcup_{i=1}^{n} F_i$

But that equality is not part of the definition of $F_i$ — the definition only says $F_i = E_i E_1^{c}\cdots E_{i-1}^{c}$. The equality is a consequence, and it is the one thing the book's hint tells you to *show*. Your whole first step rests on it.

Half of it is free: $F_i \subseteq E_i$ for each $i$, so $\bigcup F_i \subseteq \bigcup E_i$ immediately. Take that as given.

---

**Your move.** Prove the other inclusion:

$$\bigcup_{i=1}^{n} E_i \ \subseteq\ \bigcup_{i=1}^{n} F_i.$$

Take a point $x$ in the left-hand side. It lies in $E_i$ for at least one $i$ — but the $F_i$ have all the earlier $E$'s cut out of them, so not every such $i$ will do. Choose the right one, then check $x$ is in that $F_i$.

Three or four lines. Everything else on your page stands.
