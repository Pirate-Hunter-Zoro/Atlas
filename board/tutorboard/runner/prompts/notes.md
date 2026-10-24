This notes session is ending now. You get one turn and nobody will read stdout. There are no cards and no recap: the session is the handwriting below.

The owner wrote these pages on a blank canvas, in this order. Open each picture and read all of it:

%(pages)s

The session is titled "%(title)s" and is bound to %(subject)s.

1. If it is bound to no course or project, the owner ended it without choosing one: bind it to Random lessons, the catch-all, with `board bind %(scratch)s`. Only when its pages plainly belong to another course or project, bind that one instead: `board bind courses/<name>` or `board bind projects/<name>`, adding `--create` when none fits (a project also takes `--phi no` or `--phi yes`).
2. Start the transcript with `board writeup new --md "%(title)s"`. It prints the path, from the Atlas root, of `docs/<slug>/notes.md`, where the pages are filed: it already holds one image line per page, `![page N](handwritten/page-NN.png)`, in page order.
3. Transcribe each page under its own image line, in page order, as Markdown: a heading where the page heads something, math in `$...$` and `$$...$$`, a short `[illegible]` where a word cannot be read. Keep every image line. Transcribe what is written; do not add to it, explain it or correct it.
4. Run `board build <that notes.md>` and fix whatever it reports until it builds.

Do not write a card and do not ask questions -- the owner has gone. The session's End commits notes.md once you are done.
