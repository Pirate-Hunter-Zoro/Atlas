---
kind: note
title: You are stuck because that case cannot happen
---

You are stuck on a case that is empty. That is worth knowing before you spend any more time on it.

Everything else is settled. The inequality is turned the right way now, the induction is set up correctly, the base case is right, and your **first** bullet — $e \notin E_n$, so $e \in \bigcup_1^{n-1}E_i \subseteq \bigcup_1^{n-1}F_i \subseteq \bigcup_1^{n}F_i$ — is a complete and correct case. Keep it exactly as written.

The break is one line above it, where you split into cases. You are working under the standing assumption

$$e \notin F_n, \qquad F_n = E_n E_1^{c}E_2^{c}\cdots E_{n-1}^{c}.$$

Being *in* $F_n$ means two things at once: in $E_n$, **and** outside every one of $E_1,\dots,E_{n-1}$. So being *outside* $F_n$ means at least one of those two things fails — and "outside every earlier $E_i$" fails by there being **one** earlier $E_i$ you are inside, not by being outside all of them.

Now read your second bullet back:

> If $e \in E_n$, and $e \notin E_i\ \forall i<n$

That is $e \in E_n$ and $e$ outside every earlier $E_i$. Which is the definition of $F_n$. You assumed $e \notin F_n$ and then asked what happens when $e \in F_n$. Nothing happens; there is no such $e$.

---

**Your move.** Negate $e \notin F_n$ properly and write down the two cases it actually splits into. One of them is the bullet you already finished. State the other one correctly and see how far it is from being done.

One line to state it. You may find the finish is a line you have already written.
