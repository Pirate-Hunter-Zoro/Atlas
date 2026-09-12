---
kind: note
title: "Right so far — yes, and one line of it is doing no work"
---

Yes. The zero-divisor half of the forward direction is correct, and the step
that carries it is the one you used without naming: primality read backwards.
$a$ prime says $a \mid r_{1}r_{2} \Rightarrow a \mid r_{1}$ or $a \mid r_{2}$;
contrapose it and you get exactly your line — $a \nmid r_{1}$ and
$a \nmid r_{2}$ force $a \nmid r_{1}r_{2}$, so $r_{1}r_{2} + (a)$ is not the
zero class. Two non-zero classes, non-zero product. No zero divisors.

One line in it is doing no work: *since $r_{1}r_{2}$ is nonzero due to $R$
being an integral domain*. That $r_{1}r_{2} \neq 0$ in $R$ is true and
irrelevant — a class $r + (a)$ is zero when $a \mid r$, not when $r = 0$. Your
conclusion rests on $a \nmid r_{1}r_{2}$ alone. Drop it or keep it, but know it
is not load-bearing.

---

**Your move.** You have shown $R/(a)$ has no zero divisors. That is not yet an
integral domain — the definition also demands $1 \neq 0$, and in $R/(a)$ that
reads
$$1 + (a) \neq 0 + (a).$$

Prove it, still assuming $a$ prime. Name which part of the definition of prime
you used.
