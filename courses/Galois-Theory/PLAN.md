# Plan

Chapter 6, *Ruler-and-compass constructions*. Four book exercises: **6.2, 6.5,
6.6, 6.7**. Nothing else in Chapter 6 is assigned. 6.1 and 6.3 are drawing
recipes with no field theory in them; 6.4 follows from 6.2 in two lines. None
of the three is taught or transcribed.

## Order of work

Taught in this order, which is not the book's. The write-up is in the book's
order regardless.

1. **6.5** --- $(2^{1/3},0)$ is not constructible. Theorem 6.1 applied
   directly: $x^{3}-2$ is Eisenstein at $2$, so $[\mathbb{Q}(2^{1/3}):\mathbb{Q}]=3$,
   which is not a power of $2$. The warm-up, and the whole method in one page.
2. **6.6** --- no regular nonagon, no regular heptagon. (a) is the trisection
   argument of Section 6.2 reused: the nonagon gives $\cos(\pi/9)$, of degree
   $3$. (b) needs the degree of $\cos(2\pi/7)$, which is $3$ as well.
3. **6.2** --- given $(\ell,0)$ constructible, construct $(\sqrt{\ell},0)$ and
   $(\ell^{2},0)$. The converse direction: the semicircle-and-altitude picture
   for the square root, similar triangles for the square.
4. **6.7** --- $[\mathbb{Q}(x,y):\mathbb{Q}]=2$ forces $(x,y)$ constructible,
   then the induction up a tower of quadratic steps. Last, and it runs on 6.2.

## Write-up

One file:
`chapters/ch06-ruler-and-compass-constructions/homework/ch06-homework.tex`.
`board hw use ch06` pins a sitting to it. All four statements are transcribed
with empty solution regions, labelled `06.2`, `06.5`, `06.6`, `06.7` in book
order; the file builds to 1 page with 0 warnings.

A solution region is filled in the same turn the answer is agreed, not at the
end of the sitting. The student's own argument goes in, in their steps.
`board hw file <label>` puts the handwriting beside it and `board hw build`
compiles the set. `board hw status` reads the `% ===== SOLUTION <label> =====`
markers: one problem environment per label, each opener matched by its closer,
or the report is wrong.

## What is closed

Chapter 5 is not this chapter's business. The field-extensions worksheet under
`homework/worksheet-field-extensions/` is a separate set and is not in scope.
