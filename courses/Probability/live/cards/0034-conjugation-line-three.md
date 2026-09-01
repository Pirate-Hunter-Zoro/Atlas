---
kind: wrong
title: The $(1\,2)$ vanished between line 2 and line 3
---

That page is conjugation in $S_3$, not Problem 4 — Problem 4 closed at card 0016
and the sheet is compiled and pushed. You wrote over an old answer block. Fine;
I read what is on the page, so here is the page.

You have $h=(1\,2)$, $g=(1\,2\,3)$, $g^{-1}=(1\,3\,2)$, and

$$ghg^{-1}=(1\,2\,3)(1\,2)(1\,3\,2).$$

Three factors. Line 3 has two:

$$=(1\,2\,3)(3\,2\,1).$$

**$(3\,2\,1)$ is $(1\,3\,2)$.** Same cycle, started at a different letter:
$3\mapsto2$, $2\mapsto1$, $1\mapsto3$. So line 3 is $g$ and $g^{-1}$ with the
$h$ deleted — the transposition you were conjugating is gone. Everything after
that is about a different product, which is why line 4 collapses to something
that looks like $g$.

Line 4 does not survive on its own either. Take line 3 exactly as written and
ask what $g$ times $g^{-1}$ is; it is not $g$.

One check on the final answer before you redo it, and it costs no work:
conjugation cannot change cycle type. $ghg^{-1}$ is $h$ with every letter
relabelled by $g$, so a conjugate of a transposition is a **transposition**. You
answered with a $3$-cycle. That alone says the page is wrong without computing
anything.

---

**Your move.** Do the middle product on its own, and only that one:

$$(1\,2)(1\,3\,2)=\ ?$$

Track each of $1$, $2$, $3$ through both factors and say where it lands. State
which order you are composing in — right factor first, or left factor first —
because your answer depends on it and I will read it in whichever convention you
name.
