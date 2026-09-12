---
kind: wrong
title: f(h(s)) is not a thing that exists
---

"Zero divisors" is now right. The lower block still never says why $f$ and $g$ are non-zero — one line, still owed.

**The break is the second line of the new block.** You wrote

$$(f+g)(h(s)) = f(h(s)) + g(h(s)).$$

Look at what $f$ eats. Elements of $R^S$ are functions $S \to R$: $f$ takes an element of $S$ and returns an element of $R$. But $h(s)$ is an element of $R$. So $f(h(s))$ feeds a ring element into a function that is only defined on $S$ — it does not typecheck, and no rearrangement of that line will fix it.

What you have written is **composition** of functions. The multiplication in $R^S$ is not composition. Go back to the defining formula you were given: $(fg)(s) = f(s)g(s)$ — the right-hand side is a *product of two elements of $R$*, not one function fed into another. Nothing in this problem ever puts a function inside a function.

**And the identity you wrote down is false as stated.** $(f+g)h$ does not pair with $fg + fh$. Multiply out $(a+b)c$ in any ring and read off which two products you get.

**Your move.** Same job, stated correctly this time. Let $f, g, h \in R^S$ and prove

$$(f+g)h = fh + gh.$$

Fix an arbitrary $s \in S$ and work at that $s$. Every line you write must be an equation between **elements of $R$**. You are allowed exactly two tools: the two defining formulas, and one named axiom of $R$ — and I want that axiom named on the page where you use it.

Four or five lines, every one of them an equality in $R$.
