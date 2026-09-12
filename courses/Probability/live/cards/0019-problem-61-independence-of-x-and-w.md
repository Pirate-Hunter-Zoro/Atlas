---
kind: question
title: problem-61-independence-of-x-and-w
---
**(d) is right, and one symbol is missing from it.**

You skipped the factorization and went at it by substitution instead. The substitution is fine — $u = -(x+w)\lambda$, $du = -\lambda\,dx$, flipping the limits to kill the minus sign — and every move you made with it is legitimate. One slip, in the limits:

$$u = -(x+w)\lambda,\qquad x = 0 \;\Longrightarrow\; u = -(0+w)\lambda = -\lambda w \quad\textbf{— not } -w.$$

The $\lambda$ multiplies the *whole* bracket, so it rides along into the limit. Carry it through and the answer is

$$f_W(w) = \lambda e^{-\lambda w}, \qquad w > 0,$$

not $\lambda e^{-w}$. A density has to integrate to $1$ over its range; yours integrates to $\lambda$. That check catches exactly this kind of dropped constant, and it costs one line.

Everything else on the page stands. Problem 61 is finished.

---

**Now look at what you have.** All four parts, side by side:

$$f_X(x) = \lambda e^{-\lambda x}\ (x>0), \qquad f_W(w) = \lambda e^{-\lambda w}\ (w>0), \qquad f_{X,W}(x,w) = \lambda^2 e^{-\lambda(x+w)}\ (x>0,\ w>0).$$

**Exercise (Ross, Ch. 2, Problem 61 — the payoff).**
Decide whether the working time $X$ and the repair time $W$ are **independent**, and say what makes you sure.

*Definitions / symbols used*
- **Independence, continuous case.** $X$ and $W$ are independent exactly when $f_{X,W}(x,w) = f_X(x)\,f_W(w)$ **for every** $x$ and $w$.
- That "for every" includes the region. The factorization must hold on the whole set where the joint density lives, and the region itself must be a rectangle in $(x,w)$ — if the allowed values of $w$ depended on $x$, knowing $x$ would tell you something about $w$ and no factorization could save it.
- **Law of exponents.** $e^{a+b} = e^a e^b$.
- $\lambda$: a fixed positive constant.
- Contrast, for free: $X$ and $Y = X + W$ are **not** independent, since $f_{X,Y}$ lives on $0 < x < y$, where the upper variable is fenced in by the lower one.

---

**Your turn. Two lines.**

1. Multiply $f_X(x)\,f_W(w)$ out and say whether it equals $f_{X,W}(x,w)$.
2. Check the region: is the set $\{x > 0,\ w > 0\}$ a rectangle, or does one variable's range depend on the other's value?

Then state the verdict.
