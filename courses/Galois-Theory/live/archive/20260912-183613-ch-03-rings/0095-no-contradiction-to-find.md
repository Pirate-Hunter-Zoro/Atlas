---
kind: note
title: No, and there is nothing to contradict — irreducible is not "cannot be factored".
---

Your two questions first.

**"Will this system lead to a contradiction?"** No, and it never can. Take
$a = 1$, $b = 0$, $c = 2$, $d = 1$: then $ac - 5bd = 2$ and $ad + bc = 1$. That
solution is the factorization
$$2 + i\sqrt{5} = 1 \cdot (2 + i\sqrt{5}),$$
which is perfectly real. Any route ending in *this system has no solutions* is
closed before you start.

And that is not a flaw in your setup. Look again at what you are proving:
irreducible does **not** say $\alpha$ has no factorizations. It says every
factorization $\alpha = \beta\gamma$ has a **unit** in it. Factorizations exist;
you are pinning down what they must look like.

**"Am I right so far?"** The expansion is right — $ac - 5bd$ and
$i\sqrt{5}(ad + bc)$ are both correct this time. But $a, b, c, d \neq 0$ is an
assumption you added and do not have: $\beta = 3$ has $b = 0$ and is not a unit.

The real trouble is that you put $\varphi$ down. Coordinates give you two
coupled integer equations in four unknowns. $\varphi$ gives you one equation in
$\mathbb{N}$ — which is why the problem hands it to you, and why it worked ten
minutes ago in (a).

---

**Your move.** Compute $\varphi(2 + i\sqrt{5})$.

Then list every way that number can be written as a product of two elements of
$\mathbb{N}$.
