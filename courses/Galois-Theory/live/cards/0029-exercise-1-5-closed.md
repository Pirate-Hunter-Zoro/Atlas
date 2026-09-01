---
kind: correct
title: Exercise 1.5 is closed — and you did it the long way
---
All of it is right. $K = \{e, (1\,2)(3\,4)\}$, normal in $H$ because $H$ is abelian, and the witness $g = (1\,2\,3\,4)$, $k = (1\,2)(3\,4)$ gives $gkg^{-1} = (1\,4)(2\,3) \notin K$. I checked every one of your four lines, including $g^{-1} = (2\,1\,4\,3)$; they are all correct. Your margin remark is correct too — any of the three would have served, since each has order 2.

So normality does not pass through, and Exercise 1.5 is done. I am writing it into the chapter file now.

One thing, and it is about speed rather than correctness. You multiplied three permutations across four lines. Card 0028 handed you the one-line version and you did not reach for it:

$$g\,(a\,b)(c\,d)\,g^{-1} = (g a\ \, g b)(g c\ \, g d).$$

With $g = (1\,2\,3\,4)$ that reads off immediately: $1 \mapsto 2$, $2 \mapsto 3$, $3 \mapsto 4$, $4 \mapsto 1$, so $(1\,2)(3\,4) \mapsto (2\,3)(4\,1)$. Same answer, no products.

This is a habit worth breaking now. Conjugation is going to be the most-used operation in this course, and in Galois theory you will be conjugating things you *cannot* multiply out by hand. Relabel; do not compute.

*(A clerical slip, twice now: you wrote $gkg^{-1} = gg^{-1}$, dropping the $k$. Second time this has happened — it costs you nothing today and a mark eventually.)*

**Your move — one line, to make the shortcut stick.** Same $H$, same $k = (1\,2)(3\,4)$. Take $g = (2\,3)$ and read off $gkg^{-1}$ by relabelling. No products.
