---
kind: question
title: problem-12-binomial-guessing
---
**Problem 9 is right, all five masses.** You didn't stop at $P(X=2)$ — you read off the whole pmf, and every jump is correct: $p(0)=\tfrac12$, $p(1)=\tfrac1{10}$, $p(2)=\tfrac15$, $p(3)=\tfrac1{10}$, $p(3.5)=\tfrac1{10}$. They sum to $1$, which is the check that there is no sixth atom hiding anywhere. Add one line to finish the statement of a pmf: $p(a)=0$ for every other $a$.

Your margin rule, stated exactly. The jump at $a$ is $F(a)$ minus the **left-hand limit** $\lim_{b\uparrow a}F(b)$, not $F$ at the previous atom. Here those are the same number — $F$ is flat across $[0,1)$, so $F(1^-)=F(0)=\tfrac12$ — which is why $F(1)-F(0)$ gave you the right $\tfrac1{10}$. Write it as $F(1)-F(1^-)$ anyway; the shortcut only survives because the function is constant between the atoms.

Next on the sheet: problem **12**.

---

**Exercise (Ross, Ch. 2, Problem 12).**
On a multiple-choice exam with three possible answers for each of the five questions, what is the probability that a student would get four or more correct answers just by guessing?

*Definitions / symbols used*
- **Bernoulli trial**: one attempt with two outcomes, success or failure, success probability $p$, and no influence on any other attempt.
- **Binomial random variable** $X\sim\mathrm{Bin}(n,p)$: the number of successes in $n$ independent Bernoulli trials, each with success probability $p$. Its pmf is
$$P(X=i)=\binom{n}{i}p^i(1-p)^{n-i},\qquad i=0,1,\dots,n.$$
- **Binomial coefficient** $\binom{n}{i}=\dfrac{n!}{i!\,(n-i)!}$: the number of ways to choose *which* $i$ of the $n$ trials are the successes.
- **Guessing**: on a question with three answers, one of which is right, a blind guess is correct with probability $\tfrac13$ and wrong with probability $\tfrac23$, independently of the other questions.
- **"Four or more"** means the count of correct answers is at least $4$ — so $P(X\ge 4)$, not $P(X=4)$.

---

**Your turn.** One number first, not the whole thing.

What is $P(X=4)$ — the probability of getting exactly four of the five right by guessing? Leave it as a fraction over $243$. One line saying how many arrangements of four-right-one-wrong there are, and what each one is worth.
