---
kind: correct
title: $k_{1} \in S$ by lemma B, and minimality of $m$ does the rest. 3.17 is closed.
---

**Both lines land.** You wrote

> Note $k_{1} \in S$, since $y \in I$, so $u^{-1}y = p^{k_{1}} \in I$.

That is lemma B used exactly where it was needed: $u$ is a unit, so $u^{-1}$
lies in $R$, and absorption drags $p^{k_{1}}$ into $I$. That is the membership
condition of $S$, so $k_{1} \in S$. And "$k_{1} \geq m$ through definition of
$m$" is now the right reason — $m$ is the *least* member of $S$, and $k_{1}$
is a member. Well-ordering has been retired to where it belongs.

So $I = (p^{m})$, and with $I = \{0\} = (0)$ disposed of at the top of your
page, every ideal of $R$ is principal. **Exercise 3.17 is finished, all three
parts.** I am writing it up.

(Pen, mine, no redo: the quantifier in $I = \{rx \mid x \in R\}$ is still $r$,
and "since $I$ is an ideal" is **absorption**. Both get fixed in the file.)

---

**Exercise 3.8** — the last quarter of it, which is still owed.

Let $K$ be a field. For $f = a_{0} + a_{1}x + \cdots + a_{n}x^{n} \in K[x]$
and $k \in K$, define

$$(\Phi(f))(k) = a_{0} + a_{1}k + \cdots + a_{n}k^{n}.$$

You have already shown $\Phi$ is a ring homomorphism from $K[x]$ to $K^{K}$,
and that **when $K$ is finite** it is an epimorphism but not a monomorphism.

**What happens if $K$ is infinite?**

**Recall.**

- $K^{K}$: the ring of *all* functions from $K$ to $K$, added and multiplied pointwise. Its zero is the function that is $0$ at every point of $K$.
- $\Phi$ sends a polynomial to the function it computes. $\Phi(f)$ is the zero of $K^{K}$ exactly when $f(k) = 0$ for **every** $k \in K$.
- *Monomorphism:* an injective homomorphism. For a ring homomorphism this is the same as $\ker \Phi = \{0\}$, i.e. only the zero polynomial maps to the zero function.
- *Epimorphism:* a surjective homomorphism — every function $K \to K$ is $\Phi(f)$ for some polynomial $f$.
- *Careful:* the zero **polynomial** (all coefficients $0$) and the zero **function** are different objects living in different rings. Failure of injectivity means a nonzero polynomial hitting the zero function.
- *Your 3.15 (cards 0116–0119):* if $K$ is a field and $f \in K[x]$ is nonzero of degree $n$, then $f$ has at most $n$ roots in $K$.

---

**Your move.** One concrete instance first, since the finite case turned on one.

Over $K = \mathbb{Z}_{3}$, the polynomial $x^{3} - x$ is nonzero but
$\Phi(x^{3} - x)$ is the zero function — that is what broke injectivity there.

**Now take $K = \mathbb{Q}$. List the roots of $x^{3} - x$ in $\mathbb{Q}$, and
say whether $\Phi(x^{3} - x)$ is the zero function of $\mathbb{Q}^{\mathbb{Q}}$.**
