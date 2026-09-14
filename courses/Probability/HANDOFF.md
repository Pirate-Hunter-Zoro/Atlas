<!-- chapter: hw02 -->
**Where they got to.** Homework 2, Problem 1 is finished and correct: Var(cX)=c^2 Var(X), Cov(cX,Y)=c Cov(X,Y), and Cov(X+Y,Z)=Cov(X,Z)+Cov(Y,Z), all proved from the deviation definition of covariance. Pages filed as homework/hw02/handwritten/hw02-p1-cov-scaled.png and hw02-p1-cov-sum.png. Problem 2 (linearity of expectation from the joint pmf) is posed and open, unanswered.

**Do not re-teach.** The deviation definition Cov(X,Y)=E[(X-mu_X)(Y-mu_Y)] is solid. They now reach for it unprompted as the first move of any covariance proof. They can rewrite (X+Y)-mu_{X+Y} as the sum of the two deviations, multiply out, split the expectation, and read the covariances back off. They also substitute mu_{cX}=c mu_X and pull constants out through E without help.

**What was wrong, earlier in the session.** Nothing in the last two pages. The one standing weakness is bookkeeping, not mathematics: they used linearity of expectation twice on the Cov(X+Y,Z) page with no justification named in the margin -- once collapsing mu_{X+Y} to mu_X+mu_Y, once splitting E[A+B]. They were told to start naming it once Problem 2 proves it. Watch for it; do not lecture again.

**The single next thing.** Marginalization. Card 0006 asks only for the two row sums of a concrete 2x2 joint pmf, named as probabilities about X1 alone -- the point being that summing p(x1,x2) over x2 gives p_{X1}(x1). That one fact is the entire hinge of Problem 2: the left side is a double sum against the joint pmf, the right side is two single sums against marginals. Get that step landed before any algebra.

**How this student works.** They answer on the slate in five or six clean lines and no prose. They label what they are proving at the top themselves, with their own "Prove:" or "(Prove)" tag -- that is a label, not a question to them, so do not answer it as one. They take formatting corrections immediately and keep them. Bare correctness plus one named tool per turn is the right dose.
