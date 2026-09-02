<!-- chapter: Ch 03 — Rings -->
# HANDOFF

**Ch 03, Rings (Garling) — homework.** Assigned, student's order: **3.1, 3.2,
3.3, 3.8, 3.10, 3.11, 3.12, 3.14, 3.15, 3.17, 3.25, 3.26.** Not ours to prune.
Sheet: `handwritten/20260902-exercise-list.png`.

## Where it got to

**3.1 — closed by their decision.** Transcribed as written; the `.tex` comment
block lists what it lacks. Told once. Do not re-open unasked.

**3.2 — SKIPPED at 16:31, and 3.3 with it.** *"I have lost patience."* Seventeen
revisions on one problem did it. Skip means *not now*: both are still assigned,
both regions are still empty, and they come back **after** the rest of the sheet
— unremarked upon until then. 3.3's statement is still untranscribed.

Everything below on 3.2 is where to resume it, not what to do next.

**3.2 — seventeen revisions, the setup is done, they are inside the proof.**
Statement transcribed, solution region empty.
`handwritten/20260902-3.2-attempt{1..13}.png`.

## Right — do not re-teach

Field of fractions of $R$ and its equivalence relation; $R \hookrightarrow F$ is
injective, not surjective, and misses exactly the classes with $\gcd(a,b)=1$,
$b \neq 1$; isomorphism = homomorphism **plus** bijection, so a non-field is
never isomorphic to a field; elements of $F(\underline x)$ are *classes* of pairs
of polynomials; $x_1$ has no inverse in $\mathbb{Z}[x_1,x_2]$; and $r11$:
$(\tfrac12x+1)/x = (x+2)/(2x)$ — clearing denominators, correctly.

## Wrong, and the actual pattern

Given a constraint they cannot meet, they **weaken the statement instead of
changing their object**: $b \neq 1_R$, then $a \neq b$, then trimming the
codomain of $\phi$ to its image. Say plainly when a repair points the wrong way.
Old correct lines also drift wrong on the next revision — recheck them.

The domain of $\phi$ took five askings and then *"I don't understand."* I gave it
outright ($\operatorname{Frac}(R[x_1,\ldots,x_n])$) and they answered correctly
within three minutes. Withholding was the mistake.

## The single next thing

Card 0022 asked for the $d$ that clears an arbitrary $a/b \in \mathbb{Q}(x)$ and
**why one always exists**. r12 came back stalled: *"I don't know... all I know is
that $b^{-1}$ exists but $ab^{-1}$ need not be in $\mathbb{Z}[x]$."* The
misunderstanding is the target, not the method — they were hunting for
$ab^{-1} \in \mathbb{Z}[x]$ instead of a **different representative of the same
class**. Card 0023 said so and dropped to a concrete pair,
$a = \tfrac12x^2 + \tfrac23 x$, $b = \tfrac56 x + 3$. r13: **$d = 6$, correct**,
but justified as *"the maximal $q$ in all the $p/q$ coefficients"* — false, and
true on that example only by accident, since $\max\{2,3,6\} = \operatorname{lcm}$
there. Card 0024 handed them $a = \tfrac12 x + \tfrac13$, $b = 1$ to break it on.
r14: they did not bother computing the counterexample, they just **corrected the
rule to the lcm** — right, and settled. Do not re-teach it.

Card 0025 was the finiteness rung — an lcm is a number only over a **finite**
set, so the rule needs finitely many coefficients — asked as: write
$\tfrac12 x^2 + \tfrac23 x$ as the coefficient tuple your own margin note
describes and count the non-zero entries. They answered **2**. Settled: *all but
finitely many* entries are $0_R$, not "infinitely many may be". They were told to
fix the note; check that they did.

