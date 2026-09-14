---
kind: question
title: problem-9-pmf-from-a-distribution-function
---
**Problem 2 is correct and finished.** You skipped the row-sum warm-up and did the whole thing, and every line of it holds: expand $g(x_1,x_2)=a_1x_1+a_2x_2$ against the joint pmf, split the double sum in two, collapse each inner sum into a marginal, pull the constants out. Both of the hard moves are there — you swapped the order of summation on the second term so that $x_1$ was the *inner* index, which is exactly what lets $\sum_{x_1}p(x_1,x_2)$ become $p_{X_2}(x_2)$. Problems 1 and 2 are both done.

One piece of bookkeeping, the same one as last time. The step from line 2 to line 3 is **marginalization** — $\sum_{x_2}p(x_1,x_2)=p_{X_1}(x_1)$ — and it is the whole point of the problem, so name it in the margin where you use it. Same for the interchange of the two summations. Also write $a_1$ and $a_2$ with their subscripts all the way down; from line 3 on they drift into a bare $a$.

Next is the textbook. Edition 11, problem **9**.

---

**Exercise (Ross, Ch. 2, Problem 9).**
If the distribution function of $X$ is given by
$$F(b) = \begin{cases} 0 & b<0\\[2pt] \tfrac{1}{2} & 0\le b<1\\[2pt] \tfrac{3}{5} & 1\le b<2\\[2pt] \tfrac{4}{5} & 2\le b<3\\[2pt] \tfrac{9}{10} & 3\le b<3.5\\[2pt] 1 & b\ge 3.5\end{cases}$$
calculate the probability mass function of $X$.

*Definitions / symbols used*
- **Distribution function (cdf)** $F(b)=P(X\le b)$: the probability that $X$ lands at or below $b$. It never decreases, and it runs from $0$ up to $1$.
- **Probability mass function (pmf)** $p(a)=P(X=a)$: the probability that $X$ hits the single value $a$ exactly. It is $0$ everywhere except at countably many points, and those values sum to $1$.
- **The link between them, for a discrete $X$**: $F$ is a step function, flat except where it jumps. $P(X=a)$ equals the *size of the jump* of $F$ at $a$ — the value $F$ takes at $a$ minus the value it held just to the left of $a$.
- **Answering "calculate the pmf"** means: list every value $X$ can take, and the probability of each.

---

**Your turn.** One number first.

$F$ holds steady at $\tfrac{3}{5}$ across $1\le b<2$, then sits at $\tfrac{4}{5}$ across $2\le b<3$.

What is $P(X=2)$? One number, and one line saying which two values of $F$ you subtracted.
