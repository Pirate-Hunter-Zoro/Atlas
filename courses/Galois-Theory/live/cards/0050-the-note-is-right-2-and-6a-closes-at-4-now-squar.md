---
kind: lesson
title: the-note-is-right-2-and-6a-closes-at-4-now-square-it-again
---
**Yes --- $[\mathbb{Q}(\sqrt{2}):\mathbb{Q}] = 2$, and your own reason is the
right one.** Your page asks it with a question mark and then answers it: the
basis is $\{1, \sqrt{2}\}$, two elements, so the dimension is $2$. Nothing else
is needed there.

The rest lands too. $[K:\mathbb{Q}(\sqrt{2})] = 2$ with basis
$\{1, \sqrt{3}\}$, ruling out $1$ because $\sqrt{3} \notin \mathbb{Q}(\sqrt{2})$,
and the tower law gives $2 \cdot 2 = 4$. **6(a) is closed.** It is written up
now, statement and your argument, with your page filed beside it.

One correction I made in the write-up rather than leaving to you. Your two
branches read "since $b \in \mathbb{Q}$" and "since $a \in \mathbb{Q}$"; those
are the hypothesis, not the contradiction. The file says $\sqrt{6}$ is
irrational in the first branch and $\sqrt{3}$ is irrational in the second.

**Problem 6(b).** Let $K = \mathbb{Q}(\sqrt{2},\sqrt{3})$ and
$\gamma = \sqrt{2} + \sqrt{3}$. Show that $K = \mathbb{Q}(\gamma)$, and compute
$m_{\gamma,\mathbb{Q}}$.

What this uses:

- $\mathbb{Q}(\gamma)$ --- the smallest subfield of $\mathbb{C}$ containing $\mathbb{Q}$ and $\gamma$.
- $m_{\gamma,\mathbb{Q}}$ --- the monic rational polynomial of least degree with $\gamma$ as a root.
- $\deg m_{\gamma,\mathbb{Q}} = [\mathbb{Q}(\gamma):\mathbb{Q}]$ --- the degree of the minimal polynomial is the degree of the extension it generates.
- $[K:\mathbb{Q}] = 4$ --- what you just proved.
- a subfield of $K$ containing $\mathbb{Q}$ with the same degree over $\mathbb{Q}$ as $K$ is all of $K$ --- equal finite dimension forces equality.
- $\gamma^2 = 5 + 2\sqrt{6}$ --- you computed this two cards ago.

**Your move, one line of arithmetic only.** Take $\gamma^2 = 5 + 2\sqrt{6}$, move
the $5$ to the left, and square both sides. Write down the resulting equation
with every term on one side, and tell me its degree in $\gamma$.
