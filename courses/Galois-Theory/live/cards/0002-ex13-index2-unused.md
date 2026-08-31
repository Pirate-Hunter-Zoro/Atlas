---
kind: wrong
title: 1.3 — the break is in the "Note that" line
---

Two things are genuinely settled, and I am not sending those back.

- Restating normality as $g H g^{-1} = H$ for all $g$ is legitimate.
- The closure computation, $g h_1 g^{-1} \circ g h_2 g^{-1} = g h_1 h_2 g^{-1}$, is
  correct. $g H g^{-1}$ really is a subgroup.

The break is the sentence beginning **"Note that if $g H g^{-1}$ is a group, this is
necessarily true"**, and everything after it rests on that sentence.

You rule out $g H g^{-1} = G \setminus H$, on the grounds that $G \setminus H$ has no
identity. Fine — but nobody ever suggested $g H g^{-1}$ was $G \setminus H$. The step
you actually need is that $g H g^{-1}$ has to be *one of those two sets in the first
place*, and nothing on the page says that. A subgroup containing $e$ can be a third
thing entirely: neither $H$ nor its complement.

Here is the test that makes it undeniable. Read your argument again and ask where the
hypothesis *index 2* is used. "$G \setminus H$ is not a subgroup" is true for **every**
subgroup $H$ of every group, index 2 or not. So your proof, exactly as written, proves
that every subgroup of every group is normal — and $H = \{e, (12)\}$ in $\Sigma_3$ is
not normal, since $(13)^{-1} \circ (12) \circ (13) = (23) \notin H$.

An argument that proves a false statement has a break in it, and that is where it is.

---

**Your move.** Do not rewrite the proof yet. Just answer this, in one or two lines:

> Fix some $g \notin H$. Index 2 says there are exactly two right cosets. Name them
> both, and then say which coset the element $h \circ g$ lies in, for $h \in H$.

That is the fact your argument is missing, and it is the only thing I want on the page.
