---
kind: question
title: worksheet-open-7a
---
Yes --- chapter 6 is dropped, and card 0001 with it. Do not answer the $2^{1/3}$ question. We are on the worksheet you uploaded, *Automorphisms, Irreducibility and Splitting Fields*, problems 7--12.

Four of them this sitting: **7**, then **8**, then **9**, then **10**. They are one chain. Problem 7 says an automorphism sends a root of $f$ to another root of $f$. Problem 8 turns that into a count, by proving the cyclotomic polynomial $\Phi_p$ irreducible. Problems 9 and 10 run the whole machine on $x^4+1$ and on $x^3-2$. Left out: 11 and 12, which are finite fields and use none of the four.

**Problem 7(a).** Let $K/F$ be a field extension and let $\sigma \in \operatorname{Aut}(K/F)$. Show that if $f \in F[x]$ and $f(\alpha)=0$ for some $\alpha \in K$, then $f(\sigma(\alpha))=0$.

You are not answering that yet. Everything it uses, first:

- **$K/F$** --- shorthand for: $F$ is a subfield of $K$.
- **$F[x]$** --- the polynomials in $x$ whose coefficients all lie in $F$.
- **Field automorphism $\sigma$ of $K$** --- a bijection of $K$ with itself satisfying $\sigma(a+b)=\sigma(a)+\sigma(b)$ and $\sigma(ab)=\sigma(a)\sigma(b)$.
- **$\operatorname{Aut}(K/F)$** --- those automorphisms of $K$ that also fix $F$ pointwise.
- **Fixes $F$ pointwise** --- $\sigma(c)=c$ for every single element $c$ of $F$, not merely $\sigma(F)=F$.

Here is the one rung. Take $F=\mathbb{Q}(\sqrt{2})$, let $\alpha$ be a real number with $\alpha^{2}=\sqrt{2}$, let $K=F(\alpha)$, and let $f(x)=x^{2}-\sqrt{2}$, which lies in $F[x]$ and has $\alpha$ as a root. Let $\sigma \in \operatorname{Aut}(K/F)$. Three equalities:

$$\text{(i)}\ \ \sigma(\alpha^{2})=\sigma(\alpha)^{2} \qquad \text{(ii)}\ \ \sigma(\sqrt{2})=\sqrt{2} \qquad \text{(iii)}\ \ \sigma(\alpha^{2}-\sqrt{2})=\sigma(\alpha^{2})-\sigma(\sqrt{2})$$

Exactly one of the three needs $\sigma$ to fix $F$ pointwise; the other two hold for any field homomorphism. Which one is it?
