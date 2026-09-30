---
kind: lesson
title: check cube-root-four
---
Not yet: your first line is false. An element of $F(\alpha_1,\dots,\alpha_n)$ is not always $\sum c_i\alpha_i$. No question on the page, so this is grading only.

The rest of your chain is good. Each step is labelled, and "fixes $F$" lands on the coefficients $c_i$, where it belongs. The trouble is only the form you gave $x$. Sums $\sum c_i\alpha_i$ cover the degree-one part. They miss products like $\alpha_1\alpha_2$, powers like $\alpha_1^2$, and quotients.

One check, with $F=\mathbb{Q}$, $n=1$, $\alpha_1=\sqrt[3]{2}$, so $K=\mathbb{Q}(\sqrt[3]{2})$.

- $\sqrt[3]{4}=(\sqrt[3]{2})^2$ lies in $K$, because $K$ is closed under multiplication.
- $\{1,\sqrt[3]{2},\sqrt[3]{4}\}$ is a basis of $K$ over $\mathbb{Q}$, since $x^3-2$ is irreducible by Eisenstein at $2$.
- Your form says every $x\in K$ is $c\,\sqrt[3]{2}$ for some $c\in\mathbb{Q}$.

Your move: is there a $c\in\mathbb{Q}$ with $\sqrt[3]{4}=c\,\sqrt[3]{2}$? Say yes or no, and give the one-line reason using that basis.
