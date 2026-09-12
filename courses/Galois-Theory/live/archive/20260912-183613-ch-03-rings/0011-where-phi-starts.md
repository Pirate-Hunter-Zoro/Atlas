---
kind: note
title: Mostly right. The arrow starts in the wrong place.
---

Asked and answered, item by item.

**The sorting: all three correct.** $4x_1^3 - x_1x_2 + 2$ in both, $\tfrac13x_2 + 5$ only in $\mathbb{Q}(x_1,x_2)$, $1/(x_1+x_2)$ only in $\mathbb{Q}(x_1,x_2)$. Nothing to fix.

**$a, b \in F[x_1,\ldots,x_n]$: right.** Add the one condition you left off — $b \neq 0$, or there is no fraction.

**"$R^n \to R$ with coefficients in $R$": not right.** A polynomial is a *formal expression* — a finite list of coefficients attached to monomials. It *gives* you a function on $R^n$, but it is not that function, and the two are genuinely different objects: over $\mathbb{F}_2$, $x^2$ and $x$ take the same value at every point and are still different polynomials. You proved 3.1 about a ring of functions; $R[x_1,\ldots,x_n]$ is not one.

**And now the thing your bubble is really asking about.** Look at where your $\phi$ starts:

$$\phi : R[x_1,\ldots,x_n] \longrightarrow F(x_1,\ldots,x_n).$$

3.2 does not ask you to identify $R[x_1,\ldots,x_n]$ with $F(x_1,\ldots,x_n)$. It asks you to identify **the field of fractions of** $R[x_1,\ldots,x_n]$ with $F(x_1,\ldots,x_n)$. Those are not the same object, and no map from the left-hand set as you have written it can be an isomorphism onto the right.

**Your move.** Take $R = \mathbb{Z}$ and $n = 2$, so the right-hand side is $\mathbb{Q}(x_1,x_2)$.

Does $x_1$ have a multiplicative inverse in $\mathbb{Z}[x_1,x_2]$? Does it have one in $\mathbb{Q}(x_1,x_2)$? Then write down what the domain of $\phi$ has to be.
