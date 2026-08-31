---
kind: correct
title: Boole is done — and the axiom Problem 4 stretches
---

That is a proof. Problem 3 is finished.

The negation is right this time, and the part worth naming is your last bullet: *if the former is true, the latter must still be true*. $e\notin E_n$ together with $e\in\bigcup_1^n E_i$ forces $e\in E_i$ for some $i<n$ — so the first case collapses into the second and you only ever had one case to do. That is the whole content of the step.

I am writing it up now, in your order: the main argument, then the Aside, then the induction.

---

**Problem 4 (Ross 1.12).** $E$ and $F$ are mutually exclusive. Repeat the experiment until one of them occurs. Show the probability that $E$ occurs before $F$ is $P(E)/[P(E)+P(F)]$.

One thing here is new, and it is not the algebra. Every union you have taken all evening has been **finite** — $n$ sets, $n$ terms. Here the experiment can run for any number of trials, so the event "$E$ comes first" is

$$\bigcup_{n=1}^{\infty} \{\text{$E$ occurs on trial $n$, nothing before}\},$$

a union of **infinitely many** disjoint events. Axiom 3 as you have been using it says nothing about that. The axiom is in fact stated for a countable sequence $A_1, A_2, A_3,\dots$ of pairwise disjoint events, and it says $P(\bigcup_{n=1}^{\infty} A_n) = \sum_{n=1}^{\infty} P(A_n)$ — an infinite series, and the finite rule you have been using is the special case where the rest are empty.

---

**Your move — a small one, before the problem.** Flip a fair coin repeatedly. Let $A_n$ be the event that the **first head** appears on flip $n$, so $P(A_n) = (1/2)^n$, and the $A_n$ are disjoint. Compute $P(\text{a head appears eventually})$.

One line.
