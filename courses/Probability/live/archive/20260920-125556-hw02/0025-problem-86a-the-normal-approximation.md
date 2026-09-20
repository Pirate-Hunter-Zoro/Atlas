---
kind: question
title: problem-86a-the-normal-approximation
---
**The road is right; one number got substituted wrong.** You wrote $\mathrm{Var}(S_{40}) = 40\,\mathrm{Var}(T) = 120$. That uses $\mathrm{Var}(T)=3$. But $3$ is the *standard deviation* of $T$, not its variance:

$$\mathrm{Var}(T_i)=\mathrm{SD}(T_i)^2=3^2=9 .$$

So $\mathrm{Var}(S_{40}) = 40\cdot 9 = 360\ \text{min}^2$, and $\mathrm{SD}(S_{40}) = \sqrt{360} = 6\sqrt{10} \approx 18.97$ minutes.

Everything around that substitution is exactly what I asked for. You refused to touch the standard deviation directly, went down to variance, multiplied by $40$ because the terms are identical, came back up with a square root, and simplified $\sqrt{120}$ to $2\sqrt{30}$ without being told to. The $\sqrt{n}$ formula is gone and did not come back. $E[S_{40}]=400$ by linearity, correct.

Two notes on the page itself. You wrote $40\,E[S]$ and $40\,\mathrm{Var}[S]$ — but $S$ is the name you gave the *total*, $S_{40}$. The single book is $T$. Using one letter for both the part and the whole is how the $3$-versus-$9$ slip survives unnoticed. And carry the units as you did: $\mathrm{min}^2$ for a variance, $\mathrm{min}$ for a standard deviation, is a free check that you squared the right thing.

---

**The exercise (Ross, Ch. 2, Problem 86).**

Each new book donated to a library must be processed. The time a librarian takes to process a book has mean $10$ minutes and standard deviation $3$ minutes. A librarian has $40$ books to process, one at a time.

**(a) Approximate the probability that it takes more than $420$ minutes to process all $40$ books.**

(Part (b) comes after.)

*Definitions / symbols used*
- $T_i$ = time to process book $i$, for $i=1,\dots,40$. Independent and identically distributed, $E[T_i]=10$, $\mathrm{SD}(T_i)=3$, so $\mathrm{Var}(T_i)=9$.
- $S_{40}=T_1+\cdots+T_{40}$, the total processing time. "More than $420$ minutes to process all $40$" is the event $S_{40}>420$.
- Already established, this turn: $E[S_{40}]=400$ minutes, $\mathrm{Var}(S_{40})=360\ \mathrm{min}^2$, $\mathrm{SD}(S_{40})=6\sqrt{10}\approx 18.97$ minutes.
- **Central limit theorem.** For large $n$, the standardized sum
$$Z=\frac{S_n-E[S_n]}{\mathrm{SD}(S_n)}$$
is approximately standard normal. $n=40$ counts as large.
- $\Phi(z)=P(Z\le z)$ is the standard normal distribution function — the table in the back of Ross. It gives probabilities **below** $z$, so a "more than" question needs $1-\Phi(z)$.
- $\Phi$ is only tabulated for $z\ge 0$; for negative arguments use $\Phi(-z)=1-\Phi(z)$.

---

**Your turn.** Answer (a): a single approximate probability, to two decimal places. Show the standardization step — the value of $z$ you look up — so the tool is on the page and not just in your head.
