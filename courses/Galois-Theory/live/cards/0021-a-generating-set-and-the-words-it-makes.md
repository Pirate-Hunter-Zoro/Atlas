---
kind: lesson
title: A generating set, and the words it makes
---
No — and the difference is the whole point of the notation. Two symbols $h$ and $g$ are sitting in your hand, and you are allowed to combine them in **any finite product**, in any order, using each one as many times as you like. The phrase "over and over" is too narrow: it picks out one word — $g, h, g^2, hg, hgh, \dots$ — and only in the pattern $g$ first.

The set $\langle h, g\rangle$ is every finite string of $h$'s and $g$'s, multiplied out, subject only to the relations that hold in $\Symn{3}$. Two strings can land on the same element — that is the interesting part, not a nuisance.

Let me name the shapes a string can take.

- $h$ alone: powers of $h$ give just $\{e, h\}$ since $h^2 = e$.
- $g$ alone: powers of $g$ give $\{e, g, g^2\}$ since $g^3 = e$.
- Mixed: words with both letters, like $gh$, $hg$, $ghg$, $hgh$, $\dots$

In a group of order six there is only so much room. The three transpositions $\{e, (1\,2), (1\,3), (2\,3)\}$ already use four elements, and the three-cycles $\{e, (1\,2\,3), (1\,3\,2)\}$ use three. They overlap at $e$ only. So six elements is the **ceiling**, and you either hit it or you don't.

**Your move:** write down, in braces, the elements of $\langle h, g\rangle$ where $h = (1\,2)$ and $g = (1\,2\,3)$. You already have $e$, $h$, $g$, $g^2 = hgh$, $gh$, $hg$ in your pocket from earlier cards — combine them and tell me how many you get.
