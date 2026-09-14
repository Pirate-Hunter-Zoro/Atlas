---
kind: correct
title: $u^{-1}x = p^{k}$, and you said why $u^{-1}$ exists. The lemma is general now.
---

**That is the line.** $x = u\,p^{k} \in I$, $u$ is a unit so $u^{-1} \in R$,
and $u^{-1}x = u^{-1}u\,p^{k} = p^{k} \in I$. The multiplier is in $R$ for a
stated reason and nothing about $I$ was assumed beyond the ideal axioms. Same
argument as $\tfrac{2}{5}$, no numbers left in it.

("Since $I$ is an ideal" is again the property called **absorption** — I will
write that word into the file. Not a correction, just the name.)

So: **every nonzero element of $I$ produces a bare power of $p$ inside $I$.**
That is exactly what makes the following definition legal. Put

$$S = \{\, k \geq 0 : p^{k} \in I \,\}.$$

Your line says $S \neq \emptyset$ whenever $I$ has a nonzero element. A
nonempty set of non-negative integers has a least element — that is
well-ordering, and it is the only thing you need it for. Let $m = \min S$, so
$p^{m} \in I$ and no smaller power of $p$ is in $I$.

The claim is $I = (p^{m})$. Two inclusions. One of them is a single line.

---

**Exercise 3.17, part three.** Let $p$ be a fixed prime and

$$R = \left\{ x \in \mathbb{Q} : x = r/s \text{ for some } r,s \in \mathbb{Z},\ s \neq 0,\ p \nmid s \right\}.$$

**Show that $R$ is a principal ideal domain.**

**Recall.**

- *Integral domain:* commutative ring with $1$, no zero divisors. $R \subseteq \mathbb{Q}$, so that half is free.
- *Unit:* $u \in R$ is a unit if $uv = 1$ for some $v \in R$; then $v = u^{-1}$ lies in $R$.
- *Units of $R$ (yours, card 0129):* $n/q \in R$ is a unit iff $p \nmid n$.
- *Ideal $I$ of $R$:* nonempty; closed under addition; and **absorption** — $rx \in I$ for every $r \in R$ and every $x \in I$.
- *Principal ideal:* $(c) = \{rc : r \in R\}$, the multiples of the single element $c$. *PID:* every ideal is $(c)$ for some one $c$. **Still the conclusion, never a hypothesis.**
- *Your lemma (cards 0130–0133):* every nonzero $x \in R$ is $x = u\,p^{k}$ with $u$ a unit of $R$ and $k \geq 0$.
- *Just proved (this card):* if $x = u\,p^{k}$ lies in $I$ then $p^{k} \in I$.
- *Already disposed of:* $I = \{0\}$ is $(0)$, principal. So $I$ has a nonzero element.
- *Set up above:* $m$ is the smallest $k \geq 0$ with $p^{k} \in I$, and $p^{m} \in I$.

---

**Your move.** The easy inclusion.

**Show that $(p^{m}) \subseteq I$.** Take a typical element of $(p^{m})$, say
what form it has, and say which one of the three ideal properties puts it in
$I$. One line — and name the property, not "$I$ is an ideal".

Then the other inclusion, which is where $m$ being *smallest* finally earns
its keep. That one is the last step of 3.17.
