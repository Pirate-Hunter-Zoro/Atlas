---
kind: correct
title: $\tfrac{2}{5}$ and the conclusion both land. The property is called absorption.
---

**That is the step.** $\tfrac{2}{5} \in R$ because $3 \nmid 5$, and
$\tfrac{2}{5} \cdot \tfrac{5}{2} \cdot 3^{3} = 3^{3} \in I$. No $x$, no
generator, nothing assumed about $I$ beyond its being an ideal. The circular
line is gone and the multiplier survived intact.

One word for the file. "Since $I$ is an ideal" is the right reason, but the
ideal has three properties and only one of them did any work here:
**absorption**, $rx \in I$ for every $r \in R$ and every $x \in I$. You took
$r = \tfrac{2}{5}$ and $x = \tfrac{5}{2}\cdot 3^{3}$. Nonemptiness and closure
under addition were never touched. Say *absorption* when you write it up — it
is the name of the only thing you used.

And notice what the step really did: it deleted the unit $\tfrac{5}{2}$ from
the element. That is the whole reason the units were worth computing. Every
element of $I$ can be stripped down to a bare power of $p$ that is still in
$I$. That sentence, stated for all of $I$ at once, is the next line.

---

**Exercise 3.17, part three.** Let $p$ be a fixed prime and

$$R = \left\{ x \in \mathbb{Q} : x = r/s \text{ for some } r,s \in \mathbb{Z},\ s \neq 0,\ p \nmid s \right\}.$$

**Show that $R$ is a principal ideal domain.**

**Recall.**

- *Integral domain:* commutative ring with $1$, no zero divisors. $R \subseteq \mathbb{Q}$, so that half is free.
- *Unit:* $u \in R$ is a unit if $uv = 1$ for some $v \in R$; then $v = u^{-1}$ lies in $R$.
- *Units of $R$ (yours, card 0129):* $n/q \in R$ is a unit iff $p \nmid n$.
- *Ideal $I$ of $R$:* nonempty; closed under addition; and **absorption** — $rx \in I$ for every $r \in R$ and every $x \in I$.
- *Principal ideal:* $(c) = \{rc : r \in R\}$. *PID:* every ideal is $(c)$ for some single $c$. **Still the conclusion, never a hypothesis.**
- *Your lemma, proved (cards 0130–0133):* every nonzero $x \in R$ can be written $x = u\,p^{k}$ with $u$ a unit of $R$ and $k \geq 0$ an integer.
- *Already disposed of:* if $I = \{0\}$ then $I = (0)$, principal. So from here $I$ has a nonzero element.
- *Just proved (this card):* for $p = 3$, from $\tfrac{5}{2}\cdot 3^{3} \in I$ absorption gives $3^{3} \in I$.
- *The plan:* the generator is $p^{m}$ for the **smallest** $m$ with $p^{m} \in I$. Before "smallest" means anything, you need to know that at least one such $m$ exists.

---

**Your move.** General $p$ now, and no numbers. Let $I$ be an ideal of $R$ with
some nonzero element $x \in I$. Write $x = u\,p^{k}$ by your lemma.

**Show that $p^{k} \in I$** — one line, the same line you just wrote. Name the
element of $R$ you multiply $x$ by, and say why that element is in $R$ at all.
