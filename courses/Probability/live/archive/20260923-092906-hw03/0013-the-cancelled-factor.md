---
kind: question
title: the-cancelled-factor
---
Nowhere in the setup — the miss branch is fixed, and the mistake is one algebra step lower down. You dropped a factor of $m-1$ and put $m$ in its place.

Your recursion is now exactly right. Miss branch $\frac{m^n-1}{m-1}+\mu$, hit branch $\frac{m^n-1}{m-1}+1$, weights $\frac{m-1}{m}$ and $\frac{1}{m}$. That is the recursion I would write.

Then you put everything over $m(m-1)$. The hit term is fine: $\frac{m^n+m-2}{m(m-1)}$. The other term is
$$\frac{m^n-1}{m-1}\cdot\frac{m-1}{m},$$
and the two copies of $m-1$ cancel, leaving $\frac{m^n-1}{m}$. Over the denominator $m(m-1)$ that is $\frac{(m-1)(m^n-1)}{m(m-1)}$. You wrote $\frac{m(m^n-1)}{m(m-1)}$ — an $m$ on top where an $m-1$ belongs.

Everything after that inherits it, including the last line. Put $m-1$ back and the whole chain collapses to $\frac{m^{n+1}-1}{m-1}$ in two lines, with no cleanup.

**Exercise (Homework 3, Problem 22).**
Independent trials, each equally likely to have any of $m$ possible outcomes, are performed until the same outcome occurs $k$ consecutive times. If $N$ is the number of trials, show that
$$E[N] = \frac{m^{k}-1}{m-1}.$$

*Definitions / symbols used*
- Each trial takes one of $m$ values, each with probability $1/m$, independently of every other trial.
- The **run** at trial $n$: the number of trials ending at $n$ all showing the same outcome.
- $N_j$ = the first trial at which the run reaches $j$; $N_1=1$ and $N=N_k$.
- $\mu = E[N_{n+1}]$, the unknown in your induction step.
- Induction hypothesis: $E[N_n]=\frac{m^n-1}{m-1}$.
- **Law of total expectation**: $E[X]=\sum_i E[X\mid A_i]P(A_i)$ over a partition $\{A_i\}$.

**The one thing.** Take $m=3$, $n=1$, so $\frac{m^n-1}{m-1}=1$. Give me one number: $\frac{m^n-1}{m-1}\cdot\frac{m-1}{m}$ evaluated there. Then say what that number is when written over the denominator $m(m-1)=6$.
