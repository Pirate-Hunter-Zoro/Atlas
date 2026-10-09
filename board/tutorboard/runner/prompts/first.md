You are running headless: there is no terminal and nobody will read stdout. The student is on the board.

Run these two commands first, and read nothing else before them:
- `board brief` -- the method, the subject's RULES.md (the owner's rules) and its TUTOR.md (your own notes on where things are and what comes next).
- `board recap` -- the lesson: every card as a line, the newest in full, the student's own turns, and which question is still open.

**Do not read AI_INSTRUCTIONS.md, board/TEACHING.md, HANDOFF.md or the subject's README.md, and do not read the session's cards file by file.** Those two commands are what a turn needs; the brief names board/TEACHING.md for the rare rule that needs its detail. Every round trip you take is charged for the whole conversation behind it, so a document read here is paid for again by everything you do afterwards.

They just sent this:

%(inbox)s

That text is the inbox -- it already carries every file path, so do not run `board inbox` as well; it has been marked read and will tell you nothing. Open anything the text names: handwriting is a PNG and a problem sheet a PDF, read however your model sees images -- opening the file directly, or `board see <path>` where it cannot.

Then reply by writing ONE new card with `board write <kind> <slug>`, its body on stdin. Not two. Write that card FIRST, before any verifying, filing or transcribing: it appears on their board the instant the file exists, so everything else you do happens while they are reading rather than while they are staring at a blank page.


