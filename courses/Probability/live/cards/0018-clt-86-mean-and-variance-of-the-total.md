---
kind: question
title: clt-86-mean-and-variance-of-the-total
---
Your question on the page answers itself, and you answered it: $\Var(Y)/\varepsilon^2 = \sigma^2/(n\varepsilon^2)$, which goes to $0$ as $n\to\infty$ for every fixed $\varepsilon>0$. That is 76, done, and done in one pass. $\E[\bar{X}_n]=\mu$ by linearity; $\Var(\bar{X}_n)=\sigma^2/n$ because the constant $1/n$ comes out squared and independence lets the $n$ variances add; Chebyshev at $k=\varepsilon$ then bounds the probability by $\sigma^2/(n\varepsilon^2)$.

One seam I closed for you in the write-up. You stated Chebyshev with $\ge k$, and the problem asks about $>\varepsilon$. The strict event sits inside the non-strict one, so the bound still applies --- the file now carries that line, and 76 is typeset.

Last problem of the set. 86.

**Each new book donated to a library must be processed. The time it takes a librarian to process a book has mean 10 minutes and standard deviation 3 minutes. A librarian has 40 books that must be processed, one at a time.**

**(a) Approximate the probability that it will take more than 420 minutes to process all 40 books.**

**(b) Approximate the probability that at least 25 books will be processed in the first 240 minutes.**

Everything this uses:

- $T_i$: the time to process book $i$. The $T_i$ are independent and identically distributed with $\E[T_i]=10$ and $\mathrm{SD}(T_i)=3$, so $\Var(T_i)=9$.
- $S_n = T_1 + \cdots + T_n$: the total time for the first $n$ books.
- The central limit theorem: for large $n$, $S_n$ is approximately normal with mean $n\mu$ and variance $n\sigma^2$. The word "approximate" in the problem is naming this and nothing else.
- Standardizing: $P\{S_n > a\} \approx P\{Z > (a - n\mu)/\sqrt{n\sigma^2}\}$, where $Z$ is standard normal.
- $\Phi$: the standard normal distribution function, $\Phi(z) = P\{Z \le z\}$, read off the table in the back of the text.
- $\Var(\sum T_i) = \sum \Var(T_i)$ for independent summands --- the same step you used in 76.

Part (b) has a translation in it that part (a) does not, so leave it alone for now.

One thing first, for (a). The random variable you are aiming the central limit theorem at is $S_{40}$. What are $\E[S_{40}]$ and $\Var(S_{40})$?
