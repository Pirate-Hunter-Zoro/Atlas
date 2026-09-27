---
kind: question
title: hw02-complete-what-next
---
Your question on the page answers itself, and you answered it: $\Var(Y)/\varepsilon^2 = \sigma^2/(n\varepsilon^2)$, which goes to $0$ as $n\to\infty$ for every fixed $\varepsilon>0$. That is 76, finished, in one pass. $\E[\bar{X}_n]=\mu$ by linearity; $\Var(\bar{X}_n)=\sigma^2/n$ because the constant $1/n$ comes out squared and independence lets the $n$ variances add; Chebyshev at $k=\varepsilon$ then bounds the probability by $\sigma^2/(n\varepsilon^2)$.

One seam I closed in the write-up rather than handing it back. You stated Chebyshev with $\ge k$, and the problem asks about the strict event $|\bar{X}_n-\mu| > \varepsilon$. That strict event sits inside the non-strict one, so the bound carries to it --- and a probability cannot drop below $0$, so the left side is squeezed rather than merely bounded above. Both lines are in the file now.

**Homework 2 is complete.** All nine handed-in problems --- 1, 2, 9, 12, 22, 37, 61, 76, 86 --- now have the statement and your own argument typeset in `homework/hw02/hw02.tex`, your page is filed as `handwritten/hw02-p76-wlln-chebyshev.png`, and the document builds clean at 7 pages. You did 86 on the 12th, with three pages filed for it, so I am not putting it back in front of you.

The starred problems, $\ast 16$ and $\ast 49$, are in the back of the book and are not handed in. The sheet is done.

So the next question is yours rather than mine. Close the sitting here, or start something else --- and if something else, what? The next homework sheet is not in this repository, so if there is one, tell me where the file is.
