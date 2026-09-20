<!-- chapter: hw03 -->
Homework 3 (Ross ch. 3): problems 1, 7, 9-or-10, 12, 22, 31, 37, 40. All eight statements are already transcribed into `homework/hw03/hw03.tex`.

**Done and correct: Problem 1** — sum over x of p(X|Y)(x|y) = 1. Do not re-teach it. They now own the whole argument: chain rule p(x,y) = p_X(x) p_{Y|X}(y|x), 1/p_Y(y) pulled out because y is fixed, and sum over x of p(x,y) = p_Y(y). Their proof is typeset in SOLUTION 1, their page is `handwritten/hw03-1.png`, and the build is clean (2 pages, 0 warnings).

**What it cost them, three attempts.** First attempt assumed independence, which the problem does not give. Second dropped independence but bolted a sum over y onto a statement where y is fixed — and the p_Y(y) denominator would have blocked pulling it out anyway. The real gap behind both: they did not see that marginalising the joint over x rebuilds p_Y(y). That is the move to keep pointing at when a conditional-pmf argument stalls.

**Next: Problem 7**, posed on card 0004 and unanswered. Joint pmf of X, Y, Z in eight cells; find E[X | Y=2] and E[X | Y=2, Z=1]. The open ask is just the denominator: the four cells with y=2, summing to p_Y(2) = 5/16. It is the right next thing because it is the same marginalisation they just proved, now with numbers, and it is the arithmetic half of the conditioning they have only done symbolically. After the denominator, the numerator is sum over x of x·p(x,2); then the second part conditions on two variables at once, which narrows to two cells.

**How this student works.** They answer with a full proof rather than the small numeric step you asked for — twice now they skipped the baby table entirely and sent the next attempt at the real thing. Do not chase the skipped sub-question; read what they actually sent and mark that. They work in symbols by preference and are quick, so a wrong line is usually one misplaced quantifier, not confusion about the object. Name the single defective symbol and stop.
