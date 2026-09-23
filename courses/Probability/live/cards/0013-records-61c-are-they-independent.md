---
kind: question
title: records-61c-are-they-independent
---
That is the standard objection, and it is false. The record indicators really are independent.

Here is what the intuition misses. $I_3$ asks one thing: is $X_3$ bigger than both earlier values? That has probability $1/3$ whichever of $X_1, X_2$ happened to be the larger one. Knowing that $X_2$ won its private contest against $X_1$ tells you nothing about how $X_3$ ranks against the pair. "The bar is higher" is true, but the bar is the same height either way -- it is the max of two numbers in both cases.

Don't take that on faith. Count it.

Take $n=3$. Because the $X_i$ are continuous and identically distributed, the six orderings are equally likely. Write each as the ranks of $(X_1, X_2, X_3)$, with $3$ meaning largest:
$$(1,2,3),\quad (1,3,2),\quad (2,1,3),\quad (2,3,1),\quad (3,1,2),\quad (3,2,1).$$

Everything this uses:

- A record occurs at time $i$ when $X_i > \max(X_1, \ldots, X_{i-1})$.
- $I_i$: equals $1$ if a record occurs at time $i$, else $0$.
- So $I_2 = 1$ exactly when $X_2 > X_1$.
- And $I_3 = 1$ exactly when $X_3$ is the largest of the three.
- Two indicators are independent when $P\{I_2=1,\, I_3=1\} = P\{I_2=1\}\,P\{I_3=1\}$.
- All six orderings above have probability $1/6$, from part (a).

Go down the six orderings and mark $I_2$ and $I_3$ for each one.

Then give me three numbers: $P\{I_2=1\}$, $P\{I_3=1\}$, and $P\{I_2=1,\, I_3=1\}$.
