---
kind: lesson
title: check coefficient-ring
---
Closer, but not yet: your polynomial has coefficients in $K$, and they have to be in $F$. No question on the page, so this is grading only.

Writing $x=f(\alpha_1,\dots,\alpha_n)$ was the right move. The trouble is the phrase $f\in K[\dots]$. Your chain needs $\sigma(c_i)=c_i$ for every coefficient. An automorphism in $\operatorname{Aut}(K/F)$ only promises that for $c_i\in F$. If the $c_i$ may be anything in $K$, the claim "every $x$ is a polynomial" becomes empty: take $f$ to be the constant $x$ itself.

One check, with $F=\mathbb{Q}$, $K=\mathbb{Q}(i)$, and $\sigma$ complex conjugation.

- $\sigma(a+bi)=a-bi$ for $a,b\in\mathbb{Q}$. It fixes $\mathbb{Q}$ and nothing else.
- The constant polynomial $f=i$ lies in $K[t]$, and $f(i)=i$.
- Your step "$\sigma$ fixes the coefficients" would give $\sigma(f(i))=f(\sigma(i))$.

Your move: compute both sides, $\sigma(f(i))$ and $f(\sigma(i))$, for that constant $f=i$. Do they agree? Then say in one line which ring the coefficients of $f$ must come from so the step is honest.
