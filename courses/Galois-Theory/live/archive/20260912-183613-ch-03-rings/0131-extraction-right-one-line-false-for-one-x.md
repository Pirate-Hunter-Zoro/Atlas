---
kind: wrong
title: The extraction is right, and you said why $u$ is a unit. One line is false for one $x$.
---

You wrote: if $r/s$ is a unit, done, with $k = 0$; else $p \mid r$, so there are
$k \geq 1$ and $n \in \mathbb{Z}$ with $np^{k} = r$ and $p \nmid n$, hence

$$\frac{r}{s} = \frac{n}{s}\cdot p^{k}, \qquad \frac{n}{s} \text{ a unit.}$$

That is the right proof. The split into unit / non-unit is the right split, $u$
is the right $u$, $k$ is the right $k$, and you gave the reason $n/s$ is a unit
— $p \nmid n$ — instead of asserting it. That last part is the one people drop.

**But your third line is false for one element of $R$.** Take $x = 0$. It is in
$R$ (write it as $0/1$). It is not a unit, so your proof sends it down the
*else* branch, and $p \mid 0$ is true, so it stays there. Then the line

$$\exists\, k \geq 1,\ n \in \mathbb{Z} \ \text{ s.t. } \ np^{k} = r,\ p \nmid n$$

asserts something that does not exist for $r = 0$: every $n$ with $n p^{k} = 0$
is $n = 0$, and $p \mid 0$. Your first line has a word missing.

---

**Exercise 3.17, part three.** With $p$ a fixed prime and

$$R = \left\{ x \in \mathbb{Q} : x = r/s \text{ for some } r,s \in \mathbb{Z},\ s \neq 0,\ p \nmid s \right\},$$

**show that $R$ is a principal ideal domain.**

**Recall.**

- *Integral domain:* commutative ring with $1$, no zero divisors. $R \subseteq \mathbb{Q}$, so that half is free.
- *Ideal $I$ of $R$:* nonempty, closed under addition, and $rx \in I$ for every $r \in R$, $x \in I$.
- *Principal ideal:* $(c) = \{rc : r \in R\}$. *PID:* every ideal is some $(c)$.
- *Membership in $R$:* $x \in R$ iff **at least one** representation $r/s$ of $x$ has $p \nmid s$.
- *Units of $R$ (yours):* $n/q \in R$ is a unit iff $p \nmid n$.
- *$a \mid b$:* there is an integer $k$ with $b = ak$.

---

**Your move.** One line, nothing new to prove.

State the lemma the way your own proof actually proves it: fill the blank in

> *for every $x \in R$ with \_\_\_\_\_, there are a unit $u$ of $R$ and an
> integer $k \geq 0$ with $x = u\,p^{k}$.*

Then say, in one sentence, why the excluded $x$ has to be excluded rather than
handled — what would $u$ and $k$ have to be for it?
