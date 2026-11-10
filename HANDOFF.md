# HANDOFF: what is left

This file lists the work still to do, in the order to do it. Delete an item when it lands.

## How to run this file

The owner starts a session with "read HANDOFF.md and get to work with ultracode". Then:

0. **Commit the plan.** If HANDOFF.md shows as modified, commit it from the main checkout
   before making any worktree, with
   `bash board/scripts/save-and-push.sh "HANDOFF: the plan" -- HANDOFF.md`. A worktree
   branches from HEAD.
1. **Do not ask; every decision is made.** They are under *Owner decisions*. The owner files
   under *Owner files* are pre-approved.
   - Write each owner file from its bullets, and commit it when its item runs, by pathspec in
     its own commit.
   - A new subject's RULES.md lands right after that item's `subjects.create`, which refuses a
     directory that already exists.
   - Stop for the owner only where an item says the owner acts: the iPad or a key.
     Ask only if the tree contradicts this file in a way it does not foresee.
2. **Then take the items in order.** Each item is one workflow chain:
   - Re-inventory against the tree. Line numbers drift, so find code by name.
   - Implement in a worktree under `~/Developer/Atlas-wt/<item>`.
   - Run `python3 board/test/run.py`.
   - Review adversarially, with independent verifiers that try to refute the change.
   - Merge.
   - Delete the item from this file in the same commit.

   When a Done-when needs the iPad or the owner, merge once everything machine-checkable
   passes. Move the on-device criteria into *On the glass* in the same commit, and name them in
   the report as the owner's.
3. **Between items, report in six lines or fewer.** Say what landed, what was skipped and why,
   and what the owner must do on the iPad.

Rules that hold throughout:
- **The main checkout serves the iPad live.** Merging board code restarts the board. Merge only
  when `sessions/*/agent.json` shows no `turn_pid` and the owner is not mid-lesson.
- **Commit named paths only**, with `bash board/scripts/save-and-push.sh "message" -- <paths>`.
  The main checkout carries uncommitted owner work.
- **Owner files are the owner's.** These are `RULES.md`, subject `README.md`s, and
  `TUTOR.md` outside `board memo`. A tutor turn may not commit them.
- **DeepSeek through OpenCode is the AI,** for turns and for vision. Nothing chooses another
  assistant. Speech is Azure first and local last.
- **Python is standard library only. The web client is plain JavaScript.** External tools arrive
  through Homebrew or a subject's declared toolchain, never at board run time.

## Owner decisions

- **Atlas stays public.**
- **Git and sync.**
  - TUTOR.md stays tracked, but commits only with End or with real work.
  - End's commit and the sync pass push to GitHub automatically.
- **Owner files are pre-approved:** the owner's RULES.md files, the subject READMEs and the
  ai-config `update-tools` fix.
- **Machine upkeep.** One system, `upkeep/`, byte-identical in Atlas and Media-Orchestrator,
  keeps every Mac installed and current; `flutter doctor` stays green. Atlas adds only its
  `upkeep.d/hook`.
- **Longtable:** the verification language is Lean 4 without Mathlib. Rust, Zig, Kubernetes
  and Flutter are the things the project exercises, each with a real job in the table. The
  product is offline first and iPad first, uses SRD 5.1 plus the owner's homebrew, and replaces
  the physical materials of a D&D table.
- **A blank canvas.** Home opens a canvas to write on with no tutor, for notes at a lecture. It
  saves to Random lessons, any subject or nowhere, and goes to a tutor at any time (item 12).
  Handing it over wakes one tutor turn.
- **Defaults:**
  - Home's "Annotate a PDF" preselects Random lessons.
  - A finished textbook ingest wakes one tutor turn.
- **Speech.**
  - Azure first, local last.
  - Narrates boxed text on a tap; nothing auto-plays and no voice is graded.

## Owner files

These are pre-approved. Write each from its bullets, and commit it when its item runs. None is
waiting.

## The owner's

- **The full keyboard.** The board's text fields are out of the Pencil's reach, so Scribble
  cannot take one, and a finger tap gives the full keyboard. Scribble can stay on. Once, after
  the board updates: force-quit the home-screen app and Safari, because the mini-keyboard state
  sticks to the running app. If the system keyboard itself is floating, pinch it out once.
- **Speech.** This Mac has `whisper.cpp`, `espeak-ng`, the whisper model and the Azure key.
  `setup-mac.sh` installs the first three.
- **Read `board/TEACHING.md` once.** Every turn is told to follow it.
- **Keep `~/.elan`.** Its 2.7 GB v4.34.1 toolchain is reused by every Lean subject.
- **Delete the ignored `projects/Lean-Theorem-Proving`** (about 14 GB of `.lake`) if this Mac
  has it. `subjects.walk` lists any directory under `projects/` as a subject.
