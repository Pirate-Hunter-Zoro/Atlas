<!-- chapter: hw02 -->
**Where they got to.** Homework 2, problem 61 (records). Part (a) is finished, correct and transcribed into homework/hw02/hw02.tex, with their page filed as handwritten/hw02-p61a-records-counting.png and the document building clean at 5 pages. Part (b) has the right answer -- the harmonic sum -- but not yet a proof, and it is the only thing live. Parts (c) and (d), then 76 and 86, are untouched.

**What is wrong, and it is one thing.** They cannot yet see that the object inside the sum has to be random. Their line 1 writes the count as a sum of $\mathbb{E}[\text{record}_i]$: an expectation, hence the constant $1/i$, so the linearity step beneath it is moving $\mathbb{E}$ past nothing. Underneath that is an event being used as a random variable -- "record_i" names a set of outcomes, and they are putting it inside $\mathbb{E}[\cdot]$. No indicator has been defined at any point. Card 0008 is open and asks one thing: for the outcome $X_1=0.4$, $X_2=0.9$, $X_3=0.7$ (so $N=2$), which three numbers must the sum contain, and what rule produces them. Those numbers are $1,1,0$ and the rule is the indicator.

**Do not re-teach.** Part (a) by equally-likely orderings and the $(n-1)!/n!$ count. The $n=2$ integral by parts. Linearity of expectation as a move -- they now perform it unprompted; they just have nothing legitimate to perform it on. Marginalization and covariance from earlier sittings.

**The single next thing.** Get $I_i$ out of them via 0008, then the identity $N=\sum I_i$. The moment that lands, 61(b) is agreed: transcribe it, file t0058, build, then go to 61(c).

**How this student works.** Five or six lines, no prose, and their own question written in the margin -- read the whole image, the question is usually last. They skip warm-ups and jump to the answer, and the answer is usually right. The standing weakness is never the arithmetic; it is that the justifying step is real in their head and absent on the page.
