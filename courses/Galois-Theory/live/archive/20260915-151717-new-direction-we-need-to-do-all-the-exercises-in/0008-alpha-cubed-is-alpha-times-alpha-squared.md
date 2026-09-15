---
kind: lesson
title: alpha-cubed-is-alpha-times-alpha-squared
---
One exponent went missing, and it changed the answer. Pulling $\alpha$ out of
$\alpha^3 + 3\alpha$ leaves $\alpha(\alpha^2 + 3)$, not $\alpha(\alpha + 3)$,
because $\alpha^3$ is $\alpha$ times $\alpha^2$. So the bracket you divided by
was the wrong element, and $-1 \cdot \alpha - 3 \cdot 1$ is not $\alpha^{-1}$.

Everything else on the page holds. The rearrangement to $-1 = \alpha^3 + 3\alpha$
is right, spotting that $\alpha$ is a common factor is the right move, and the
coefficients you underlined are indeed the rational numbers the exercise wants.

**Exercise 4.4, still the same half.** *Suppose that $\alpha$ is a root of
$x^3 + 3x + 1$ in $\mathbb{C}$. Express $\alpha^{-1}$ as a linear combination,
with rational coefficients, of $1$, $\alpha$ and $\alpha^2$.*

Everything it uses:

- **$\alpha$ is a root** — it means $\alpha^3 + 3\alpha + 1 = 0$, and this is the only fact about $\alpha$ you have.
- **$\mathbb{Q}(\alpha)$** — the smallest subfield of $\mathbb{C}$ containing $\mathbb{Q}$ and $\alpha$; every element of it is $a + b\alpha + c\alpha^2$ with $a$, $b$, $c$ rational.
- **$\alpha^{-1}$** — the element with $\alpha \cdot \alpha^{-1} = 1$. It exists because $\alpha \neq 0$: putting $0$ into $x^3 + 3x + 1$ gives $1$.
- **Linear combination of $1$, $\alpha$, $\alpha^2$ over $\mathbb{Q}$** — a sum $a \cdot 1 + b\alpha + c\alpha^2$ and nothing else, with no $\alpha$ left in a denominator.
- **Reducing with the cubic** — the root condition rewritten as $\alpha^3 = -3\alpha - 1$. Any $\alpha^3$ that appears can be replaced by that, which is how a cubic or higher expression collapses back to the three-term form.

**Your move.** Redo the last line with the corrected factorisation and write down
$\alpha^{-1}$. Then check it yourself: multiply $\alpha$ by the answer you got,
replace the $\alpha^3$ that appears using $\alpha^3 = -3\alpha - 1$, and report
what the product comes to. If it is not $1$, the answer is wrong and the check
has told you so. That multiply-and-reduce check is the thing that would have
caught the lost power, and it is the same move the harder half of 4.4 needs.
