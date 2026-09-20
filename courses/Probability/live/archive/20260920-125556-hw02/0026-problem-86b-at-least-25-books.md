---
kind: question
title: problem-86b-at-least-25-books
---
**Correct. $\approx 0.15$.**

$E[S_{40}]=400$, $\mathrm{SD}(S_{40})=\sqrt{360}=6\sqrt{10}$ — the $3$-versus-$9$ slip is gone. You standardized $420$ to
$$z=\frac{420-400}{6\sqrt{10}}=\frac{20}{6\sqrt{10}}=\frac{\sqrt{10}}{3}\approx 1.054,$$
rationalizing the denominator on the way past without being asked, and took $1-\Phi(z)=0.1459$. A "more than" question, so the upper tail. Right tool, right tail, right number.

One notation repair. You wrote $P(z^*) > \frac{20}{6\sqrt{10}}$. That reads as "the probability of $z^*$, and that is bigger than $1.054$," which is not what you mean. The $>$ belongs *inside* the $P$, and the thing being compared is the random variable:
$$P\left(Z > \frac{\sqrt{10}}{3}\right).$$
Everything inside $P(\cdot)$ is one event; nothing outside it is part of the event.

---

**The exercise (Ross, Ch. 2, Problem 86(b)).**

Each new book donated to a library must be processed. The time a librarian takes to process a book has mean $10$ minutes and standard deviation $3$ minutes. A librarian has $40$ books to process, one at a time.

**(b) Approximate the probability that at least $25$ books are processed in the first $240$ minutes.**

The first move is not arithmetic. It is translating that sentence into an event about a *sum of processing times*, because a sum is the only thing you have a normal approximation for. "At least $25$ books are done by minute $240$" is the same statement as something about $S_{25}$ — decide which, and which direction the inequality runs.

*Definitions / symbols used*
- $T_i$ = time to process book $i$. Independent and identically distributed, $E[T_i]=10$ minutes, $\mathrm{SD}(T_i)=3$ minutes, so $\mathrm{Var}(T_i)=9$ min$^2$.
- $S_n=T_1+\cdots+T_n$, the time at which book $n$ is finished, since the books are processed one at a time with no gaps.
- $E[S_n]=n E[T_i]$ by linearity of expectation.
- $\mathrm{Var}(S_n)=n \mathrm{Var}(T_i)$, because the $T_i$ are independent so all covariance terms vanish. $\mathrm{SD}(S_n)=\sqrt{\mathrm{Var}(S_n)}$ — never scale a standard deviation directly.
- **Central limit theorem.** For large $n$, $Z=\dfrac{S_n-E[S_n]}{\mathrm{SD}(S_n)}$ is approximately standard normal.
- $\Phi(z)=P(Z\le z)$, the standard normal table: probabilities **below** $z$. For negative arguments, $\Phi(-z)=1-\Phi(z)$.
- Already done in (a): $E[S_{40}]=400$, $\mathrm{SD}(S_{40})=6\sqrt{10}$, $P(S_{40}>420)\approx 0.15$.

---

**Your turn.** Answer (b): a single approximate probability, to two decimal places. Start by writing the event as an inequality about $S_{25}$, then standardize and look it up. Show the $z$ you use.
