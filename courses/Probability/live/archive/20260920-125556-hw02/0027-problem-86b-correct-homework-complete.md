---
kind: note
title: problem-86b-correct-homework-complete
---
**Correct. $\approx 0.25$. Homework 2 is finished.**

The exercise was the translation, and you made it in one line: "at least $25$ books done by minute $240$" is the event $S_{25}\le 240$. More books finished means *less* time per book, so the inequality flips direction when you move from counting books to summing times. Everything after that was bookkeeping, and it was clean —
$$E[S_{25}]=25(10)=250,\qquad \mathrm{Var}(S_{25})=25(9)=225,\qquad \mathrm{SD}(S_{25})=15,$$
$$z=\frac{240-250}{15}=-\frac{10}{15}=-\frac{2}{3},\qquad P(Z\le -\tfrac23)\approx 0.2525.$$

Lower tail for a $\le$ event, and you took it as $\Phi(-2/3)$ directly instead of detouring through $1-\Phi(2/3)$.

The notation repair from card 0026 stuck immediately: the inequality is inside the $P$ this time. One residual habit, and it is the last one I will mention — you wrote $P(z^*\le -\frac{10}{15}=-\frac23)$, chaining an arithmetic simplification inside the event. Simplify the fraction outside, then write the event once with the finished number in it. And the standardized variable is $Z$, capital, a random variable like any other; $z^*$ reads like a fixed critical value.

Your margin note is right and worth keeping: the CLT applies to the **sum** and to the **sample mean**, because each is a constant multiple of the other. Which one you reach for is decided by the question — here the question was about elapsed *time*, so the sum.

---

**Where the set stands.** That was the last open problem. All of Homework 2 is answered:

| | | |
|---|---|---|
| 1 | variance and covariance identities | done |
| 2 | linearity of expectation from a joint pmf | done |
| 9 | pmf from a distribution function | done |
| 12 | binomial guessing | done |
| 22 | first head on the fifth trial | done |
| 37 | maximum of uniforms | done |
| 61 | working and repair times, (a)–(e) | done |
| 76 | variance of a product | done |
| 86 | normal approximation, (a) and (b) | done |

The write-up is mine, not yours — you are not typing your own mathematics twice. I am typesetting 76 and 86 into `homework/hw02/hw02.tex` and compiling it now, and your slate pages are filed alongside it in `homework/hw02/handwritten/`. Nothing for you to do while that happens.

**One thing to notice before you close the tablet.** Three different problems in this set came down to the same question — *is this a sum of independent things?* Problem 1 built the covariance machinery that makes $\mathrm{Var}(X+Y)=\mathrm{Var}(X)+\mathrm{Var}(Y)$ true exactly when the covariance vanishes; Problem 76 is what happens when it does not; Problem 86 is what independence buys you once $n$ is large. That is the spine of the chapter, not a coincidence of the assignment.
