---
kind: question
title: PID — every ideal is the multiples of *one* element. Nothing on your page is wrong.
---

**P.I.D. = principal ideal domain.** Two words, one condition.

*Principal ideal:* pick one element $c \in R$. The set of all its multiples,
$(c) = \{rc : r \in R\}$, is an ideal. An ideal built that way — out of a single
element — is called **principal**.

*Principal ideal domain:* an integral domain in which **every** ideal is
principal. Not "there exists a principal ideal" — every ideal $I$, however it
was handed to you, turns out to be $(c)$ for some one element $c$.

$\mathbb{Z}$ is the model. Hand me any ideal of $\mathbb{Z}$ and it is the
multiples of a single integer: $\{\ldots,-6,-3,0,3,6,\ldots\} = (3)$, and
$\{0\} = (0)$. There is no ideal of $\mathbb{Z}$ that needs two generators.
That is what you are claiming about $R$.

**So what you are trying to prove.** Exercise 3.17 had three parts. $R$ is a
subring of $\mathbb{Q}$ — done, card 0125. The units of $R$ are the $n/q$ with
$p \nmid n$ — done, card 0129. This is part three:

> Take an ideal $I$ of $R$. You know nothing about $I$ except that it is an
> ideal. Produce a single element $c \in R$ and show $I = (c)$.

And you have already built the tool for it. Your lemma says every nonzero
element of $R$ is a unit times a power of $p$. So the only elements of $R$ that
differ from each other in any way an ideal can see are $p^{0}, p^{1}, p^{2},
\ldots$ — the units are invisible to an ideal, because an ideal swallows
multiplication by them. The generator $c$ is going to be $p^{m}$ for the
**smallest** $m$ with $p^{m} \in I$. That is the whole plan, and the step below
is the reason the units are invisible.

Nothing on the page needs fixing. The lemma is closed and the $\{0\}$ case is
disposed of.

---

**Exercise 3.17, part three.** Let $p$ be a fixed prime and

$$R = \left\{ x \in \mathbb{Q} : x = r/s \text{ for some } r,s \in \mathbb{Z},\ s \neq 0,\ p \nmid s \right\}.$$

**Show that $R$ is a principal ideal domain.**

**Recall.**

- *Integral domain:* commutative ring with $1$, no zero divisors. $R \subseteq \mathbb{Q}$, so that half is free.
- *Unit:* $u \in R$ is a unit if $uv = 1$ for some $v \in R$; then $v = u^{-1} \in R$.
- *Units of $R$ (yours, card 0129):* $n/q \in R$ is a unit iff $p \nmid n$.
- *Ideal $I$ of $R$:* nonempty, closed under addition, and $rx \in I$ for **every** $r \in R$ and every $x \in I$.
- *Principal ideal:* $(c) = \{rc : r \in R\}$. *PID:* every ideal is some $(c)$.
- *Your lemma, proved:* every nonzero $x \in R$ is $u\,p^{k}$ for some unit $u$ of $R$ and some integer $k \geq 0$.
- *Already disposed of:* if $I = \{0\}$ then $I = (0)$, principal. So assume $I$ has a nonzero element.

---

**Your move.** One line. Fix $p = 3$. Let $I$ be some ideal of $R$ — you know
nothing about it except that it is an ideal and that

$$\tfrac{5}{2} \cdot 3^{3} \in I .$$

($\tfrac{5}{2} \in R$ and $3 \nmid 5$, so $\tfrac{5}{2}$ is a unit of $R$.)

Show that $3^{3} \in I$.
