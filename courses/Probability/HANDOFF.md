<!-- chapter: hw03 -->
Homework 3 (Ross ch. 3): problems 1, 7, 9-or-10, 12, 22, 31, 37, 40. All eight statements are transcribed in `homework/hw03/hw03.tex`.

**Done, correct, typeset — do not re-teach.** Problems 1, 7, 9-or-10 and 12. Four of eight. Each has their argument in its SOLUTION region and their page in `handwritten/`. Last build: 4 pages, 0 warnings.

Between them they now own: the chain rule for a joint pmf; marginalising the joint over x to rebuild p_Y(y); conditioning on two variables at once (Problem 7's numbers); and the whole continuous version — marginal density by integrating the joint over x, conditional density as the quotient, expectation against the conditional, integration by parts with the vanishing boundary term, L'Hôpital on -xy/e^{x/y}.

**The one error worth remembering.** On Problem 12 they first integrated x against the JOINT density and never divided by f_Y(y), landing on ye^{-y} instead of y. Same shape as their Problem 1 mistakes: the conditioning denominator is what goes missing. Named once, their redo was correct end to end. The gap is closed; this is here so you recognise it if it returns.

**Next: Problem 22**, posed on card 0008, unanswered. Independent trials over m equally likely outcomes until one outcome repeats k times in a row; show E[N] = (mᵏ-1)/(m-1). Open ask is a fair-die warm-up: run of 2 at trial 5, what can the run be after trial 6 and with what probability. It targets the one thing that breaks the recursion — a failed extension restarts the run at 1, not 0. Nothing they have done so far is recursive.

**How this student works.** They skip the small warm-up and send a full proof of the real problem instead, four times now. Do not chase the skipped sub-question; read what arrived and mark that. They write in symbols, fast and clean, so an error is one defective symbol, not confusion. Name it and stop. They write "Where did I mess up?" on the page even when nothing is wrong; answer that first, in its own card, and say plainly when the answer is "nowhere".
