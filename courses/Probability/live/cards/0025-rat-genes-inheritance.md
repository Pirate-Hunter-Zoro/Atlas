---
kind: lesson
title: The rats — what "dominates" means, before any probability
---

Ross 41 is a conditioning problem wearing a biology costume. The probability is
the part you already have; the costume has to be unpacked first, and it is three
facts.

**One.** Every rat carries exactly **two** colour genes, one inherited from each
parent. Write $B$ for the black gene and $b$ for the brown one, so a rat is
$BB$, $Bb$ or $bb$.

**Two.** A parent passes on **one** of its two genes, chosen with probability
$1/2$ each, and the two parents choose independently.

**Three.** Black *dominates* brown: the rat is black if it carries at least one
$B$. So $BB$ and $Bb$ are both black — indistinguishable by eye — and only $bb$
is brown. That is what makes the problem a problem: you can see the coat, you
cannot see the pair.

**A cross, worked.** Mate a $BB$ with a $Bb$. The first parent has only $B$ to
give. The second gives $B$ or $b$, each with probability $1/2$. So the offspring
is

| from parent 1 | from parent 2 | pair | coat |
|---|---|---|---|
| $B$ | $B$ | $BB$ | black |
| $B$ | $b$ | $Bb$ | black |

each with probability $1/2$. Every offspring of that pairing is black, and half
of them carry a brown gene invisibly.

The four outcomes of a cross are equally likely because the two parents' choices
are independent and each is a fair coin. That is the only probability fact the
setup needs.
