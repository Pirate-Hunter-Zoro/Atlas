---
kind: wrong
title: The multiplier $2/5$ is right, and so is your reason for it. Line one assumes what you are proving.
---

**The bottom of the page is the proof.** $3^{3} = \tfrac{2}{5}\cdot\left(\tfrac{5}{2}\cdot 3^{3}\right)$,
and $\tfrac{2}{5} \in R$ since $3 \nmid 5$. And your parenthetical is the real
content of the step: *"which is why $\tfrac{5}{2}$ had to be a unit."* Exactly —
being a unit is what puts $\left(\tfrac{5}{2}\right)^{-1} = \tfrac{2}{5}$ inside
$R$, and only elements of $R$ are licensed as multipliers.

**Line one is the problem.** You wrote

$$\exists\, x \in R \ \text{ s.t. } \ \{rx : r \in R\} = I .$$

That sentence says $I$ is principal. That is exercise 3.17 part three — the
entire thing you are trying to prove, about an ideal you know nothing about.
Assume it and there is nothing left to do. This is the same shape as card 0115:
the line you reached for *was* the theorem.

You also do not need it. Look at what $x$ actually did for you: nothing except
sit inside a product equal to $\tfrac{5}{2}\cdot 3^{3}$. But you were handed
$\tfrac{5}{2}\cdot 3^{3} \in I$ directly. The generator is a detour through an
assumption you are not allowed to make.

Strike line one and the two lines about $r_{1}$ and $r_{2}$. Keep $\tfrac{2}{5}$.

---

**Exercise 3.17, part three.** Let $p$ be a fixed prime and

$$R = \left\{ x \in \mathbb{Q} : x = r/s \text{ for some } r,s \in \mathbb{Z},\ s \neq 0,\ p \nmid s \right\}.$$

**Show that $R$ is a principal ideal domain.**

**Recall.**

- *Integral domain:* commutative ring with $1$, no zero divisors. $R \subseteq \mathbb{Q}$, so that half is free.
- *Unit:* $u \in R$ is a unit if $uv = 1$ for some $v \in R$; then $v = u^{-1} \in R$.
- *Units of $R$ (yours, card 0129):* $n/q \in R$ is a unit iff $p \nmid n$.
- *Ideal $I$ of $R$:* nonempty, closed under addition, and $rx \in I$ for **every** $r \in R$ and every $x \in I$. That last property is called absorption, and it is the only tool this step needs.
- *Principal ideal:* $(c) = \{rc : r \in R\}$. *PID:* every ideal is some $(c)$. **This is the conclusion, not an available hypothesis.**
- *Your lemma, proved:* every nonzero $x \in R$ is $u\,p^{k}$ for some unit $u$ of $R$ and some integer $k \geq 0$.
- *Already disposed of:* if $I = \{0\}$ then $I = (0)$, principal. So assume $I$ has a nonzero element.
- *The plan:* the generator will be $p^{m}$ for the smallest $m$ with $p^{m} \in I$. This step is why the units are invisible to $I$.

---

**Your move.** One line, and no $x$ in it. Fix $p = 3$. Let $I$ be an ideal of
$R$ — you know nothing whatever about $I$ except that it is an ideal and that

$$\tfrac{5}{2} \cdot 3^{3} \in I .$$

Name the element $r$ of $R$ you multiply by, and name which of the three ideal
properties above you are invoking, to conclude $3^{3} \in I$.
