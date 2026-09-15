<!-- chapter: New direction — We need to do all the exercises in chapter 4 -->
The run is all eleven exercises of chapter 4. Order: 4.1, 4.4, 4.6, 4.5, then
4.2, 4.7-4.11, with 4.3 last. 4.1, 4.4 and 4.6 are closed.

Where they got to. 4.1: tower law, the full degree-7 pair list, and the answer
that the only intermediate fields are K and L. 4.4: they proved x^3+3x+1
irreducible over Q unaided and produced both inverses, alpha^{-1} and
(1+alpha)^{-1}, as rational combinations of 1, alpha, alpha^2. 4.6: their own
proof, correct -- pick l in L outside K, note K is strictly inside K(l), and
let their 4.1 force K(l) = L. None of that gets re-taught.

What was wrong. Nothing in the algebra this session. The one recurring habit is
the unwritten justifying line: on 4.6 they asserted K strictly inside K(alpha)
without saying alpha is in one and not the other. Supply those lines yourself,
do not re-pose them. The old structural fault -- reaching for contradiction
where none is needed -- is gone. Do not re-teach it.

Next thing to teach, and the trap in it. EXERCISE 4.5 AS PRINTED IS FALSE.
Take K = Q, L = Q(2^{1/3}), alpha = 2^{1/6}: then [L(alpha):L] = 2 and
[L:K] = 3 are coprime, but the minimal polynomial x^2 - 2^{1/3} has a
coefficient outside Q. Card 0013 is open and has them compute exactly that
tower, without being told why. When they report it, confirm the statement is
broken, repair the hypothesis to gcd([K(alpha):K], [L:K]) = 1, and have them
prove the repaired version: n divides d[L:K], coprimality gives n divides d,
and d <= n because m_L divides m_K, so d = n and m_L = m_K. Then 4.2.

How this student works. Algebra and arithmetic are reliable; the gaps are
structural. They skip any warm-up they judge beneath the real exercise, so run
those inside the next card instead of asking. They copy the exercise out at the
top of the page, and that is not a question.

Tooling: `board write <kind> <slug>` creates the card and its front matter.
