---
kind: lesson
title: check 10c-beta-over-alpha
---
$\beta/\alpha$ means $\beta \cdot \alpha^{-1}$. It exists because $\alpha \ne 0$. You already have the key line; you just read it the wrong way.

Your line $\beta^n (\alpha^n)^{-1} = 1$ is the whole trick. Multiplication in $\mathbb{C}$ commutes, so $\beta^n (\alpha^{-1})^n = (\beta \alpha^{-1})^n$. Your line says

$$\left(\frac{\beta}{\alpha}\right)^n = 1.$$

Stop trying to isolate $\beta$. Treat $\gamma = \beta/\alpha$ as one unknown number. The line above says $\gamma$ is a root of $x^n - 1$. Once you know which number $\gamma$ is, $\beta = \alpha\gamma$ follows for free.

You were right in the margin: $(\beta^{-1})^n = (\alpha^{-1})^n$ does not give $\beta^{-1} = \alpha^{-1}$. Equal $n$-th powers do not force equal numbers. Here $\gamma$ is exactly the leftover factor that measures the difference.

The exercise is 10(c). Let $a \in \mathbb{Q}^\times$ and let $\alpha$ be any complex root of $x^n - a$. Show the splitting field of $x^n - a$ over $\mathbb{Q}$ is $\mathbb{Q}(\alpha, \zeta_n)$. You are on the first inclusion: every root $\beta$ lies in $\mathbb{Q}(\alpha, \zeta_n)$.

What you need:
- $a \in \mathbb{Q}^{\times}$ means $a$ is a nonzero rational.
- $\alpha^n = a$ and $\beta^n = a$, so $\alpha \ne 0$.
- $\gamma = \beta/\alpha$ satisfies $\gamma^n = 1$.
- $\zeta_n = e^{2\pi i/n}$. Its powers $1, \zeta_n, \dots, \zeta_n^{n-1}$ are $n$ distinct roots of $x^n - 1$.
- A nonzero polynomial of degree $n$ has at most $n$ roots in a field.
- A field is closed under products.

Show that $\gamma = \beta/\alpha$ equals $\zeta_n^k$ for some $k$. Then conclude $\beta = \alpha\zeta_n^k \in \mathbb{Q}(\alpha, \zeta_n)$.
