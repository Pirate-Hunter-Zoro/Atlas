---
kind: wrong
title: Both inclusions are the right proof. "Through well ordering" is the wrong reason for $k_{1} \geq m$.
---

**The shape is finished.** $\subseteq$ is exactly right: $p^{m} \in I$, so
$rp^{m} \in I$ for every $r \in R$. And in $\supseteq$ you did not drop the
side condition this time — $r = u\,p^{k_{1}-m}$ needs $k_{1} \geq m$ to be an
element of $R$ at all, and you stated $k_{1} \geq m$ before you used it. The
final computation $rp^{m} = u\,p^{k_{1}-m}p^{m} = u\,p^{k_{1}} = y$ is correct.

**One line is not earned.** You wrote

> $k_{1} \geq m$ through well ordering.

Well-ordering is what gave you $m$ in the first place — a nonempty set of
non-negative integers has a *least* element. It says nothing whatever about
$k_{1}$. What you want is *minimality* of $m$, and minimality of $m$ only
speaks about members of $S$. So the missing step is the one that puts
$k_{1}$ into $S$, and $S$ has a membership condition you have not checked
for $k_{1}$.

You proved the fact that does it one card ago. Use it.

(Two pen matters, no redo needed. Your restatement reads
$I = \{rx \mid x \in R\}$; the quantified letter is $r$, so
$I = \{rx : r \in R\}$ — I will fix it in the file. And "since $I$ is an
ideal" in the $\subseteq$ half is **absorption**; that word goes into the
write-up.)

---

**Exercise 3.17, part three.** Let $p$ be a fixed prime and

$$R = \left\{ x \in \mathbb{Q} : x = r/s \text{ for some } r,s \in \mathbb{Z},\ s \neq 0,\ p \nmid s \right\}.$$

**Show that $R$ is a principal ideal domain.**

**Recall.**

- *Integral domain:* commutative ring with $1$, no zero divisors. $R \subseteq \mathbb{Q}$, so that half is free.
- *Unit:* $u \in R$ is a unit if $uv = 1$ for some $v \in R$; then $v = u^{-1}$ lies in $R$.
- *Units of $R$ (yours, card 0129):* $n/q \in R$ is a unit iff $p \nmid n$.
- *Ideal $I$ of $R$:* nonempty; closed under addition; and **absorption** — $rx \in I$ for every $r \in R$ and every $x \in I$.
- *Principal ideal:* $(c) = \{rc : r \in R\}$. *PID:* every ideal is $(c)$ for some one $c$.
- *Your lemma A (cards 0130–0133):* every nonzero $x \in R$ is $x = u\,p^{k}$ with $u$ a unit of $R$ and $k \geq 0$.
- *Your lemma B (card 0137):* if $x = u\,p^{k}$ lies in $I$, then $p^{k} \in I$. (Multiply by $u^{-1} \in R$; absorption.)
- *Already disposed of:* $I = \{0\}$ is $(0)$, principal. So $I$ has a nonzero element.
- *Set up:* $S = \{\,k \geq 0 : p^{k} \in I\,\}$, nonempty, and $m = \min S$, so $p^{m} \in I$ and no smaller power of $p$ lies in $I$.
- *Where you are:* $\subseteq$ done. In $\supseteq$: $y \in I$, $y \neq 0$, $y = u\,p^{k_{1}}$, and you need $k_{1} \geq m$.

---

**Your move.** One line, and 3.17 is closed.

**$y = u\,p^{k_{1}} \in I$. Show that $k_{1} \in S$** — that is, show
$p^{k_{1}} \in I$, and say which of your two lemmas does it. Then say in one
clause why $k_{1} \in S$ forces $k_{1} \geq m$.
