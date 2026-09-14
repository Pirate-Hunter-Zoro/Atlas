---
kind: question
title: problem-2-linearity-from-the-joint-pmf
---
Correct, and Problem 1 is finished. All three identities are proved.

Six lines, and the shape is right: $(X+Y)-\mu_{X+Y}$ became $(X-\mu_X)+(Y-\mu_Y)$, you multiplied out against $(Z-\mu_Z)$, split the expectation, and read off the two covariances.

Two of those lines were *linearity of expectation*, used silently. Line 2, where $\mu_{X+Y}$ became $\mu_X+\mu_Y$. And line 5, where $E[A+B]$ became $E[A]+E[B]$. That is the sum form of the tool whose constant-multiple form you used in the last proof — and it is exactly what Problem 2 now asks you to prove. Once you have proved it, start naming it in the margin when you use it.

---

**Exercise (Homework 2, Problem 2).**
Let $X_1$ and $X_2$ be discrete random variables and let $a_1$ and $a_2$ be real numbers. **Using the joint probability mass function of $X_1$ and $X_2$**, show that
$$E[a_1X_1 + a_2X_2] \;=\; a_1E[X_1] + a_2E[X_2].$$

*Definitions / symbols used*
- **Joint pmf** $p(x_1,x_2) = P(X_1=x_1,\; X_2=x_2)$: the probability that both variables take those particular values at once. It sums to $1$ over all pairs.
- **Marginal pmf** $p_{X_1}(x_1) = P(X_1=x_1)$: the pmf of $X_1$ on its own, ignoring $X_2$.
- **Expectation of a function of two variables**: $E[g(X_1,X_2)] = \sum_{x_1}\sum_{x_2} g(x_1,x_2)\, p(x_1,x_2)$ — weight each value of $g$ by the probability of the pair that produces it.
- **Expectation of one variable**: $E[X_1] = \sum_{x_1} x_1\, p_{X_1}(x_1)$.

Notice the mismatch the problem is built on: the left side is a double sum against the *joint* pmf, and the right side is two single sums against the *marginal* pmfs. Getting from one to the other is the whole proof.

---

**Your turn.** One small thing first, on a concrete table.

Let $X_1$ take the values $0,1$ and let $X_2$ take the values $1,2$, with this joint pmf:

| $p(x_1,x_2)$ | $x_2=1$ | $x_2=2$ |
|---|---|---|
| $x_1=0$ | $0.1$ | $0.3$ |
| $x_1=1$ | $0.4$ | $0.2$ |

Compute the two row sums: $\sum_{x_2} p(0,x_2)$ and $\sum_{x_2} p(1,x_2)$.

Then tell me what those two numbers *are* — name them as probabilities about $X_1$ alone.
