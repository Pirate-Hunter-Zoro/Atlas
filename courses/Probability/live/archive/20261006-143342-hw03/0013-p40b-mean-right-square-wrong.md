---
kind: lesson
title: p40b-mean-right-square-wrong
---
**Yes, the concept is right for $E[X]$, and it gives $\mu = \tfrac52$.** Your $\tfrac13\left(2 + \tfrac12\cdot 3\right) + \tfrac13\left(3 + \tfrac12\cdot 2\right)$ conditions on the first door and then on the second. That is exactly the no-repeat model. $\tfrac13(3.5 + 4) = 2.5$ days. I will typeset it.

**The second moment is not right, because the square is in the wrong place.** You wrote $\left(E[X \mid \text{door 1 first}]\right)^2$. The formula needs $E[X^2 \mid \text{door 1 first}]$. Squaring an average is not averaging the squares. Here that costs you $S \approx 9.42$ where the true value is larger.

**Problem 40(c), for model (b).** Find $\mathrm{Var}(X)$ when he never repeats a door.

- $X$ = days until freedom.
- Door 1: back in 2 days. Door 2: back in 3 days. Door 3: free at once.
- Each pick is uniform over the doors not yet used.
- $S = E[X^2] = \sum_{d} E[X^2 \mid \text{first door } d]\, P(\text{first door } d)$.
- $\mathrm{Var}(X) = S - \mu^2$, with $\mu = \tfrac52$.

Given door 1 first, $X = 2$ with probability $\tfrac12$ (door 3 next) and $X = 5$ with probability $\tfrac12$ (door 2, then door 3).

Compute $E[X^2 \mid \text{door 1 first}]$.
