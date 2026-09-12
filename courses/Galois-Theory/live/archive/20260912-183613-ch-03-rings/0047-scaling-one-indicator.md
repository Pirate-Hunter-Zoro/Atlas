---
kind: note
title: That is the same page with a box drawn on it. One smaller step, then.
---

The page that came back is your $\delta$ working from before, with a box now
around $\delta(x) = 2(x-1)(x-2)$. Nothing new below it. That line is right and
it is already settled — card 0046 said so. So take a smaller step toward the
$f$ I asked for.

The three indicators, so you do not have to scroll:

| | polynomial | at $0$ | at $1$ | at $2$ |
|---|---|---|---|---|
| $\delta_{0}$ | $2(x-1)(x-2)$ | $1$ | $0$ | $0$ |
| $\delta_{1}$ | $2x(x-2)$ | $0$ | $1$ | $0$ |
| $\delta_{2}$ | $2x(x-1)$ | $0$ | $0$ | $1$ |

Everything is in $\Fq{3}$, so arithmetic is mod $3$.

---

**Your move.** One polynomial, three numbers. Let
$$g(x) = 2\,\delta_{0}(x) + \delta_{2}(x).$$

Compute $g(0)$, $g(1)$, $g(2)$, reading each $\delta$'s value off the table
above — do not multiply the brackets out.
