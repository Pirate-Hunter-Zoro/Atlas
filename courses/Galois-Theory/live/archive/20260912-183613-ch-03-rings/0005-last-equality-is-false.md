---
kind: wrong
title: The first line finally lands. The last one is false.
---

**This landed, and it is the step you were missing for two revisions:**

$$\big((f+g)h\big)(s) = \big(f(s) + g(s)\big)\,h(s).$$

You evaluated at $s$ and came out with a product of two elements of $R$. No function sits inside another function anywhere in it. That is the move the whole problem runs on, and it is now on the page.

**The break is the last equality.** You wrote

$$f(s)h(s) + g(s)h(s) \;=\; fg(s) \cdot gh(s).$$

A sum went in and a product came out. Nothing between those two expressions can turn a $+$ into a $\cdot$, and the identity you are proving has a $+$ on its right-hand side — so the chain has to end with one.

The second factor is wrong too, and the same slip is in the statement you copied at the top: you have written $fg$ where the identity needs $fh$. Multiply out $(a+b)c$ once more and read off which two products it is.

**Two notes on the middle line.** $f(s)$ and $h(s)$ are both elements of $R$, so they are multiplied by $R$'s own multiplication — $\circ$ means composition, and there is none in this problem. And I asked for the axiom of $R$ you used to be named at the point you use it. It is still not there.

**Your move.** Start from

$$f(s)h(s) + g(s)h(s)$$

and finish the chain, ending at $(fh + gh)(s)$. Every step an equality in $R$.

The one thing this needs: a defining formula is an *equation*, so it reads in both directions. You have been using $(fh)(s) = f(s)h(s)$ left to right all along. The end of this chain needs it right to left.

Still owed, third time: one line saying why $f$ and $g$ are non-zero.
