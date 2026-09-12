---
kind: question
title: Yes — but that sentence *is* the theorem, so contradiction has nothing to bite on. Divide instead.
---

**Your question:** *"If we can't pull an $(x-a)$ from $f$, then there's no way
$f(a)$ could be $0$?"*

Yes. That sentence is true. It is also, word for word, the contrapositive of the
direction you are trying to prove: *$f(a)=0 \Rightarrow f \in (x-a)$* says
exactly the same thing as *$f \notin (x-a) \Rightarrow f(a) \neq 0$*.

So the "suppose not" stalls for a structural reason, not because you missed a
trick. You assumed $f \notin (x-a)$ and then looked for a contradiction — but
the only thing that assumption contradicts is the conclusion itself, which is
what you are trying to establish. Contradiction gives you nothing to *compute*
with here. There is no equation on the page.

Also right: the $(x-a)^{-1}$ line from your last page is gone. It should be.

**What $\Rightarrow$ actually needs is a construction.** You must produce the
$g$, not argue that one must exist. And there is exactly one tool in this
chapter that manufactures polynomials out of a division: **Theorem 3.7**.

---

**3.15 (first half), in full.** Let $K$ be a field, $a \in K$, $f \in K[x]$.
Prove: if $f(a) = 0$, then $f \in (x-a)$.

What you have available:

- *Theorem 3.7 (Garling, p. 43):* if $f$ and $g$ are non-zero in $K[x]$, there
  exist $q, r \in K[x]$ with $g = qf + r$, and either $r = 0$ or
  $\deg r < \deg f$. It is long division; Garling never names it.
- *$a$ is a root of $f$:* $f(a) = 0$, where $f(a)$ means substituting $a$ for
  $x$ and evaluating in $K$.
- *$(x-a)$:* the ideal $\{h\cdot(x-a) : h \in K[x]\}$ of $K[x]$. So
  $f \in (x-a)$ means precisely: some $g \in K[x]$ has $f = g\cdot(x-a)$.
- *$\deg(x-a) = 1$;* a non-zero constant has degree $0$; the zero polynomial has
  no degree.
- *Evaluation at $a$ respects $+$ and $\times$* — you used this in $\Leftarrow$.
- The case $f = 0$ is already done and needs no theorem: $0 = 0\cdot(x-a)$, so
  take $f$ non-zero from here on.

---

**Your move.** Apply Theorem 3.7 with $x-a$ as the divisor and your $f$ as the
dividend. It hands you $q$ and $r$ in $K[x]$ with

$$f = q\cdot(x-a) + r, \qquad r = 0 \text{ or } \deg r < 1.$$

Say what that leaves $r$ able to be. Describe **every** polynomial in $K[x]$
that the clause "$r = 0$ or $\deg r < 1$" permits.

One line. Do not touch $f(a) = 0$ yet.
