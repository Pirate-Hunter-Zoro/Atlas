---
kind: correct
title: $\beta$ or $\gamma$ is a unit. Correct — 3.12(b) is done. Now (c).
---

That closes it. The step that carried the whole proof is the boxed **NO**:
$\varphi$ never takes the value $3$, so the $3 \cdot 3$ branch cannot happen,
and every surviving branch puts $\varphi = 1$ on one of the factors. Which
contradicts *not units*.

$2 - i\sqrt{5}$ needs no separate work — $\varphi(2 - i\sqrt{5}) = 9$ as well,
so the argument is the same one, word for word. I will say so in the write-up.

---

## 3.12(c)

Let $R = \mathbb{Z} + i\sqrt{5}\,\mathbb{Z}$. Show that $2 + i\sqrt{5}$ is
**not prime** in $R$, and deduce that $R$ is not a unique factorization domain.

What the statement uses:

- $R = \{m + i\sqrt{5}\,n : m, n \in \mathbb{Z}\}$, a subring of $\mathbb{C}$.
- $\varphi(m + i\sqrt{5}\,n) = m^2 + 5n^2$, and $\varphi(\alpha\beta) = \varphi(\alpha)\varphi(\beta)$.
- *Units of $R$:* exactly $\pm 1$ — part (a).
- *$a \mid b$ in $R$:* there is some $c \in R$ with $b = ac$. The $c$ must lie in $R$.
- *Prime* (Garling, p. 362; $a$ non-zero and not a unit): whenever $a \mid bc$, either $a \mid b$ or $a \mid c$.
- *Irreducible:* $a$ is not a unit, and $a = bc$ forces $b$ or $c$ to be a unit — which is what you just proved for $2 \pm i\sqrt{5}$.
- *Named result:* in a unique factorization domain, every irreducible element is prime.

---

**Your move.** Show $2 + i\sqrt{5}$ is not prime.

Only that half. It uses the same number $9$ you just computed, and the same
short list of its factorizations.
