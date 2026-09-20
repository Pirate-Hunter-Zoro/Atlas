---
kind: question
title: problem-2-linearity-from-the-joint-pmf
---
Picking up where we stopped. Problem 1 is finished and correct — all three covariance identities are proved. Problem 2 is open and nothing has been written on it yet, so here it is again in full.

---

**Exercise (Homework 2, Problem 2).**
Let $X_1$ and $X_2$ be discrete random variables and let $a_1$ and $a_2$ be real numbers. **Using the joint probability mass function of $X_1$ and $X_2$**, show that
$$E[a_1X_1 + a_2X_2] \;=\; a_1E[X_1] + a_2E[X_2].$$

*Definitions / symbols used*
- **Joint pmf** $p(x_1,x_2) = P(X_1=x_1,\; X_2=x_2)$: the probability that both variables take those particular values at once. Summed over all pairs it gives $1$.
- **Marginal pmf** $p_{X_1}(x_1) = P(X_1=x_1)$: the pmf of $X_1$ on its own, ignoring what $X_2$ did. Likewise $p_{X_2}(x_2)$.
- **Expectation of a function of two variables**: $E[g(X_1,X_2)] = \sum_{x_1}\sum_{x_2} g(x_1,x_2)\, p(x_1,x_2)$ — weight each value of $g$ by the probability of the pair that produces it.
- **Expectation of one variable**: $E[X_1] = \sum_{x_1} x_1\, p_{X_1}(x_1)$, and $E[X_2] = \sum_{x_2} x_2\, p_{X_2}(x_2)$.

The mismatch the problem is built on: the left side is a *double* sum against the *joint* pmf, and the right side is two *single* sums against the *marginal* pmfs. Getting from one to the other is the whole proof.

---

**Your turn.** One small thing first, on a concrete table.

Let $X_1$ take the values $0,1$ and let $X_2$ take the values $1,2$, with this joint pmf:

| $p(x_1,x_2)$ | $x_2=1$ | $x_2=2$ |
|---|---|---|
| $x_1=0$ | $0.1$ | $0.3$ |
| $x_1=1$ | $0.4$ | $0.2$ |

Compute the two row sums: $\sum_{x_2} p(0,x_2)$ and $\sum_{x_2} p(1,x_2)$.

Then tell me what those two numbers *are* — name them as probabilities about $X_1$ alone.
