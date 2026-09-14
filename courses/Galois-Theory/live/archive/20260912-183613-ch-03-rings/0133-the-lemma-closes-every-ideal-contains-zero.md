---
kind: correct
title: The lemma closes. But *every* ideal contains $0$.
---

$u p^{k} = 0 \Rightarrow p^{k} = u^{-1} \cdot 0 = 0$, impossible. Correct, and you
used the sharper fact — $u$ is a unit, so $u^{-1}$ exists in $R$ and you can just
multiply. So $0$ is not $u p^{k}$ for any unit $u$, the margin patch goes, and the
blank is **$x \neq 0$**:

> For every **nonzero** $x \in R$ there are a unit $u$ of $R$ and an integer
> $k \geq 0$ with $x = u\,p^{k}$.

That lemma is done. Cross the "pick $u = 0$" note off the page.

**Now the line underneath it.** You wrote:

> But an ideal containing $0$ is just $\{0\}$.

$R$ is an ideal of $R$, and $0 \in R$. So that is false — every ideal contains
$0$, because an ideal is closed under $r x$ and $0 \cdot x = 0$. What is true is
the other way round: $\{0\}$ is the ideal that contains **nothing but** $0$, and
it is principal, since $\{0\} = (0)$. That case is disposed of. Everything from
here is about an ideal with a nonzero element in it, and *that* is where the
lemma gets used.

---

**Exercise 3.17, part three.** With $p$ a fixed prime and

$$R = \left\{ x \in \mathbb{Q} : x = r/s \text{ for some } r,s \in \mathbb{Z},\ s \neq 0,\ p \nmid s \right\},$$

**show that $R$ is a principal ideal domain.**

**Recall.**

- *Integral domain:* commutative ring with $1$, no zero divisors. $R \subseteq \mathbb{Q}$, so that half is free.
- *Unit:* $u \in R$ is a unit if $uv = 1$ for some $v \in R$; then $v = u^{-1} \in R$.
- *Units of $R$ (yours):* $n/q \in R$ is a unit iff $p \nmid n$.
- *Ideal $I$ of $R$:* nonempty, closed under addition, and $rx \in I$ for **every** $r \in R$ and every $x \in I$.
- *Principal ideal:* $(c) = \{rc : r \in R\}$. *PID:* every ideal is some $(c)$.
- *Your lemma, now proved:* every nonzero $x \in R$ is $u\,p^{k}$ for some unit $u$ of $R$ and some integer $k \geq 0$.

---

**Your move.** One line. Fix $p = 3$, and let $I$ be some ideal of $R$ — you know
nothing about it except that it is an ideal and that

$$\tfrac{5}{2} \cdot 3^{3} \in I .$$

($\tfrac{5}{2} \in R$ and $3 \nmid 5$, so $\tfrac{5}{2}$ is a unit.)

Show that $3^{3} \in I$.
