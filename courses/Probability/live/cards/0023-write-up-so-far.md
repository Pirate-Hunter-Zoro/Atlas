---
kind: question
title: write-up-so-far
---
**Answering your question first: yes — I am writing it up now, while you read this.**

That is my job, not yours. You do not transcribe your own work twice. What goes into `homework/hw02/hw02.tex`, and then into the compiled `build/hw02.pdf`:

- **Problem 1** — $\mathrm{Var}(cX)=c^2\mathrm{Var}(X)$, $\mathrm{Cov}(cX,Y)=c\,\mathrm{Cov}(X,Y)$, $\mathrm{Cov}(X+Y,Z)=\mathrm{Cov}(X,Z)+\mathrm{Cov}(Y,Z)$.
- **Problem 2** — linearity of expectation from the joint pmf, via marginalization.
- **Problem 9** — pmf recovered from a distribution function by jump sizes.
- **Problem 12** — binomial guessing.
- **Problem 22** — first head on the fifth trial.
- **Problem 37** — maximum of uniforms.
- **Problem 61** — all five parts: the density of $X$, the density of $Y$, the joint density of $X$ and $W$ through the change of variables $W=Y-X$, the density of $W$, and the independence of $X$ and $W$.
- **Problem 76** — $\mathrm{Var}(XY)=\sigma_x^2\sigma_y^2+\mu_y^2\sigma_x^2+\mu_x^2\sigma_y^2$ for independent $X,Y$.

Your handwritten pages are the record; the `.tex` is the typeset version of them, nothing added and nothing invented. I will say when the PDF compiles clean. Problem 86 is the only one still open, so it is the only gap in the document.

**On the page you just sent.** Both corrections landed. Line 1 now reads $\mathrm{Var}[XY]$, which is the quantity you are actually computing. The margin note now reads $E[X^2]=\mathrm{Var}(x)+(E(X))^2$ — plus, matching the $(\sigma_x^2+\mu_x^2)$ you use one line below it. Nothing else on the page changed, and nothing else needed to.

---

**Still open (Ross, Ch. 2, Problem 86).** Restated in full so you do not have to scroll.

Each new book donated to a library must be processed. The time a librarian takes to process a book has mean $10$ minutes and standard deviation $3$ minutes. A librarian has $40$ books to process, one at a time.

(a) Approximate the probability that it takes more than $420$ minutes to process all $40$ books.
(b) Approximate the probability that at least $25$ books are processed in the first $240$ minutes.

*Definitions / symbols used*
- $T_i$ is the time to process book $i$, for $i=1,\dots,40$. The $T_i$ are independent and identically distributed with $E[T_i]=10$ and $\mathrm{SD}(T_i)=3$, hence $\mathrm{Var}(T_i)=9$.
- $S_n=T_1+\cdots+T_n$ is the total time for the first $n$ books.
- **Linearity of expectation.** $E[S_n]=E[T_1]+\cdots+E[T_n]$. Always true; independence not required.
- **Variance of a sum of independent variables.** $\mathrm{Var}(S_n)=\mathrm{Var}(T_1)+\cdots+\mathrm{Var}(T_n)$. This one *does* need independence — the cross terms are the covariances you split in Problem 1, and they vanish here.
- $\mathrm{SD}(Z)=\sqrt{\mathrm{Var}(Z)}$. Standard deviations do **not** add.
- **Central limit theorem.** For large $n$, $S_n$ is approximately normal with mean $E[S_n]$ and standard deviation $\mathrm{SD}(S_n)$; equivalently $(S_n-E[S_n])/\mathrm{SD}(S_n)$ is approximately standard normal. $\Phi$ is the standard normal distribution function.

**Your turn. Two numbers.**

Give $E[S_{40}]$ and $\mathrm{SD}(S_{40})$, with one word beside each naming the rule you used. The second one is the whole point of the problem: $40\times3$ is wrong, and knowing why is the line worth getting right.
