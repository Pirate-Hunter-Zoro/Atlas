# HANDOFF

2026-08-28, ~18:45. Garling §1.1, lecture. Chosen set: **1.3**, then **1.7**, then **1.5**.

## Where they got to

**Exercise 1.3 (index 2 ⟹ normal): one line short, still.** At revision 10 they abandoned
patching and **rewrote the whole proof clean** on page 2 — the first time this session they have
not merely appended. The rewrite is correct end to end: fix a disjoint coset $gH$, so $g \notin
H$; take $h \in H$, set $x = ghg^{-1}$; suppose $x \in gH$, cancel to $g^{-1} = h^{-1}h_1 \in H$,
so $g \in H$, contradiction; therefore $x \notin gH$, hence $x \in H$ because $H$ and $gH$
partition $G$. All theirs, all correct, and it has been told to them as settled — do not raise
any of it again.

They also erased the *"Are you ready for me to hit save?"* question from page 2, so there is no
outstanding question of theirs on the page. Page 1 is stale ink from an earlier attempt
(including *"If $gHg^{-1}=H$, we're done"*, which they asked me to axe in the write-up).

## Next thing to teach — and it is the only thing

**Element to set — third attempt at the same missing line.** Their last line reads *"So
$x = ghg^{-1} \in H$ and $H$ is normal."* The first clause is proved; *"and $H$ is normal"* is
not, because it quantifies over all of $H$ and everything above it is about one $x$. Card 0011
tried *"which element of $H$ is $h$?"* and did not land — they answered it by rewriting the proof
rather than by adding the line. Card **0012** changes the form again: it expands
$gHg^{-1} = \{ghg^{-1} : h \in H\}$ for them and asks them to copy out
"$gHg^{-1}$ ___ $H$" and fill in one symbol (⊆). Resume by reading their answer to that.

If a third form also fails, do not re-ask a fourth time — teach the quantifier move on a smaller
instance (fix $G = S_3$, $H = A_3$, one $g$, run all three $h$) and let them see the set fill up.

Then one leftover, promised twice and still not named to them: their opening fixes $g \notin H$,
so the case $g \in H$ (where $gHg^{-1} = H$) is untreated. A sentence, not a proof.

When both land, 1.3 is done. The sitting is bound to `ch01`: transcribe into the solution region
that turn — **omitting** *"If $gHg^{-1}=H$, we're done"*, which they asked me to axe — then
`board hw build`, then 1.7.

## Right — do not re-teach

Coset partition at index 2 and that it is what the hypothesis buys; $gHg^{-1}$ is a subgroup;
$gH = H$ iff $g \in H$; both conjugation forms are one condition; the cancellation; and now the
entire page-2 rewrite through the partition step.

## Wrong, and what it actually was

They read "contradiction reached" as "proof finished" — twice the page stopped at the bolt
without discharging the supposition. That is fixed. The live misunderstanding is narrower and
older: they do not see that a proof about an arbitrary element *is* a proof about the set, so
"$H$ is normal" gets asserted directly off an element statement with no set line between.
Untaught and may bite in 1.7: card 0001's fact list uses right cosets $H \circ g$ while every
later card uses $gH$.

## How this student works

**They patch exactly the character or sentence you name and nothing adjacent** (revision 9 was
one stroke), so a request repeated in the same words will not land — change the *form* of the
challenge each time into something whose answer *is* the missing line (a fill-in-the-blank beat a
re-ask twice now). **Revision 10 broke the append habit** — they will rewrite cleanly when the
page gets cluttered, so do not assume stale ink is current; read the bottom-most block and watch
the stroke count (`live/turns.jsonl` carries it per revision — 325 → 439 was a full rewrite, not
an addition). Pages are sparse; five lines can hold a whole proof, and page 1 is often dead.
Questions get written on the page — answer as `note`, never `wrong`. A lightning bolt means
*contradiction*.

Board `http://127.0.0.1:8787/`; iPad `https://board.tail0c6c62.ts.net/`. `board recap` = the
lesson. Verify via `/board.json`. Python `urllib` does not prompt; `curl` and `&&` do. No `$…$`
in card titles. Revisions 7–10 filed in `chapters/ch01-.../handwritten/` as
`ex1.3-element-step-attempt3…6.png`.
