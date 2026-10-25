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
- **No provider is load-bearing.** That covers text, vision and speech. Each walks a table, and
  something local ends every chain.
- **Python is standard library only. The web client is plain JavaScript.** External tools arrive
  through Homebrew or a subject's declared toolchain, never at board run time.

## Owner decisions

- **Atlas stays public.**
- **Git and sync.**
  - TUTOR.md stays tracked, but commits only with End or with real work.
  - End's commit and the sync pass push to GitHub automatically.
  - Laptops get the ignored course inputs by rsync over SSH from the Mac mini.
- **Owner files are pre-approved:** the owner's RULES.md files, the subject READMEs and the
  ai-config `update-tools` fix.
- **Brew upgrades.** Both upgraders stay.
  - The external `com.mikeyferguson.brewupgrade` keeps its job.
  - `atlas.brew-upgrade` keeps a full brew upgrader on every clone.
  - A cover run is a full brew upgrade, the external job's protected casks included.
- **Spirit-Forge:** the verification language is Lean 4 without Mathlib. Zig, Rust and
  containerization are the three things the project exercises, each with a real job in the game.
  Flutter stays the client as planned.
- **A blank canvas.** Home opens a canvas to write on with no tutor, for notes at a lecture. It
  saves to Random lessons, any subject or nowhere, and goes to a tutor at any time (item 12).
  Handing it over wakes one tutor turn.
- **Defaults:**
  - Home's "Annotate a PDF" preselects Random lessons.
  - A finished textbook ingest wakes one tutor turn.
- **Speech.**
  - Azure first, OpenAI second, local last.
  - A language course auto-speaks target phrases only.
  - Gaelic means Irish (ga-IE).

## Owner files

These are pre-approved. Write each from its bullets, and commit it when its item runs. None is
waiting.

## The owner's

- **For the full keyboard every time, turn Scribble off** in Settings > Apple Pencil, then
  force-quit Safari or the home-screen app. A Pencil tap on the answer box hands it to Scribble:
  the thin bar is Scribble's toolbar, and its Show Keyboard opens a mini keyboard that ignores
  the pinch. The page cannot choose the keyboard. Pencil ink on the board is unaffected.
- **Speech.** This Mac has `whisper-cpp`, `espeak-ng`, the whisper model and the Azure key.
  `setup-mac.sh` installs the first three on any other Mac.
- **For item 9:** turn on Remote Login on the Mac mini, add the laptop's SSH key to it, and give
  `setup-mac.sh --coding` the Mac mini's tailnet name.
- **Read `board/TEACHING.md` once.** Every turn is told to follow it.
- **Keep `~/.elan`.** Its 2.7 GB v4.34.1 toolchain is reused by every Lean subject.
- **Delete the ignored `projects/Lean-Theorem-Proving`** (about 14 GB of `.lake`) on any laptop
  that has it. `subjects.walk` lists any directory under `projects/` as a subject.
- **Tools on every machine.** Run `bash scripts/setup-mac.sh` twice on the Mac mini, and
  `bash scripts/setup-mac.sh --coding` twice on each laptop. The second run must
  end clean with `Brewfile.all unchanged`. The first installs mise, ghostscript and tesseract,
  re-renders the tutor-board plist with mise's shims on its PATH, and deletes the retired
  vendor checkouts and any retired project that holds only caches. One holding anything else
  is kept and named: move what is the owner's out of it, then delete it.

## Loose ends in the code

- `ai-config/adapters/claude_code.py` is a no-op hook kept for Claude Code sessions started
  before 2026-10-24, which still run it through `~/.claude/hooks/block-phi.py`. Once every
  session has restarted, delete both, and `A_LEFTOVER` in `assistants/claude_code.sh`.

## On the glass

These are built but not yet used for real. Strike each one after an evening on the iPad.

- **Home:**
  - Continue rows, New session and New canvas side by side, the Courses and Projects lists,
    and "+ new".
  - Random lessons first in every picker, and preselected in Annotate's sheet.
  - A subject delete with its typed name.
  - Deletes of a material, a document and a session, each with a second tap.
- **Sessions:**
  - A new session starts unbound, and "this is for Topology" binds it.
  - A free lesson sent to Random lessons at End, leaving a TUTOR.md line and any write-up.
  - One that ended unsent, sent later from its chip.
  - A new course made from the send picker at End.
  - Who teaches, switched from the tutor's chip mid-session.
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
- **Typing:** with the full keyboard up, the answer box sits on the keys, the lesson scrolls
  behind it, and the ⤢ key makes the box tall.
- **Laptop coding:**
  - In an iPad session bound to a subject with code, run the header's command on the laptop and
    edit one file. A `[code] step` card shows within a minute.
  - A do-mode `board push` lands on the laptop.
  - `board code <sid> --end` leaves one commit on main, no `code/*` ref, and the Mac pulled.
- **Teach and do on a computation:** in a fresh teach session on hw04, "tell me the (1,3)
  result" gets 169/432 and stops: no E[X₃], no write-up, no commit, the mode unchanged. In do
  mode it gets the same card and touches no file.
- **Answers:**
  - A response typing out, and the typed half of the answer panel.
  - Whether the verdict band and streak chip feel like information or like a scoreboard.
- **Speech,** on a subject whose `speech.lang` is zh-CN:
  - A zh-CN `say` phrase plays.
  - A take on the speak tab shows "heard: ..." within about 5 s, with a tone chip per syllable.
  - `board doctor --dry` names a working local TTS, STT and assessment.

## The work it is for

Each item's open tasks live in its subject's TUTOR.md.

1. **Probability and Galois Theory homework**, with items 10 and 11 taking the friction out.
2. **The Colibri course** (`courses/Colibri`): the lesson from card 0048, and the pitch deck's
   rounds.
3. **Spirit-Forge:** Sparring spirit in Rust, then the Lean thread.
