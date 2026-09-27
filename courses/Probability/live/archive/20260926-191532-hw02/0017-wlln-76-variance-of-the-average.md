---
kind: question
title: wlln-76-variance-of-the-average
---
That is 61(d), finished, and by the more expensive road. You computed $P\{N=i\}$ head-on and got $(i-2)!/i!$, which is right: among the $i!$ equally likely orderings of $X_1,\ldots,X_i$, the ones in $\{N=i\}$ need $X_i$ largest overall and $X_1$ largest of the rest, leaving the other $i-2$ values free. Then $i \cdot (i-2)!/i! = (i-2)!/(i-1)! = 1/(i-1)$, and $\sum_{i\ge2} 1/(i-1)$ is the harmonic series, so $\E[N]=\infty$. I said the "and" inside $\{N=i\}$ was the costly part; you priced it at one factorial and paid it. Problem 61 is written up in full --- all four parts, your counting argument in (d), not the tail one.

Next is 76, the whole of it.

**Let $X_1, X_2, \ldots$ be independent and identically distributed with mean $\mu$ and variance $\sigma^2$. Using Chebyshev's inequality, show that for every $\varepsilon > 0$,**
$$P\left\{\left|\frac{X_1 + \cdots + X_n}{n} - \mu\right| > \varepsilon\right\} \to 0 \quad \text{as } n \to \infty.$$

Everything this uses:

- $\bar{X}_n$: the sample mean $(X_1 + \cdots + X_n)/n$, the thing inside the absolute value.
- Chebyshev's inequality: for any random variable $Y$ with finite mean and variance, and any $k > 0$, $P\{|Y - \E[Y]| \ge k\} \le \Var(Y)/k^2$.
- $\Var(cX) = c^2\Var(X)$ for a constant $c$ --- you proved this in Problem 1.
- Variance adds over independent summands: $\Var(\sum Y_i) = \sum \Var(Y_i)$ when the $Y_i$ are independent --- the step you paid for in 61(c).
- $\E[\bar{X}_n] = \mu$, by linearity.

One thing before the inequality. Chebyshev needs the variance of the random variable you are aiming it at, and that variable is $\bar{X}_n$. What is $\Var(\bar{X}_n)$, in terms of $\sigma^2$ and $n$?
