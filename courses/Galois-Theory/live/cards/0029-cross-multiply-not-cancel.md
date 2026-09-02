---
kind: note
title: Yes — and it never uses cancellation.
---

Your question first. **Yes, $d\alpha$ has all its coefficients in the image of $R$**, and the suspicion is worth having — but nothing in this step uses cancellation.

Watch one coefficient. Write $d = bc$, where $b$ is the denominator of the coefficient $a/b$ and $c$ is the product of all the other denominators. Then

$$d \cdot \frac{a}{b} \;=\; \frac{d}{1}\cdot\frac{a}{b} \;=\; \frac{bca}{b}.$$

Whether that equals $\dfrac{ca}{1}$ is not a question of cancelling $b$ from top and bottom — you are right that you have no such licence in a general $R$. It is a question of the *defining relation* of $\operatorname{Frac}(R)$: $p/q = p'/q'$ exactly when $pq' = p'q$. You are not permitted to cancel; you are permitted to cross-multiply, and cross-multiplying is the only thing this argument ever needed. It is the same move you made on $\dfrac{\tfrac12 x + 1}{x} = \dfrac{x+2}{2x}$ hours ago.

One correction to your setup, and it is the other half of the same worry: **$R$ is not an arbitrary ring.** It is an integral domain. Without that, $\operatorname{Frac}(R)$ does not exist to write down, and $d$ — a product of non-zero denominators — could be $0$.

**Your move.** Let $R$ be an integral domain and $a, b, c \in R$ with $b \neq 0$, $c \neq 0$. Show that

$$\frac{bca}{b} \;=\; \frac{ca}{1}$$

holds in $F = \operatorname{Frac}(R)$: write out the cross-multiplication the definition demands, and say why the two sides are equal.
