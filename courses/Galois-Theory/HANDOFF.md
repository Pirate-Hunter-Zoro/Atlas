<!-- chapter: Ch 06 — Ruler-and-compass constructions -->
This sitting is not ruler-and-compass. The student skipped Chapter 6 and works homework/worksheet-automorphisms-splitting-fields, Problems 7 to 10 in sheet order. Problems 11 and 12 wait for their own sheet. The sitting is bound to that file with board hw use.

Where they got to: 7(a)-(c), 8(a), 8(b) and the degree half of 8(c) ([Q(zeta_p):Q] = p-1, Phi_p is the minimal polynomial) are written up. The rest of 8(c) is open: the injection Aut(Q(zeta_p)/Q) -> (Z/p)^x from 7(c) is onto. That is the TODO at the end of 8(c) in the .tex.

Open question: show Phi_p(zeta_p^k) = 0 for 1 <= k <= p-1. That is step one of onto; they left before answering. Expect: (zeta^k)^p = 1, zeta^k != 1 because p does not divide k, and (x-1)Phi_p = x^p - 1. Step two: Q(zeta^k) = Q(zeta), because zeta = (zeta^k)^m with km = 1 mod p. Then 8(a) gives sigma_k. Then re-pose onto in full, replace the TODO with their argument, board hw file 8c, board hw build, and pose 9(a) (x^4 + 1).

Where they got stuck: they wrote the onto statement correctly, then said "I'm stuck". They could not see how 8(a) reduces it to two facts about zeta^k. Earlier they said they had no idea what they were proving. The gap was the statement, not the technique.

Got wrong, now fixed: in 7(c) they confused injectivity of sigma with injectivity of the map sigma -> k mod n. Pigeonhole fixed it.

Got right, do not re-teach: roots go to roots; an automorphism is determined by its generators; elements of F(alpha) are polynomials in alpha; composition goes to multiplication mod n; 8(a) existence via evaluation maps into F[x]/(p), and uniqueness; ker = (p) because (p) is maximal; Eisenstein on the shifted Phi_p.

How they work: they answer in handwriting with no concluding words, and they leave margin questions. Answer a margin question first. They reject tiny numeric warm-ups ("NO! We can finish the onto gap") and over-explaining ("that's trivial"). Aim at the actual gap. board write needs a card kind: board write check <slug>.
