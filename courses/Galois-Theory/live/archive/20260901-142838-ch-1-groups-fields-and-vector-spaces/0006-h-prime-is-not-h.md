---
kind: note
title: No — and it is a name collision, one letter wide
---

You asked whether $x \in gH$ forces $g^{-1} = e$. **No.** But the question is a good one,
because the place it comes from is a single reused letter.

$x \in gH$ says: $x = g \circ h'$ for **some** $h'$ in $H$. Whatever element $gH$ happens
to supply. It is **not** the $h$ you started with — you fixed $h$ before you ever looked
at $gH$, and $gH$ has never heard of it.

Write both as $h$ and you get
$$g \circ h \circ g^{-1} = g \circ h,$$
cancel $g$ on the left, cancel $h$ on the right, and out drops $g^{-1} = e$. That is where
your answer came from, and you can tell it is too strong: $g^{-1} = e$ says $g = e$, and
$e \in H$, so you would have contradicted $g \notin H$ — but only for that one $h$. It
proves nothing, because the equation you started from was never given to you.

So keep them apart. What you actually have is
$$g \circ h \circ g^{-1} = g \circ h', \qquad h, h' \in H,$$
and no reason on earth for $h$ and $h'$ to be the same element.

---

**Your move.** Same line, correct names.

> From $g \circ h \circ g^{-1} = g \circ h'$, cancel the $g$ on the left. Then rearrange
> until $g^{-1}$ is alone on one side. **What is sitting on the other side, and which of
> $H$, $gH$ does it belong to?**
