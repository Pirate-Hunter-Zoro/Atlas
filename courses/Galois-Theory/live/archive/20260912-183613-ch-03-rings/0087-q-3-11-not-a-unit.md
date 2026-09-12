---
kind: question
title: $x = ra^{-1}$. Correct — the quantifier is right and so is the witness. Now the clause itself.
---

Correct. $r \in (a)$ iff **there exists** $x \in R$ with $xa = r$ — that is the
$\exists$ — and you produced the witness: $x = ra^{-1}$, which lands because
$(ra^{-1})a = r(a^{-1}a) = re = r$. Every $r \in R$ is therefore in $(a)$, so
$(a) = R$.

That was the last rung. Here is what it was for.

---

## The remaining clause of 3.11

**Let $R$ be a commutative ring with identity and let $a \in R$. Show that if
$R/(a)$ is an integral domain, then $a$ is not a unit.**

This is the $(a) = R$ you just proved, pushed into the quotient.

**What the statement uses.**

- $(a) = \{ra : r \in R\}$.
- **Unit:** $a$ is a unit if there is $a^{-1} \in R$ with $aa^{-1} = e$.
- **$R/(a)$:** its elements are the cosets $r + (a)$, and
  $r + (a) = s + (a)$ exactly when $r - s \in (a)$. Its zero is $0 + (a)$; its
  identity is $e + (a)$.
- **Integral domain:** a commutative ring in which $e \neq 0$, and in which
  $xy = 0$ forces $x = 0$ or $y = 0$.
- **Just proved:** if $a$ is a unit then $(a) = R$.

---

**Your move.** Write the proof.
