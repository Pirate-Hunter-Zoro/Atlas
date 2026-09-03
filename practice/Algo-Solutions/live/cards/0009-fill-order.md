---
kind: correct
title: Nothing on the right you cannot already have
---

$\mathcal{E} = \{4,8,12\}$ and

$$E(4) \;=\; A(4) - E(8) - E(12).$$

Correct. The step that carried it was reading the bucket sum off $A(4)$ rather than off $A(2)$: now every $E$ on the right is a **larger** $g$ than the one on the left.

## Your move

Before any code, fix the order the table gets filled in.

Still `nums = [1,2,3,4,5,6,7,8,9,10,11,12]`. **Write $E(12)$ and $E(6)$ in exactly the form you just wrote $E(4)$** — each one alone on the left, an $A$ and then whatever $E$ terms it subtracts.

Same identity as before: $A(g) = \sum E(m)$ over the multiples $m$ of $g$ with $m \le \max(\texttt{nums}) = 12$.
