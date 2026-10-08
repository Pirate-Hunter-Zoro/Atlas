You are running headless, and THIS TURN IS NOT PART OF THE LESSON. Nobody is waiting at a board for a card.

%(inbox)s

Do this, and nothing else:
1. Read what is uncommitted in this repository: `git status` and then `git diff` over what it names. You are looking at work another assistant did, so read it rather than trusting it.
2. Judge whether it is the mission's work and whether it is safe to make public. This repository is pushed to a remote anybody can read. The one thing that must never go is session content -- a transcript line, a quoted span, an example taken from real audio -- wherever it has been pasted, including a test fixture or a docstring. If you find any, STOP: do not push, and say so in your last line so the next turn and the person can read it.
3. If it is clean, run `board push "<a one-line message saying what the mission did>"`. That commits and pushes the whole repository; it is the only push in this tool and it makes its own machine check before it goes. If it REFUSES, do not work around it and do not pass `--anyway`: the refusal names a file, and saying so is the answer.

**Write no card.** Do not run `board write`, do not run `board open`, do not touch `live/state.json`, `live/cards/` or `HANDOFF.md`, and do not run `board wait`. Do not read `AI_INSTRUCTIONS.md`, `live/TEACHING.md` or the cards: none of them is about this. End the turn when the push has happened, or when you have said why it must not.
