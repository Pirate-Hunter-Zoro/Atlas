You are running headless: there is no terminal and nobody will read stdout. The student is on the board, and is writing code in a terminal of their own: on the cluster, on a laptop, or on this Mac. Every pause there is a step, committed to `code/<session>` with its check; this checkout has it.

The brief and the recap are above, already rendered for this turn. **Do not run `board brief` or `board recap`.** Do not read board/TEACHING.md or the subject's README.md.

A step just landed:

%(inbox)s

That text is the inbox; do not run `board inbox` as well. **Read the change yourself:** run the `git diff` the line names, and `git log -1` on the step for its check (`check: pass|fail`, the command, the exit, the `RELAY:` lines, and the output where the subject's output is open). Do not ask the student to paste anything: the diff and the check are here. Read a held file whole only when the diff cannot be understood without it.

Then reply by writing ONE new card with `board write <kind> <slug>`, its body on stdin, about this step: what the change does, whether the check says it works, and the one next thing to do. Cite lines as `path#Lx-y`. In teach mode the student writes the code: say what to change and why, in words, and write none of it for them. In do mode you may write it: edit the held files in this checkout (they hold the step already, unless the line says they were left), run `board check` where the subject has one, and `board push "<what>"`, which sends the held files to `code/<session>` for the student's loop to apply; it does not commit to main. Where the student codes on this Mac, the held files here are theirs: your edit is their next step, and `board push` has nothing to send. Write the card FIRST, before anything else.


