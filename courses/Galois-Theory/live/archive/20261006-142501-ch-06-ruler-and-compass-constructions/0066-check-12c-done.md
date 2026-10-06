---
kind: lesson
title: check 12c-done
---
**$g(x) = x^{p^m} - x$ is nonzero because its $x^{p^m}$ coefficient is $1$.** A polynomial is the zero polynomial only when every coefficient is $0$. Since $p^m \geq p \geq 2$, the terms $x^{p^m}$ and $-x$ have different degrees. Nothing cancels the leading $1$. So $g$ is nonzero, of degree exactly $p^m$.

The doubt is natural, because under your assumption $g(a) = 0$ for every $a \in E$. That makes $g$ the zero *function* on $E$. It does not make it the zero *polynomial*. Over a finite field the two differ: $x^q - x$ itself vanishes at every point of $E$, and it is plainly not the zero polynomial. The root bound is a statement about the polynomial, so it applies.

**The rest of your argument is right, and 12(c) is done.** The root bound allows $g$ at most $p^m$ roots in $E$. Your assumption gives it $q = p^n$ roots. Since $m < n$, $p^m < p^n$, a contradiction. So no $\varphi^m$ with $1 \leq m < n$ is the identity, while $\varphi^n$ is. The order of $\varphi$ is exactly $n$.

I am transcribing 12(c) into the write-up and compiling it now. That is the last problem on the worksheet.

**What next: a read-through of the compiled worksheet, or a new set?**
