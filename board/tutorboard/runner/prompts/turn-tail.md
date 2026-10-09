This turn is its own session and nothing you are holding survives it. The lesson is on disk and `board recap` reads it back. If this turn changed where things are, what is happening now, an open decision or what got done, rewrite that section of the subject's TUTOR.md before you finish: `board memo <section>`, the section's whole new text on stdin. The file is capped at 800 words.

Two things not to do, both of which cost real money before they were refused outright:
- **Do not run `board wait`.** A turn does not wait. The daemon that started this turn is already blocked on the student's next message and will hand it to a fresh turn the moment it lands. Waiting here holds this whole conversation open while they think and then answers them inside it.
- **Do not touch `HANDOFF.md`.** Not a read, not an edit. The wrap-up turn at the end of the session writes it, once, with `board handoff`. A teaching turn that edits it pays to read five thousand tokens of it first and hands the next turn a longer one.

End your turn when the card is written.
