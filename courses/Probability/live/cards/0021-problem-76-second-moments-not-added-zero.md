---
kind: question
title: problem-76-second-moments-not-added-zero
---
**Your question first: "Is there a clever way to add zero?"**

No — and you will not need one. The term you are hunting for gets manufactured for free and then cancels on its own. Adding and subtracting a term is the right instinct for the covariance proofs you did earlier, but this problem has a different engine: you replace each *second moment* $E[X^2]$, $E[Y^2]$ by what the variance identity says it equals, expand the product, and one of the four terms that falls out is exactly the one that kills $\mu_x^2\mu_y^2$. Nothing is added by hand.

---

**On the working.** The independence step is right, and you named it correctly in the margin: $E[X^2Y^2]=E[X^2]E[Y^2]$ because $X\perp Y$ makes expectation split across a product. That was the question and you answered it.

Two things on the page.

1. Line 1 reads $E[XY] = E[(XY)^2]-(E[XY])^2$. The left side is $\mathrm{Var}(XY)$, not $E[XY]$. The rest of the page treats it as the variance, so this is a slip of the pen, but it is the quantity the whole problem is about — write it.

2. The real one. You went from $\big(E[X]E[Y]\big)^2$ to $E^2[X] - E^2[Y]$. Squaring a **product** gives a **product**:
$$\big(E[X]E[Y]\big)^2 = E^2[X]\,E^2[Y] = \mu_x^2\mu_y^2,$$
one term, not two, and joined by multiplication. That minus sign is why the page stalled — you were staring at a target with three terms and holding an expression that could not produce them. Fix that and the line reads
$$\mathrm{Var}(XY) = E[X^2]E[Y^2] - \mu_x^2\mu_y^2.$$

---

**Exercise (Ross, Ch. 2, Problem 76).**
Let $X$ and $Y$ be independent random variables with means $\mu_x$, $\mu_y$ and variances $\sigma_x^2$, $\sigma_y^2$. Show that
$$\mathrm{Var}(XY) \;=\; \sigma_x^2\sigma_y^2 \;+\; \mu_y^2\sigma_x^2 \;+\; \mu_x^2\sigma_y^2.$$

*Definitions / symbols used*
- $\mathrm{Var}(Z) = E[(Z-\mu_Z)^2]$, and equivalently $\mathrm{Var}(Z) = E[Z^2] - (E[Z])^2$.
- $E[X]=\mu_x$, $E[Y]=\mu_y$, $\mathrm{Var}(X)=\sigma_x^2$, $\mathrm{Var}(Y)=\sigma_y^2$.
- **Independence.** $X\perp Y$ lets expectation split across a product: $E[XY]=E[X]E[Y]$, and likewise $E[X^2Y^2]=E[X^2]E[Y^2]$.
- $E^2[X]$ means $(E[X])^2$.
- Where you are: $\mathrm{Var}(XY) = E[X^2]E[Y^2] - \mu_x^2\mu_y^2$.

---

**Your turn. Two short lines.**

The identity $\mathrm{Var}(Z)=E[Z^2]-(E[Z])^2$ is stated as a rule for computing a variance. Rearrange it so it computes a *second moment* instead: write $E[X^2]$ in terms of $\sigma_x^2$ and $\mu_x$, and write $E[Y^2]$ in terms of $\sigma_y^2$ and $\mu_y$.
