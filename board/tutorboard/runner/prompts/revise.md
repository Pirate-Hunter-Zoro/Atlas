You are running headless, and THIS TURN IS NOT PART OF THE LESSON. Nobody is waiting at a board for a card. Somebody read a document this workspace has written and said what is wrong with it, from the library page.

They sent this:

%(inbox)s

Do this, and nothing else:
1. Read the feedback file the text above names, and read the document it is about. Both are paths in this repository.
2. REVISE THE DOCUMENT. Edit the source the document is built from -- the `.tex` or the `.md` the text above names -- and rebuild it with `board build <source>`, which writes the PDF, and the .docx of a .md, beside it. Keep its structure, its names for things and its claims except where the feedback says otherwise. Do not start it again and do not widen it.
3. ANSWER EVERY REQUEST. Where the text above names a ledger -- the `.ledger.json` beside the feedback file -- its `items` are the requests of this round, each with an id like `R3.4`. Fill its `answers` object with exactly one entry per id, keyed by the id: `disposition` (one of `done`, `partly`, `not done`, `pushed back`), `did` (one sentence of what you did, or why not; for `not done` and `pushed back` it is the reply the owner reads beside their ink), and `new` (the new wording of the passage you changed, copied exactly from the source; required for `done` and `partly`). A request you could not find or act on is still answered -- `not done`, saying why -- and one you think is wrong is `pushed back`, saying why. Change nothing else in that file. The board writes `## What was changed` into the feedback file from your answers, so do not write it yourself. Where no ledger is named, write what you changed at the BOTTOM OF THE FEEDBACK FILE instead, under a `## What was changed` heading: what you changed, what you left and why, and anything in the feedback you could not act on. Either way that is the record of this round, and it is where the person who wrote the feedback will look.

**Write no card.** Do not run `board write`, do not run `board open`, and do not touch the session's state, its cards or `HANDOFF.md`. There is a lesson on this board and it belongs to somebody else's evening; this turn must leave every part of it exactly as it found it.

Do not read `AI_INSTRUCTIONS.md`, `board/TEACHING.md` or the cards: none of them is about this document. `board brief` is not needed either. End the turn when the document is revised and every request is answered.
