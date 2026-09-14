---
kind: question
title: problem-37-maximum-of-uniforms
---
**Problem 22 is right: $\tfrac1{32}$.** One sequence, TTTTH, and no coefficient — exactly the contrast intended. "First head on trial five" pins down every one of the five flips, so the event is a single outcome of probability $(\tfrac12)^5$; "exactly four heads in five" leaves the position of the tail free, which is what the $\binom54$ was counting.

Next on the sheet: problem **37**. The coin problems are over. This one is continuous, and it is the first problem where the quantity you want is not a variable you were handed — it is a *function* of the variables you were handed.

---

**Exercise (Ross, Ch. 2, Problem 37).**
Let $X_1, X_2, \dots, X_n$ be independent random variables, each having a uniform distribution over $(0,1)$. Let $M = \text{maximum}(X_1, X_2, \dots, X_n)$. Show that the distribution function of $M$, $F_M(\cdot)$, is given by
$$F_M(x) = x^n, \qquad 0 \le x \le 1.$$
What is the probability density function of $M$?

*Definitions / symbols used*
- **Distribution function** $F_X(x) = P\{X \le x\}$: the probability that $X$ lands at or below $x$. You used it on problem 9, reading a pmf off a jump.
- **Uniform on $(0,1)$**: $P\{X_i \le x\} = x$ for $0 \le x \le 1$. The probability of landing below $x$ is just the length of the interval below $x$.
- **Independent**: the probability that several of these events all happen is the *product* of their separate probabilities.
- **$M = \max(X_1,\dots,X_n)$**: the largest of the $n$ values. It is itself a random variable — every draw of the $n$ numbers produces one value of $M$.
- **Probability density function** $f_M$: for a continuous random variable, the function whose derivative relationship to $F_M$ is $f_M(x) = \frac{d}{dx}F_M(x)$.

---

**Your turn.** One translation, no algebra, no answer.

Take $n = 3$ and $x = 0.5$. The event $\{M \le 0.5\}$ — "the largest of the three numbers is at most a half."

**Write that same event as a statement about $X_1$, $X_2$ and $X_3$ individually.** Which of them have to be $\le 0.5$ for $M \le 0.5$ to happen: at least one, exactly one, or all three? Say which, and say why the other two readings are wrong.
