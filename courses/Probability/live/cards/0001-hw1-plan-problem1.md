---
kind: question
title: Homework 1 — the plan, and Problem 1
---

## What the sheet assigns

Homework I, due 2 September. The sheet chose these, not me, so all of them get done, in this order:

1. **Problem 1** (the professor's own): prove $P(E\cup F)=P(E)+P(F)-P(EF)$ from the axioms.
2. **Ross ch.1, #8** — Bonferroni's inequality.
3. **Ross ch.1, #10** — Boole's inequality.
4. **Ross ch.1, #12.**
5. **Ross ch.1, #39.**
6. **Ross ch.1, #41.**

The sheet also lists ch.1 #4, 5, 6, 7, 17 as *practice, not to be handed in*. We can come back to any of them if you want the drill; they are not part of the six above.

Starting with Problem 1, because #8 and #10 are both built on top of it.

---

## The only equality the axioms give you

The three axioms are all you are allowed to use here:

$$\textbf{(1)}\ \ 0\le P(E)\le 1 \qquad \textbf{(2)}\ \ P(S)=1 \qquad \textbf{(3)}\ \ P\!\left(\bigcup_{n} E_n\right)=\sum_{n} P(E_n)\ \text{ for mutually exclusive } E_n$$

Look at what that list actually contains. Axiom 1 is an inequality. Axiom 2 is one specific number. **Axiom 3 is the only rule in the whole system that turns a probability of a union into a sum** — and it is useless unless the pieces are *mutually exclusive* (disjoint, $E_iE_j=\varnothing$).

So every proof in this chapter is the same manoeuvre: **rewrite the set you care about as a disjoint union of pieces**, then let axiom 3 turn it into addition. Nothing else is available. If you catch yourself writing $P(E\cup F)=P(E)+P(F)$ for overlapping $E$ and $F$, you have used axiom 3 without earning it.

Notation, Ross's: $EF$ means $E\cap F$, and $E^c$ is the complement of $E$.

---

## Watch the manoeuvre once: $P(E^c)=1-P(E)$

Not the problem you have to do — a smaller one, same technique.

The set I care about is $S$. Split it: every outcome is either in $E$ or not in $E$, and never both. So

$$S=E\cup E^c,\qquad EE^c=\varnothing .$$

Those two pieces are disjoint, so axiom 3 applies (with just two sets):

$$P(S)=P(E)+P(E^c).$$

Axiom 2 says the left side is $1$. Rearrange: $P(E^c)=1-P(E)$. Done — one disjoint split, one application of axiom 3, one substitution.

Notice what carried it: I did not decompose $E$, I decomposed the *big* set into a piece I wanted and a leftover. Your problem needs that idea twice, on two different big sets.

---

## Your move — Problem 1

> Let $E$ and $F$ be events. Using the axioms of probability, prove that
> $$P(E\cup F)=P(E)+P(F)-P(EF).$$

Write the proof on the slate. Every time you split a set, say in words why the pieces are disjoint — that is the step being graded, not the algebra at the end.
