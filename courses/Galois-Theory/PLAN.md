# Plan

Garling's Chapter 4 exercises come first. The worksheet follows them.

## Book exercises, Chapter 4

Nothing open. The book work is done.

**4.2 is out.** It was skipped and it stays skipped. `board hw status` will keep
listing it as the one thing left in `ch04`, because the tool cannot tell a
problem that was refused from one that has not been reached. It was refused.

Closed, and never re-taught: **4.1, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9, 4.10,
4.11**. 4.5 as printed is false, and the student's counterexample is the answer:
it is typeset in the 04.5 solution region, with the repaired hypothesis in the
remark under it.

## Then the worksheet

"Field Extensions and the Ring $F[x]$", six problems, sent as photographs and
read. Both pages are `live/inbox/uploads/20260915-1515*.png`; nothing else in the
repository carries the statements. Remaining order: **3(c)**, then **1**, **5**,
**2**, **4**.

Problem 6 is closed --- all three parts agreed, transcribed and built --- and so
is **3(a)**. Part **3(b)** is exercise 4.6, already proved in `ch04`, so it is
not re-posed; its region points there. **3(c)** is open and posed in full on card
0061: show $\sqrt2 \notin \mathbb{Q}(\sqrt[3]{2})$.

## Write-up

Two files, and `board hw list` names both:

- `chapters/ch04-field-extensions/homework/ch04-homework.tex` --- the book
  exercises.
- `homework/worksheet-field-extensions/worksheet-field-extensions.tex` --- the
  worksheet. `board hw use worksheet-field-extensions` pins a sitting to it.

A solution region stays empty until an answer is agreed correct; then the
student's own argument is typeset into its region, in their steps and their
order, and the page is filed beside the `.tex` with `board hw file <label>`.
`board hw build` compiles the set and `board hw status` reports it, reading the
`% ===== SOLUTION <label> =====` markers: **one problem environment per lettered
part, each with its own matched opener and closer**, or the report is wrong.
