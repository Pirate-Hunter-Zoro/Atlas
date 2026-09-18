---
kind: lesson
title: both-branches-land-now-the-tower-law-turns-it-into-4
---
**Both cases land, and the hard half of 6(a) is done.** With $a = 0$ you got
$\sqrt{3} = b\sqrt{2}$ and then $2b = \sqrt{6}$ --- right. With $b = 0$ you got
$a = \sqrt{3}$ --- right. Your last line, $\sqrt{3} \neq a + b\sqrt{2}$ for
rational $a, b$, is exactly the statement $\sqrt{3} \notin \mathbb{Q}(\sqrt{2})$.

One tightening, the same one as last card. The contradiction is not "$b \in
\mathbb{Q}$" --- that is your hypothesis, and a hypothesis cannot contradict
itself. It is that $\sqrt{6}$ is irrational. The line $2b = \sqrt{6}$ with $b$
rational makes $\sqrt{6}$ rational, and it is not. Same shape in the other
branch: $a = \sqrt{3}$ with $a$ rational makes $\sqrt{3}$ rational, and it is
not. Each branch names a different irrational.

What is left is turning $\sqrt{3} \notin \mathbb{Q}(\sqrt{2})$ into the number
$4$.

**Problem 6(a), restated.** $K = \mathbb{Q}(\sqrt{2},\sqrt{3})$. Show
$[K:\mathbb{Q}] = 4$.

What this uses:

- $[K:\mathbb{Q}]$ --- the dimension of $K$ as a vector space over $\mathbb{Q}$.
- tower law --- $[K:\mathbb{Q}] = [K:M]\,[M:\mathbb{Q}]$ whenever $\mathbb{Q} \subseteq M \subseteq K$. Here $M = \mathbb{Q}(\sqrt{2})$.
- $[\mathbb{Q}(\sqrt{2}):\mathbb{Q}] = 2$ --- settled earlier, from $x^2 - 2$.
- $[K:\mathbb{Q}(\sqrt{2})]$ --- the degree of the minimal polynomial of $\sqrt{3}$ over $\mathbb{Q}(\sqrt{2})$, since $K = \mathbb{Q}(\sqrt{2})(\sqrt{3})$.
- $\sqrt{3}$ satisfies $x^2 - 3$, which has coefficients in $\mathbb{Q}(\sqrt{2})$. So that minimal polynomial has degree $2$ or degree $1$, nothing else.
- degree $1$ would mean $\sqrt{3} \in \mathbb{Q}(\sqrt{2})$ --- which is what you just killed.

**Your move.** Two things, both one line. What is $[K:\mathbb{Q}(\sqrt{2})]$, and
which of the two possible values did your work rule out? Then put that number and
$[\mathbb{Q}(\sqrt{2}):\mathbb{Q}] = 2$ into the tower law and say what
$[K:\mathbb{Q}]$ is.
