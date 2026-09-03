---
kind: review
title: True, but it is the wrong A
---

Your last line is a true equation. Start from $A(2) = \sum_{e \in \mathcal{E}} E(e)$ with $\mathcal{E} = \{2,4,6,8,10,12\}$, move everything but $E(4)$ across, and you do get

$$E(4) \;=\; A(2) \;-\!\!\sum_{e \in \mathcal{E}\setminus\{4\}}\!\! E(e).$$

Nothing is wrong with the algebra. What is wrong is which $A$ you inverted.

Look at what sits on the right: $E(2)$ is one of the terms. So to get $E(4)$ you would first need $E(2)$ — and $E(2)$'s own identity has $E(4)$ on *its* right. Each one needs the other. That is not something you can compute in any order.

The identity holds for **every** $g$, not just $g = 2$. Pick the $g$ that makes the right-hand side contain only things you could already know.

## Your move

Still `nums = [1,2,3,4,5,6,7,8,9,10,11,12]`.

Write down $A(4)$'s bucket sum — which $m$ are in it — and then rearrange **that** one so $E(4)$ stands alone on the left.

Definitions, as you have them:

- $A(g)$: the number of strictly increasing subsequences of `nums` in which every element is divisible by $g$.
- $E(g)$: the number of strictly increasing subsequences of `nums` whose GCD is exactly $g$.
- The identity: $A(g) = \sum E(m)$ over the multiples $m$ of $g$ with $m \le \max(\texttt{nums})$.
