---
kind: question
title: Problem 1 – Binomial probability
---
**Exercise (Problem 1).**  
Let $X$ be the number of heads obtained when a fair coin is flipped $n=5$ times, independently.

1. Compute the probability that exactly $k=3$ heads occur, i.e. find $P(X=3)$.

*Definitions / symbols used*  
- **Random variable $X$**: counts the number of heads in the $5$ flips.  
- **Binomial distribution** $\operatorname{Bin}(n,p)$: $X\sim\operatorname{Bin}(n,p)$ when each trial is independent with success probability $p$.  
- **Probability mass function**:  
  $$P(X=k)=\binom{n}{k}p^{\,k}(1-p)^{\,n-k},\qquad k=0,1,\dots,n.$$  
- Here the coin is fair, so $p=\tfrac12$.

**Your turn:** Using the formula above, calculate $P(X=3)$. Write the exact value (as a fraction or simplified decimal).
