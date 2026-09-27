---
kind: question
title: records-61b-name-the-two-steps
---
Good enough for the number, not yet for the proof. Your answer $\mathbb{E}[N] = \sum_{i=1}^{n} 1/i$ is exactly right, and the harmonic sum is what problem 61(b) wants. What is missing is your very first equality. You went from $\mathbb{E}[\#\text{ records by }n]$ straight to $\sum_{i=1}^{n} 1 \cdot P\{\text{record}_i\}$ in one move, and that move IS the problem. Everything after it is arithmetic.

That one move is two separate facts, and neither is written on your page.

The first is a statement about the random variable, with no expectation in it at all: $N$ itself equals a sum of $n$ things, each of which is $0$ or $1$. That is the decomposition the hint asks for, and it is true outcome by outcome, not just on average. Your stray factor of $1$ inside the sum is the ghost of it.

The second is the rule that lets you take $\mathbb{E}$ inside that sum. It has a name, it does not require independence, and you have used it before.

**The tiny thing.** Write the line that belongs between your line 1 and your line 2. Three parts, three short lines:

1. Define $I_i$ in words or symbols -- what it is $1$ for, what it is $0$ for, and what $i$ runs over.
2. Write the identity relating $N$ and the $I_i$.
3. Name the rule that turns $\mathbb{E}$ of that sum into a sum of $\mathbb{E}$'s.

Everything this uses:

- Record at time $i$: the event $X_i > \max(X_1,\ldots,X_{i-1})$. Time $1$ is a record, vacuously.
- $N$: the number of records by time $n$.
- Part (a), proved: $P\{\text{record at time } i\} = 1/i$.
- Indicator variable: a random variable that is $1$ when a stated event happens and $0$ when it does not.
- $X_1,\ldots,X_n$ are i.i.d. and continuous, so ties have probability $0$.

So: the definition of $I_i$, the identity for $N$, and the name of the rule.
