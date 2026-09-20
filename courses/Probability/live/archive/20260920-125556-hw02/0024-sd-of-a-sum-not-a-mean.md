---
kind: question
title: sd-of-a-sum-not-a-mean
---
**Your question first: the formula you wrote is not wrong — it is the standard deviation of the wrong quantity.**

$\mathrm{SD}=\sigma/\sqrt{n}$ belongs to the **average** $\bar T=S_{40}/40$, not to the **total** $S_{40}$. Those two differ by a factor of $40$:

$$\mathrm{SD}(\bar T)=\mathrm{SD}\!\left(\tfrac{1}{40}S_{40}\right)=\tfrac{1}{40}\mathrm{SD}(S_{40}),$$

by the very identity you proved in Problem 1 — $\mathrm{Var}(cX)=c^2\mathrm{Var}(X)$, so $\mathrm{SD}(cX)=|c|\,\mathrm{SD}(X)$. Put $\sigma/\sqrt{40}=3/\sqrt{40}$ on the left of that and you get $\mathrm{SD}(S_{40})=40\cdot 3/\sqrt{40}$, which is $40$ times larger, not $40$ times smaller. You reached for the sample-mean formula because that is the one that gets drilled; the problem asks about the pile of books, not the typical book. And $E[S_{40}]=400$ is right, by linearity.

**Forget that formula for this problem.** There is a shorter road, and it does not require remembering anything about $\sqrt{n}$.

---

**The road.** Variances of *independent* variables add. Standard deviations do not. So you never add or divide standard deviations directly — you convert to variance, add there, and convert back at the very end.

$$\mathrm{SD}\;\xrightarrow{\;\text{square}\;}\;\mathrm{Var}\;\xrightarrow{\;\text{add}\;}\;\mathrm{Var}\;\xrightarrow{\;\sqrt{\;}\;}\;\mathrm{SD}$$

---

**Your turn — one number, then a second.**

$T_1,\dots,T_{40}$ are independent, each with $E[T_i]=10$ and $\mathrm{SD}(T_i)=3$. $S_{40}=T_1+\cdots+T_{40}$.

1. What is $\mathrm{Var}(S_{40})$?
2. Then what is $\mathrm{SD}(S_{40})$?

*Definitions / symbols used*
- $\mathrm{Var}(Z)=E[(Z-\mu_Z)^2]$, and $\mathrm{SD}(Z)=\sqrt{\mathrm{Var}(Z)}$. So $\mathrm{Var}(T_i)=3^2$.
- **Variance of a sum of independent variables.** $\mathrm{Var}(T_1+\cdots+T_n)=\mathrm{Var}(T_1)+\cdots+\mathrm{Var}(T_n)$. The cross terms are the covariances you split apart in Problem 1; independence kills them.
- All $40$ terms are identical here, so the sum of variances is a multiplication.

Leave it as an exact square root if it is not a whole number; a decimal to two places is fine too. Once those two numbers are down, Problem 86 is four lines of arithmetic and I will put it back in front of you in full.

---

*One filing note, unrelated.* On your 61(b) page the left-hand side is written $f_Y(x,y)$. It should read $f_Y(y)$ — the marginal of $Y$ has only one argument. The integral underneath it is correct; I have typeset it as $f_Y(y)$ in `hw02.tex`.
