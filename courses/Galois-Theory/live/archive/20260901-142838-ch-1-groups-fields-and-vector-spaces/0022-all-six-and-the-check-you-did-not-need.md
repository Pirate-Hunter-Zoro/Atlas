---
kind: correct
title: All six — and the check you did not need to do
---
Correct, and every one of the six products on the page is right. $hg = (2\,3)$, $gh = (1\,3)$, $g^2h = (2\,3)$, $hg^2 = (1\,3)$, and both $h^2g$ and $gh^2$ collapse to $g$. So

$$\langle h, g\rangle = \{e, (1\,2), (1\,3), (2\,3), (1\,2\,3), (1\,3\,2)\} = \Symn{3}.$$

Six elements. Two generators, and they pull the whole group out.

Now your margin note — *obviously others, I just didn't exhaustively check*. You did not have to, and the reason is worth having. $\langle h, g\rangle$ is a subgroup of $\Symn{3}$ by construction, and $\Symn{3}$ has exactly six elements. You exhibited six distinct ones inside it. A subset of a six-element set with six elements in it **is** that set. So closure and inverses are not something left unverified — they were handed to you the moment the count hit the ceiling.

That is a move you will use again: to prove a subgroup is everything, you do not check the axioms, you count.

The next exercise turns on a different consequence of conjugation, so here is the one line it needs.

**Your move:** let $x$ and $g$ be any two elements of any group, and write $y = gxg^{-1}$. Multiply out $y^2 = (gxg^{-1})(gxg^{-1})$ and simplify it as far as it goes. One line. Then say what $y^k$ is, for a general positive integer $k$.
