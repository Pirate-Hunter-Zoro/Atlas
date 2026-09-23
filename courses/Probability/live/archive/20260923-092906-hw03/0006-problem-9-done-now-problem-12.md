---
kind: correct
title: problem-9-done-now-problem-12
---
The proof is right, and it is the whole of Problem 9. Three lines: definition of conditional expectation, independence, definition of expectation.

One line is missing in the middle, and it is the only line a grader would ask for. You wrote "(independent)" over the step from $P(X = x \mid Y = y)$ to $p(x)$. The justification is a cancellation, so show it:
$$
p_{X \mid Y}(x \mid y) = \frac{p(x,y)}{p_Y(y)} = \frac{p_X(x)\,p_Y(y)}{p_Y(y)} = p_X(x).
$$
That is answer (b) to the question on the last card, and $p_Y(y)$ is what cancels. Note it needs $p_Y(y) > 0$, which is where the conditional is defined anyway.

I have typeset Problem 9 in `homework/hw03/hw03.tex` with that cancellation written out as its own line, and filed your page beside it.

---

**Exercise (Homework 3, Problem 12).**
The joint density of $X$ and $Y$ is
$$
f(x,y) = \frac{e^{-x/y}\,e^{-y}}{y}, \qquad 0 < x < \infty,\ \ 0 < y < \infty .
$$
Show that $E[X \mid Y = y] = y$.

*Definitions / symbols used*
- **Joint density** $f(x,y)$: probability is its integral over a region, not a value at a point.
- **Marginal density** $f_Y(y) = \int_{-\infty}^{\infty} f(x,y)\,dx$ — the continuous version of the marginalisation you used in Problems 1 and 7.
- **Conditional density** $f_{X \mid Y}(x \mid y) = f(x,y) / f_Y(y)$, defined where $f_Y(y) > 0$.
- **Conditional expectation** $E[X \mid Y = y] = \int_{-\infty}^{\infty} x\,f_{X \mid Y}(x \mid y)\,dx$.
- **Exponential density with rate $\lambda$**: $\lambda e^{-\lambda x}$ on $x > 0$, with mean $1/\lambda$.
- $y$ is fixed throughout. Every integral runs over $x$ alone, from $0$ to $\infty$.

---

**Your turn.** One integral, before the proof. Compute
$$
f_Y(y) = \int_0^{\infty} \frac{e^{-x/y}\,e^{-y}}{y}\,dx .
$$
Give the answer in terms of $y$, and say which factors came out of the integral because $y$ is fixed.

Then the exercise itself: for the density $f(x,y) = e^{-x/y}e^{-y}/y$ on $0 < x < \infty$, $0 < y < \infty$, show that $E[X \mid Y = y] = y$.