Card 0026 re-posed the arbitrary $a/b \in \mathbb{Q}(x)$. **They did not answer
it** — they interrupted (turn t0008) with two questions, and both were good:
*this proof is supposed to apply to arbitrary $R[x]$, $F(x)$, and the lcm
argument depends on $R = \mathbb{Z}$, $F = \mathbb{Q}$*; and *is it required that
$F[x_1,\ldots,x_n]$ has finitely many non-zero coefficients?* Filed as
`handwritten/20260902-3.2-question2.png`. They spotted the generalisation
obstacle themselves, one card before it was due — do not treat the $\mathbb{Q}$
case as still owed.

Card 0027 answers both: the least common multiple was never needed, only *a*
common multiple, and the **product** of the denominators is one in any
commutative ring — so "lcm" $\to$ "product" and $\mathbb{Z}$ drops out of the
argument; and finiteness is the *definition* of a polynomial, not a hypothesis
(without it the object is a formal power series and the ring is not closed under
multiplication). Its question — name $d \in R$ clearing two coefficients $a_1/b_1$, $a_2/b_2$ of a
polynomial in $F[x]$ — came back **$d = b_1 b_2$, correct** (r2). Card 0028 says
so, names where *integral domain* pays for itself ($b_1b_2 \neq 0$ needs no zero
divisors), and re-poses the real thing.

Card 0028 asked for surjectivity of $\phi$ in full. t0009 r1 is a **real
attempt**, and the shape of it is right: $\phi^{-1}(\alpha/\beta) = d\alpha/d\beta$
with $d = \prod b$ over the denominators of the non-zero coefficients of $\alpha$
and $\beta$. Both quantifier steps landed unprompted — product over *all*
denominators, and one $d$ for $\alpha$ and $\beta$ together.

Two things on that page:

- **Their question:** *"$d\alpha \in R[x]$? But cancellation may not work the same
  as it does in $\mathbb{Q}$."* Good question, and the answer is that the step
  never cancels — $bca/b = ca/1$ is the *defining relation* cross-multiplied,
  which needs only commutativity. Card 0029 answers it and asks them to check
  that one equality by cross-multiplication.
- **Their error:** they wrote *"$R$ is arbitrary ring."* It is an integral
  domain — without it $\operatorname{Frac}(R)$ is not there to write down and $d$
  can be $0$. **Fixed on r2.**

r2 did not do the cross-multiplication check; they asserted $d\alpha, d\beta \in
R[x]$ and asked, in a bubble, *"Is everything here right so far?"* Card 0030 is
that audit. What it says is not right: they wrote $\phi^{-1}(\alpha/\beta) =
d\alpha/d\beta$, which **presumes $\phi$ is a bijection — the thing being
proved.** They have a candidate preimage, not an inverse, and they have never
written the verification. 0030 asks for exactly that: with $\gamma =
d\alpha/d\beta$, verify $\phi(\gamma) = \alpha/\beta$ by cross-multiplication
($d\alpha \cdot \beta = \alpha \cdot d\beta$, commutativity). It also tells them
the clause $d\beta \neq 0$ belongs in the proof, with its reason.

r3: they did not answer either. They bracketed $d\alpha, d\beta \in R[x]$ and
wrote *"First, help me prove this because I'm still stuck."* Asked directly, so
give it directly — the withholding lesson from 3.2's early hours applies here
too.

**Open on card 0031.** The diagnosis it acts on: their obstacle is the *target*,
not the algebra. Inside $F$ nothing is literally "in $R$" — elements are classes
— so "$d\alpha \in R[x]$" means every coefficient equals $r/1$ for some
$r \in R$, and they had no idea that was the shape to aim for. 0031 states that,
restates the multiplication and equality rules, works the $\mathbb{Z}$ instance
($15/1 \cdot 2/3 = 30/3 = 10/1$, and $10 = 5 \cdot 2$), gives the factorisation
$d = bc$, and asks the one line: name $r$ with $bca/b = r/1$ and cross-multiply.
Expect $r = ca$, check $bca \cdot 1 = b \cdot ca$.

