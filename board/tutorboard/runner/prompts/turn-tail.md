Before you finish, leave the next turn a note: `board note`, at most 120 words on stdin -- what you actually READ in their answer (the misreading, not the mark) and the one thing you are aiming at next. Not a summary of the lesson; `board recap` has that. This turn is its own session and nothing you are holding survives it, so that note is the only thing that does.

Two things not to do, both of which cost real money before they were refused outright:
- **Do not run `board wait`.** A turn does not wait. The daemon that started this turn is already blocked on the student's next message and will hand it to a fresh turn the moment it lands. Waiting here holds this whole conversation open while they think and then answers them inside it.
- **Do not touch `HANDOFF.md`.** Not a read, not an edit. The wrap-up turn at the end of the session writes it, once, with `board handoff`. A teaching turn that edits it pays to read five thousand tokens of it first and hands the next turn a longer one.

End your turn when the card and the note are written.
