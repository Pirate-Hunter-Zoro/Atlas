---
kind: lesson
title: chapter-4-the-six-exercises-and-4-1
---
---
kind: lesson
title: "Chapter 4: the six exercises you asked for, and the first one"
---

You asked for **4.1 and every exercise attached to §4.3**. That is six:
**4.1, 4.2, 4.3, 4.4, 4.5, 4.6**. We take them in this order, which is not
the printed one:

1. **4.1** — intermediate fields when the degree is prime. Pure tower law. Starts here.
2. **4.4** — irreducibility of $x^3+3x+1$, then inverting $\alpha$ and $1+\alpha$ by hand. The one exercise where you *compute* with a minimal polynomial instead of talking about it.
3. **4.6** — $[L:K]$ prime forces $L:K$ simple. 4.1 plus Theorem 4.4.
4. **4.5** — coprime degrees in a tower push the minimal polynomial's coefficients down into $K$.
5. **4.2** — the degree of a compositum, $[L:K] \le [K_1:K][K_2:K]$.
6. **4.3** — $\det(xI - T_\alpha)$ *is* the minimal polynomial. Hardest; last.

You are right that the minimal polynomial is the concept. Four of these six
are about it.

---

## Exercise 4.1

> Suppose that $[L:K]$ is a prime number. What fields are there intermediate
> between $L$ and $K$?

### Everything the question uses

- **Extension $L:K$**: $L$ is a field, $K$ is a subfield of it.
- **$L$ is a vector space over $K$** (Theorem 4.1): add in $L$, scale by elements of $K$.
- **Degree $[L:K]$**: the dimension of $L$ as a vector space over $K$. Finite or $\infty$.
- **Intermediate field $M$**: a field with $K \subseteq M \subseteq L$. Then both $M:K$ and $L:M$ are extensions in their own right.
- **Tower law (Theorem 4.2)**: for $L : M : K$,
  $$[L:K] = [L:M] \cdot [M:K].$$
- **Prime**: an integer $p \ge 2$ whose only positive divisors are $1$ and $p$.
- Every degree here is a positive integer — a dimension is never $0$, since a field contains $1 \neq 0$.

The question wants a complete list, with a proof that nothing else can occur.

---

**Your move.** One concrete case. Let $[L:K] = 7$, and let $M$ be any
intermediate field, $K \subseteq M \subseteq L$.

Write down the tower law equation for this $M$, and then **list every
possible pair of values $([L:M], [M:K])$.**

Two numbers per pair, and there are not many pairs. Nothing about fields yet
— this is arithmetic.
