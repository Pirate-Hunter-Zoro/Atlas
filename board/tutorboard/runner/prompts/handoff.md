This session is ending now. You get one turn and nobody will read stdout.

Run `board recap` first: this session holds only the last turn of the lesson, and the recap is the whole shape of it in one call. Do not read the cards file by file, and do not read AI_INSTRUCTIONS.md, board/TEACHING.md or the old HANDOFF.md to write this.

Then write the handoff by piping it to `board handoff` -- that command is the only thing that writes HANDOFF.md, it stamps the chapter for you, and **it refuses a body over 350 words.** The cap is not a suggestion: this file is read at the start of every turn of every future session, so length here is a cost paid over and over. If it refuses, cut it and pipe it again. Short and concrete:

- where the student got to, by topic, not by card number
- what they got wrong, and what the misunderstanding actually was
- what they got right, so it is not re-taught
- the single next thing to teach, and why that one
- anything about how this student works that took you a while to learn

If something you wrote this session made a specific line in the course's README or AI_INSTRUCTIONS.md actually false, fix that line. Do not review either document for drift and do not rewrite sections.

Do not ask questions, do not start new teaching, and do not write a card -- the student has already gone.
