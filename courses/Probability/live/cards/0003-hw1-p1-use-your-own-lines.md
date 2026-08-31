---
kind: note
title: You already wrote the answer — it is line 1 and line 2
---

**"How to show?"** — the tool you need is the top of your own page.

Everything down to

$$P(E\cup F) = P(EF) + P(EF^{c}) + P(FE^{c})$$

is right. The three-way carve is a legitimate route — it is not the one I set up, and it works. You applied axiom 3 to a three-piece disjoint union and it paid out.

Now look at what you wrote first:

$$E = EF \cup EF^{c}, \qquad F = EF \cup FE^{c}.$$

Those are disjoint unions too. You have already used axiom 3 once on this page. **Use it on those two lines.** Each one turns into an equation about probabilities, and each of those equations contains exactly one of the two terms sitting under your brace.

That is the whole remaining step. There is nothing else to find, and no new axiom needed — you do not have to *derive* $P(E)+P(F)-2P(EF)$ out of thin air, you have to *read it off* two applications of the axiom you already used.

One thing to be careful about, since you will be marked on it: when you apply axiom 3 to $E = EF \cup EF^{c}$, say why those two pieces are disjoint. A point in both would have to be in $F$ and in $F^{c}$.

---

**Your move.** Finish Problem 1 on the slate. Take your page from the brace onward: apply axiom 3 to your line 1 and your line 2, substitute the two results into your expression for $P(E\cup F)$, and land on $P(E)+P(F)-P(EF)$.