- **Tools on this Mac.** Run `bash scripts/setup-mac.sh` twice here. The second run must
  end clean with `Brewfile.all unchanged`. The first installs mise, ghostscript and tesseract,
  re-renders the tutor-board plist with mise's shims on its PATH, and deletes the retired
  vendor checkouts and any retired project that holds only caches. One holding anything else
  is kept and named: move what is the owner's out of it, then delete it.

## On the glass

These are built but not yet used for real. Strike each one after an evening on the iPad.

- **Home:**
  - Continue rows, New session and New canvas side by side, the Courses and Projects lists,
    and "+ new".
  - Random lessons first in every picker, and preselected in Annotate's sheet.
  - A subject delete with its typed name.
  - Hiding an open session from Continue, and showing it again, without ending it.
  - Deletes of a material, a document and a session, each with a second tap.
- **Sessions:**
  - A new session starts unbound, and "this is for Topology" binds it.
  - A free lesson sent to Random lessons at End, leaving a TUTOR.md line and any write-up.
  - One that ended unsent, sent later from its chip.
  - A new course made from the send picker at End.
  - The session header: subject chip, teach and do, Make, End.
  - Teach and do persist until switched, and a do turn runs `board check`.
- **Documents:**
  - The Colibri deck's round 2. In the Colibri library, re-ask its revise: its 40 requests are
    unanswered, because the last revise timed out. Let it finish, then End. End commits, and the
    ledger shows round 2 answered.
  - One document all the way round: Make, build, read, ink, "Say what's wrong", revise.
  - The round as pairs on the Colibri deck: tap the chip, a row and a pip, and mark pairs fine
    or not fixed.
  - Pinch-zoom on a paper and a deck in the one reader. Safari's page zoom never starts, ink
    stays on its words, and one finger scrolls a zoomed page sideways.
  - A canvas's "End and transcribe": each page's text lands under its image in the filed
    notes.md, and it builds.
  - A canvas shows no Send and no Live, and the menu's "this page as PNG" and "PDF" each save.
  - "Give to the tutor" from a canvas's Continue row and from its Past row.
  - A canvas at a lecture: "New canvas" in one tap, three pages with the tutor still
    listening, "Save to" Random lessons mid-canvas, "Give to the tutor" days later bringing one
    card that reads all three pages, the PDF in the share sheet, and "End, keep the pages"
    leaving them in the library with no turn.
  - Annotate from Files, from a URL and from `board open`; "Keep a marked copy"; and the copy
    following the PDF into the chosen subject.
  - Sending selected annotations.
  - A writeup appearing after handwritten answers in a project session.
  - A code excerpt with `path#L`, opening the read-only source viewer.
  - The ink clipboard across pages: copy on the board, then in annotate, then paste on the
    board, and the annotate ink pastes. Then the reverse.
- **A textbook:** "+ new course" with a PDF ends in a `[textbook]` card, with the readings and
  chapter notes on disk and `chapters.tsv` committed. The library shows the book's line, or
  "Add the textbook".
- **The problem on screen:** in a hw04 session pinned to problem 5,
  - chips P and p show without scrolling, and the statement opens and closes in one tap;
  - P to the calculator, then `p*P^3`, shows fractions;
  - P onto the page moves with the lasso and appears in the sent PNG;
  - Galois ch07 shows problem 17 whole.
- **Typing:** a finger tap on the answer box gives the full keyboard every time, and the box sits
  on the keys. A Pencil tap on the box does nothing; any Pencil touch puts an open keyboard
  away. A card landing or a pinch-zoom while typing leaves the keyboard up. The ⤢ key makes the
  box tall.
- **Coding:**
  - In an iPad session bound to a subject with code, run the header's command on this Mac and
    edit one file. A `[code] step` card shows within a minute.
  - A do-mode `board push` lands here.
  - `board code <sid> --end` leaves one commit on main, no `code/*` ref, and this Mac pulled.
- **Teach and do on a computation:** in a fresh teach session on hw04, "tell me the (1,3)
  result" gets 169/432 and stops: no E[X₃], no write-up, no commit, the mode unchanged. In do
  mode it gets the same card and touches no file.
- **Answers:**
  - A response typing out, and the typed half of the answer panel.
  - Whether the verdict band and streak chip feel like information or like a scoreboard.
- **Speech:**
  - A card reads aloud from its speak button, and a `say` phrase plays on its own button.
  - A take on the speak tab shows "heard: ..." within about 5 s.
  - `board doctor --dry` names a working local TTS and STT.

## The work it is for

Each item's open tasks live in its subject's TUTOR.md.

1. **Probability and Galois Theory homework**, with items 10 and 11 taking the friction out.
2. **The Colibri course** (`courses/Colibri`): the lesson from card 0048, and the pitch deck's
   rounds.
3. **Longtable:** First roll in Rust, then The sheet and The table.
