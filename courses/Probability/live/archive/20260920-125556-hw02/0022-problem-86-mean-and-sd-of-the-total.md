---
kind: question
title: problem-86-mean-and-sd-of-the-total
---
**Problem 76 is done.** The last line is exactly the target: $\sigma_x^2\sigma_y^2 + \mu_y^2\sigma_x^2 + \mu_x^2\sigma_y^2$. You fixed the square of the product, substituted both second moments, expanded, and the $+\mu_x^2\mu_y^2$ from the expansion cancelled the $-\mu_x^2\mu_y^2$ you were carrying. No term was added by hand, as advertised.

**One thing to correct, and it is only on paper.** Your margin note reads
$$E[X^2] = \mathrm{Var}(X) - (E(X))^2 .$$
That sign is backwards. Rearranging $\mathrm{Var}(X)=E[X^2]-(E[X])^2$ moves $(E[X])^2$ to the *other* side, so it arrives with a plus:
$$E[X^2] = \mathrm{Var}(X) + (E(X))^2 = \sigma_x^2+\mu_x^2 .$$
The line above the note already uses the plus version — you wrote $(\sigma_x^2+\mu_x^2)(\sigma_y^2+\mu_y^2)$ and the algebra depends on it. So your hands were right and your margin was wrong. Change the sign; a grader reads the justification you wrote, not the one you meant.

Also, line 1 still says $E[XY]$ where it must say $\mathrm{Var}(XY)$. Second time on this page. Write the left side you actually mean.

---

**Next exercise (Ross, Ch. 2, Problem 86).**

Each new book donated to a library must be processed. The time a librarian takes to process a book has mean $10$ minutes and standard deviation $3$ minutes. A librarian has $40$ books to process, one at a time.

(a) Approximate the probability that it takes more than $420$ minutes to process all $40$ books.
(b) Approximate the probability that at least $25$ books are processed in the first $240$ minutes.

*Definitions / symbols used*
- Write $T_i$ for the time to process book $i$, $i=1,\dots,40$. These are independent and identically distributed, with $E[T_i]=10$ and $\mathrm{SD}(T_i)=3$, so $\mathrm{Var}(T_i)=9$.
- $S_n = T_1+\cdots+T_n$, the total time for the first $n$ books.
- **Linearity of expectation.** $E[S_n]=E[T_1]+\cdots+E[T_n]$, always — independence not required.
- **Variance of a sum of independent variables.** $\mathrm{Var}(S_n)=\mathrm{Var}(T_1)+\cdots+\mathrm{Var}(T_n)$. This needs independence; the cross terms are the covariances you proved split in Problem 1, and they vanish here.
- $\mathrm{SD}(Z)=\sqrt{\mathrm{Var}(Z)}$. Standard deviations do **not** add.
- **Central limit theorem.** For $n$ large, $S_n$ is approximately normal with mean $E[S_n]$ and standard deviation $\mathrm{SD}(S_n)$; equivalently $\big(S_n-E[S_n]\big)/\mathrm{SD}(S_n)$ is approximately standard normal. $\Phi$ denotes the standard normal distribution function.

---

**Your turn. Two numbers, for part (a).**

Take $S_{40}$, the total time for all $40$ books. Give $E[S_{40}]$ and $\mathrm{SD}(S_{40})$.

Say in one word beside each which rule you used, and be careful with the second one — the tempting answer $40\times 3$ is wrong, and the reason it is wrong is the one line of this problem worth getting right.
