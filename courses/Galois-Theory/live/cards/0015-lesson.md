---
kind: lesson
---
We need to produce a card (one turn). The student asks: they wrote h=(1 2), g=(1 2 3), they forgot what these tuples mean and how they translate to a permutation, and how to compute conjugate g h g^{-1}. So we need to answer that question: explain what cycle notation means, compute g h g^{-1} and its order. According to teaching rules: teach toward a question, one concept per response, one question per turn, one card per turn. So we need to produce a card that teaches the concept needed to answer their question, then pose at most ONE question and stop. The student asked: they forgot what these tuples mean and how they translate to a permutation, and how to compute conjugate. So we need to teach the concept of cycle notation and conjugation in symmetric groups, then ask a question to check understanding. Possibly ask: "What is g h g^{-1} as a cycle?" Or "What is its order?" The student already asked to compute ghg^{-1} and say its order. So we can teach then ask them to compute. But we must not answer the question fully? The rule: "Teach only what this step needs, then pose at most ONE question and stop. A wrong answer gets its break located, not repaired; never re-explain what they already got right." So we should teach the concept needed (cycle notation, how to read, composition, inverse) then ask them to compute ghg^{-1} and its order. That is a question. So card: kind: question? Or maybe lesson? Since we need to teach then ask a question. The pattern: we can have kind: lesson? But we need to output a card with front matter. The example given for question. But we can also have kind: lesson if we are teaching. However the instruction: "Teach only what this step needs, then pose at most ONE question and stop." So we can have a card that is a lesson (teaching) and ends with a question. The kind could be "lesson". But the example shows question. The spec: kind can be lesson|question|correct|wrong|review|note|recap. So we can use lesson. We'll include a brief teaching then a question.

We must output ONLY the card, as markdown front matter plus the body, nothing else.

Thus:

---
kind: lesson
title: Cycle notation and conjugation in S3
---

Then body: explanation.

We need to use $...$ and $$...$$ for math.

We need to explain: In cycle notation (1 2) means swap 1 and 2, fix 3. (1 2 3) means 1→2,2→3,3→1. The inverse of g is (1 3 2). Conjugation g h g^{-1} means apply g^{-1}, then h, then g. Compute: g h g^{-1} = (1 2 3)(1 2)(1 3 2) = (2 3). Or we can compute directly: conjugate of a transposition by a 3-cycle yields the transposition of the images: g (1 2) g^{-1} = (g(1) g(2)) = (2 3). So result is (2 3), order 2.

Then ask: "What is g h g^{-1} as a cycle, and what is its order?" That's one question.

We must not answer it. So we stop after posing question.

Make sure not to include extra explanation beyond needed. Keep concise.

Let's craft body:

- Explain cycle notation: (a b) swaps a and b, fixes others; (a b c) sends a→b, b→c, c→a.
- Inverse of a cycle