Still owed on 3.2 after that, in order: $\phi(\gamma) = \alpha/\beta$ for
$\gamma = d\alpha/d\beta$ (card 0030's ask, still unanswered), the $d\beta \neq 0$
clause, then injectivity of $\phi$. Then 3.2 is closed and the solution region
gets written from their own pages.

Note the pattern of the last three revisions: the page barely changes and the
question moves. They are not refusing the check — they did not know what it was
asking for. When a request is re-asked twice without an attempt, stop re-asking
and go find the missing target. On 3.2 that was found one card too late.

## Now: 3.8

**Open on card 0032.** Statement transcribed into the `.tex` and it compiles
(2 pages, no warnings). The card poses 3.8 in full — $\Phi: K[x] \to K^K$ by
evaluation, a homomorphism, an epimorphism but not a monomorphism for finite $K$,
and what happens for infinite $K$ — with $K^K$'s pointwise ring structure and
epi/mono spelled out on the card.

Its rung was meant to be a win after a bad hour: $K = \mathbb{F}_2$,
$f = x^2 + x$, give both values of $\Phi(f)$. Expect $0$ and $0$ — the zero
function — which is *already* the failure of injectivity, since $f \neq 0$ in
$\mathbb{F}_2[x]$. Point that out when they answer; they do not need a second
rung for the mono part.

t0011 r1 (`handwritten/20260902-3.8-attempt1.png`): got $(\Phi(f))(0) = 0$,
stopped, wrote **"I am so lost."** The cause is a **type confusion**, not the
arithmetic — they wrote $(\Phi(f))(0) = 0 \in K^K$, putting the *value* in the
function ring. Card 0033 separates them ($\Phi(f) \in K^K$ is the function;
$(\Phi(f))(k) \in K$ is one value), gives the two-row table for $\mathbb{F}_2$
with the top row already filled by their own correct line, states $1+1 = 0$
outright, and asks only for the bottom row.

r2 (`handwritten/20260902-3.8-attempt2.png`): **both values right**, $0$ and $0$,
with the working shown ($1\cdot1 + 1 = 1+1 = 0$). Types fixed — they now write
$\in K$. Do not re-teach either.

The predicted confusion arrived on the same page, one line up: they wrote
$\mathbb{F}_2[x] \subset K^K$. **False** — $\Phi$ is a map between the two rings,
not an inclusion, and 3.8 is entirely a measurement of how badly it fails to be
one. Card 0034 says so and turns their own table into the counterexample: name
$g \neq f$ in $\mathbb{F}_2[x]$ with $\Phi(g) = \Phi(f)$. Expect $g = 0$ (or
$g = x^2 + x + x^2 + x$-style noise; $0$ is the one to want).

That answer *is* "not a monomorphism", so when it lands, say so and go straight
to the homomorphism half — do not build a separate ladder for injectivity.
Elements of a function ring being functions is this student's live difficulty
today; it is the same shape as classes-of-pairs in 3.2, which cost most of an
hour.

Card 0012 already settled *a polynomial is not the function it gives you*. Do
not teach it again — this exercise is that fact made into a proof.

Then the *why*: $d$ exists because a polynomial has only **finitely many**
non-zero coefficients, so there are finitely many denominators to clear and a
common multiple exists. That is exactly when to fix their standing margin note
calling a polynomial a "countably infinite tuple, infinitely many of which may be
$0_R$" — it has a "(?)" pencilled beside it, so they already doubt it. It is
backwards: *all but finitely many* are $0_R$. Finiteness is now load-bearing, not
pedantry. After that, the general $a/b$, then $R$ and $n$ arbitrary.

## This student

Concrete and mechanical works; general and structural does not. When they stall,
drop to $R = \mathbb{Z}$, $n = 1$ and give something to compute. They ask only
about notation and framing — answer those instantly. Questions arrive pencilled
on the page; answer them before touching the working.

When they write *"I don't know"* they also write what they **do** know, and that
line is the diagnosis — r12's $ab^{-1}$ remark named the wrong target exactly.
Read it rather than re-asking the question louder.

## Tooling

`board recap` works; other subcommands fail (`ModuleNotFoundError: homework`).
Write cards straight into `live/cards/` as `NNNN-slug.md`. Compile with
`bash scripts/build.sh <tex>`.
