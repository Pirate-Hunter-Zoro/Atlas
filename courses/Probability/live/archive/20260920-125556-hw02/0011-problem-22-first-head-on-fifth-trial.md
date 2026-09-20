---
kind: question
title: problem-22-first-head-on-fifth-trial
---
**Problem 12 is right: $\tfrac{11}{243}$.** $P(X=4)=\binom{5}{4}(\tfrac13)^4(\tfrac23)=\tfrac{10}{243}$ and $P(X=5)=(\tfrac13)^5=\tfrac1{243}$. The coefficient is where these problems are lost and you had it: five different questions can be the one you miss, so the four-right outcome is worth five times what a single arrangement is worth. The all-five case carries $\binom55=1$, which is why no coefficient shows there.

Next on the sheet: problem **22**. It looks like more of the same and is not — the counting goes the other way.

---

**Exercise (Ross, Ch. 2, Problem 22).**
If a fair coin is successively flipped, find the probability that a head first appears on the fifth trial.

*Definitions / symbols used*
- **Fair coin**: each flip is heads with probability $\tfrac12$ and tails with probability $\tfrac12$.
- **Successively flipped**: the flips are independent — the probability of a particular sequence of outcomes is the product of the individual probabilities.
- **"A head first appears on the fifth trial"**: the fifth flip is a head, *and* none of flips 1 through 4 was a head.
- **Binomial coefficient** $\binom{n}{i}$: the number of ways to choose which $i$ of the $n$ trials are the successes. You used it on problem 12 to count arrangements.

---

**Your turn.** One count, not the answer.

In problem 12 the event "exactly four right" was made of $\binom54=5$ different outcome sequences. Here: **how many different sequences of five flips make up the event "the first head is on the fifth trial"?** Write the sequences out, in order, as a string of H's and T's.
