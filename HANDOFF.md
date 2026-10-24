# HANDOFF: what is left

This file lists the work still to do, in the order to do it. Delete an item when it lands.
Agents never ssh to the cluster; cluster steps are the owner's.

## How to run this file

The owner starts a session with "read HANDOFF.md and get to work with ultracode". Then:

0. **Commit the plan.** If HANDOFF.md or LIBR-EXIT.md shows as modified, commit both from the
   main checkout before making any worktree, with
   `bash board/scripts/save-and-push.sh "HANDOFF: the plan" -- HANDOFF.md LIBR-EXIT.md`. A
   worktree branches from HEAD.
1. **Do not ask; every decision is made.** They are under *Owner decisions*. The owner files
   under *Owner files* are pre-approved.
   - Write each owner file from its bullets, and commit it when its item runs, by pathspec in
     its own commit.
   - A new subject's RULES.md lands right after that item's `subjects.create`, which refuses a
     directory that already exists.
   - Stop for the owner only where an item says the owner acts: the iPad, the cluster, or a key.
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
   and what the owner must do on the iPad or the cluster.

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
- **What leaves.**
  - The LIBR exit removes every PHI guard, and `projects/Meetings` with the meeting deck.
  - `projects/Paper-Writer` is scrapped in the same run, and zipped with a history bundle like
    the LIBR projects.
  - The bundles' history filter is `git-filter-repo`, installed through brew for the run and
    uninstalled after.
- **Git and sync.**
  - TUTOR.md stays tracked, but commits only with End or with real work.
  - End's commit and the sync pass push to GitHub automatically.
  - Laptops get the ignored course inputs by rsync over SSH from the Mac mini.
- **Owner files are pre-approved:** the owner's RULES.md files, the subject READMEs and the
  ai-config `update-tools` fix.
- **Galois:** the p=13, d=2 worked case of ch07 13(d) carries into the course.
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

These are pre-approved. Write each from its bullets, and commit it when its item runs.

- **`courses/Random/RULES.md` (item 12):**
  - Each session is its own topic.
  - TUTOR.md "Done recently" holds at most 15 one-line entries, newest first.
  - Cut before adding.


## 5. The LIBR exit

Run `LIBR-EXIT.md`. The owner's section 5a is done, and it
stops midway for the owner's section 5b.

It zips TRD-EHR, PSYCH-ASR, libr-local-llm and Paper-Writer with their write-ups, results and
sessions to `~/LIBR-handoff-<date>/`. It records Colibri's upstream instead of zipping it. It
removes the cluster, every PHI guard, Meetings, Paper-Writer and the vendored Colibri.

Sections 1 and 2 are done: every zip and bundle in `~/LIBR-handoff-2026-10-23/` verifies. Section 3
waits for the owner's section 5b.


## 12. Free boards and any PDF, saved to Random lessons or a subject

These already exist:
- "New session" starts unbound. The chip binds it, End on an unbound session opens the send
  picker, and the send files uploads into `materials/`.
- Home's "Annotate a PDF" takes a file from the iPad's Files.

What is missing is a catch-all, a URL or a Mac path, and a single "save to" order.
- **`courses/Random` ("Random lessons").** It is a course, so phi is false.
  - Create it with `subjects.create("courses/Random")`, which names it "Random".
  - Then set its `tutorboard.json` `name` to "Random lessons" and commit that by pathspec.
  - Its RULES.md is in *Owner files*. Never name it Inbox, Data, Raw or
  Audio while `fenced.NEVER` exists, or Scratch, which `board.js` already uses for the uploads
  drawer.
- **The constant:** `subjects.SCRATCH = "courses/Random"` and `subjects.scratch(base)`.
  `/subjects.json` returns `scratch` beside `meetings` (or alone after the exit).
- **One order in all four pickers:** "Random lessons" first, then Recent, Courses, Projects. The
  pickers are `board.js` `paintSubjects`, `home.js` `paintSender` and `openAnnot`, and `slate.js`
  `openSend`, which also ends on "keep it unfiled". Annotate
  preselects Random lessons, and "not yet: it stays in the session" stays last. No route changes.
- **The notes canvas:** an unbound canvas binds to the catch-all unless its pages plainly belong
  elsewhere. Change `runner/prompts/notes.md` step 1 and `loop.notes_up`, and name the catch-all
  in `brief.py`'s unbound line.
- **The marked copy reads all ink.** `burn.strokes_by_page` reads every dir in
  `course_repo.ink_dirs(repo)`. Today ink drawn before a bind is missing from "keep a marked copy".
- **A blank canvas** (owner decision). Home's Notes canvas (`home.js` `newNotes`, a `view: slate`
  session) already opens in one tap, holds many pages and never wakes a tutor while unsent. Build
  the rest:
  - **Named for what it is.** `#act-notes` becomes "New canvas", sub-line "write now; file it or
    give it to a tutor later", beside `#new-session`. The meeting deck's `notes*` ids stay its own.
  - **Writing never wakes a tutor.** On a canvas, `slate.js` hides `bSend` and the Live chip through
    a new `api.sendable(false)` in `slate-core.js`.
  - **"Save to…" on the canvas.** `#away` gains a subject button that opens the shared picker and
    binds through `POST /s/<id>/bind`. It neither ends the session nor wakes a turn.
  - **The pages are filed, not only transcribed.** A new `sessions.file_canvas(sid)` writes the
    inked pages to `<subject>/docs/<slug>/handwritten/page-NN.png` (at the send cap, not
    `PNG_IDLE_EDGE`), beside a `notes.md` with one image link per page and a `doc.json` naming the
    session. It runs on bind and on End, and `_kept` commits that directory.
  - **End offers three things.** "End, keep the pages" files them and queues no turn. "End and
    transcribe" is today's `_notes`, writing the text under each page's image. "Keep it unfiled"
    ends with no turn and leaves the pages in the session. `routes/lesson.py` `_end` takes
    `{subject?, transcribe}`, and `RUNNER.end` runs only when `transcribe` is true.
  - **"Give to the tutor" wakes one turn on the whole canvas.** It sits on the canvas and on its
    Continue and Past rows. `POST /s/<id>/give` writes one waking `[canvas]` line naming every
    inked page in order (`sessions.slate_pages`). On an ended canvas it calls `sessions.reopen`
    first, so it is not in `ENDED_REFUSES`. Home then opens `/s/<id>/board`.
  - **The tutor knows the canvas exists.** For a canvas session, `brief.py` names its pages and
    `board slate --all`.
  - **A taught canvas gets its wrap-up.** `service._wrap` runs `loop.wrap_up` for a `view: slate`
    session that has cards, and `_notes` when transcription was asked for.
  - **Export.** `GET /s/<id>/canvas.pdf` comes from a new `burn.canvas_pdf(pages)`, drawing the
    strokes as vector paths on white pages through `_write_pdf`, each page cropped like `pngBox`
    (canvas PNGs are RGBA, which `burn._png_parts` refuses). The canvas menu offers "PDF" and "this
    page as PNG".
- **From a URL:** `POST /s/<id>/fetch {url}` in `routes/writing.py`, added to
  `handler.ENDED_REFUSES`.
  - Allow http and https only. Build the opener without `FileHandler` or `FTPHandler`, and
    recheck the scheme after redirects.
  - Use a 60 s timeout and the `multipart.MAX_UPLOAD` cap. The body must start with `%PDF-`.
  - Reply like `/upload`.
  - Home's Annotate sheet gains `#annot-url`.
- **From a Mac path:** `board open <file.pdf> [--subject <id>]` copies, never moves, the file into
  a new "Annotate <name>" session. It binds and files when given `--subject`, and prints the URL.
  It is listed in `NO_LIVE`.

Done when:
- All four pickers show Random lessons first, and a canvas has no Send or Live (JSDOM).
- `/sessions/new {view:slate}` plus an unsent `/slate/save` writes no waking line and queues no
  turn. `/give` writes one `[canvas]` line listing pages 1..N and queues one turn; on an ended
  canvas it reopens and wakes; on an empty one it answers 400.
- `_end {transcribe:false}` queues nothing and commits `docs/<slug>/notes.md` with
  `handwritten/page-*.png`; with no subject and no transcription it commits nothing.
- `canvas.pdf` starts with `%PDF-` and has one page per inked page.
- `_wrap` on a canvas with cards writes TUTOR.md.
- A send there files uploads into `courses/Random/materials/`.
- `/fetch` lands a local http.server PDF and refuses file://, ftp:// and a non-PDF.
- `board open` has a CLI test.
- A marked copy made after a bind holds the ink drawn before it.

## 14. Speech: every tutor speaks, listens and judges pronunciation

Every session gets this, math included. A language subject turns it on by default.

DeepSeek has no audio model, so the local recipe ends every chain. Run this after the exit, so
no PHI rule applies. Never track audio: the audit's binary refusal stays.

- **The table: `board/tutorboard/agents/speech.py`.**
  - `DEFAULT_SPEECH` holds the recipes:
    - `azure`: TTS by SSML. STT and assessment by the REST short-audio endpoint with the base64
      `Pronunciation-Assessment` header (Phoneme granularity, Comprehensive, EnableMiscue,
      HundredMark). The audio is WAV PCM 16 kHz mono, at most 30 s. The keys are
      `AZURE_SPEECH_KEY` and `AZURE_SPEECH_REGION` in keys.env.
    - `openai`: `gpt-4o-mini-tts`, and `gpt-4o-mini-transcribe` with multipart built by hand.
    - `local`:
      - TTS: `say`, rendered to m4a, falling back to `espeak-ng` for Irish (ga), which macOS
        has no voice for.
      - STT: `whisper-cli` with a ggml model in `~/.local/share/tutor-board/models/`.
      - Assessment: `tutorboard/speech/tones.py`.
  - Azure's Irish voices are `ga-IE-OrlaNeural` and `ga-IE-ColmNeural`.
  - `config.json` gets a `speech` block, laid over the defaults like `agents`, with
    `order = {tts, stt, assess}`. The default order is azure, openai, local.
  - `chain(kind, lang)` skips a recipe that is unkeyed, missing its command, limited, stood down
    or lacking the language, and always ends with local.
  - `run()` walks it the way `seeing.describe` does, and writes one cost line to `cost.jsonl`.
- **The local tone check: `speech/tones.py`, stdlib.**
  - A YIN F0 tracker, with median smoothing and octave-jump repair.
  - Semitones relative to the speaker's median.
  - Syllables come from whisper timestamps, else from voiced runs merged to the target count.
  - Classify each syllable against T1 to T4 and neutral, and run DTW against the TTS reference.
  - Output each syllable's target tone, heard tone and confidence, plus a word diff.
  - A low-confidence verdict counts as unknown. The scratch prototype found 6 voiced runs for 4
    syllables, so it ships labelled.
- **Listening: `POST /s/<id>/speech/say`.**
  - The request is multipart: audio, `answers`, `ref`, `lang` and `pinyin`.
  - Save it to `sessions/<id>/speech/`. Never use a dir named `audio`, or a file named
    `.transcript.txt` or `.aligned.json`.
  - Convert with `afconvert`, or `ffmpeg` for webm.
  - Run STT, then assess when there is a `ref`, and write `<base>.heard.json`.
  - Then write the turn record and a waking `[speech] heard: '...'. Target: '...'. <verdict>`
    line with `file:`. The tutor never gets raw audio.
  - Add the route to `ENDED_REFUSES`, and add `board hear <file>`.
- **Speaking.**
  - Cards may carry a fence opened with `say <lang>` and an optional `pinyin="ni3 hao3"`.
  - `lesson/cards.py` synthesises these, as `extract_tikz` does, into
    `~/.cache/tutor-board/speech/<sha>.m4a`, served at `/speech/<sha>.m4a`.
  - Each card head gets a speak button: `POST /speech/card` reads the prose and skips math and
    code.
  - An auto-speak toggle, stored per subject, is also the iOS audio unlock.
  - Playback fetches to a Blob, since there is no Range support.
- **Recording: `web/speak.js`.**
  - A third answer tab, `#tab-speak`, opens a `#speakbox` with record/stop, a level meter and the
    last heard block with tone chips.
  - MIME type: `audio/mp4`, else `audio/webm;codecs=opus`.
  - Call `getUserMedia` only on tap, and stop the tracks after each take.
  - Add it to the `sw.js` shell.
- **Per subject:** `tutorboard.json` may hold `speech = {lang, native, voice, auto}`.
  `course/config.read_config` keeps it, and `truthful.py` stays green. `SPEECH_SENSE` is included
  when a subject has `speech` or a session holds heard files. TEACHING.md gets a short drill
  section within its cap.
- **Setup:**
  - The Brewfile gets `whisper-cpp`, `ffmpeg` and `espeak-ng`.
  - `setup-mac.sh` downloads one whisper model with a checksum, and a second run changes nothing.
  - `board doctor` speaks one word and transcribes it back as a witness.
- **Tests:** `board/test/speech.py` covers fake HTTP recipes, chain order, WAV synthesised at run
  time with `wave`, sine-sweep tone classification and the route. A JS suite stubs MediaRecorder.

Done when, on the iPad PWA:
- A zh-CN `say` phrase plays.
- A take shows "heard: ..." within about 5 s, with per-syllable tones.
- `board doctor --dry` names a working local TTS, STT and assessment.

Expected cost at 5 hours a week is about $3-5 a month (Azure's free tier covers most of it), and
$0 local-only.

Language subjects need nothing else from the board. Handwriting already covers kanji, kana and
hanzi, and a subject only sets `speech`. Drawing and art come later. That work adds colour and
pressure brushes to the slate with a reference-image layer, and critique goes through the
existing vision route on the slate PNG.

## The owner's

- **LIBR-EXIT section 5b**, on the cluster. Then copy `~/LIBR-handoff-2026-10-23/` to a second disk.
- **Time Machine has no destination** (`tmutil destinationinfo`). Set one now. Materials,
  sessions, `.ink/`, the Colibri course's sources and the LIBR zips live only on the Mac disk.
- **The small iPad keyboard is the floating keyboard.** Pinch it outward with two fingers, or drag
  it to the bottom edge. A thin bar instead of keys means a hardware keyboard or Scribble is
  active.
- **For item 14:** create an Azure Speech resource and put `AZURE_SPEECH_KEY` and
  `AZURE_SPEECH_REGION` in `~/.config/tutor-board/keys.env`. Download the premium Tingting, Kyoko
  and Amélie voices in System Settings.
- **For item 9:** turn on Remote Login on the Mac mini, add the laptop's SSH key to it, and give
  `setup-mac.sh --coding` the Mac mini's tailnet name.
- **After the exit:** run `bash scripts/setup-mac.sh` once on every laptop clone, so the purged
  projects' leftovers go.
- **Read `board/TEACHING.md` once.** Every turn is told to follow it.
- **Keep `~/.elan`.** Its 2.7 GB v4.34.1 toolchain is reused by every Lean subject.
- **Before the cluster next pulls main,** check that `squeue -n mathlib` is empty. Then delete the
  ignored `projects/Lean-Theorem-Proving` there (about 14 GB of `.lake`) and on any laptop that
  has it. `subjects.walk` lists any directory under `projects/` as a subject.
- **In ai-config,** drop `workspaces/lean-theorem-proving.allow` and its `PERMISSIONS.md` rows.
- **Push ai-config's `update-tools` commit.** It puts each descriptor's `A_BIN_DIR` on the PATH,
  so a curl-installed opencode is updated. It is committed on ai-config's main, not pushed.
- **Tools on every machine.** Run `bash scripts/setup-mac.sh` twice on the Mac mini, and
  `bash scripts/setup-mac.sh --coding` twice on each laptop. The second run must
  end clean with `Brewfile.all unchanged`. The first installs mise, ghostscript and tesseract,
  and re-renders the tutor-board plist with mise's shims on its PATH.

## Loose ends in the code

- The past-lessons path is unreachable: `openHistory`, `showSession` and `#history` in
  `board/web/board.js`, and `GET /archive` in `board/tutorboard/server/routes/lesson.py`. Wire it
  to home's Past sessions, or delete it.

## On the glass

These are built but not yet used for real. Strike each one after an evening on the iPad.

- **Home:**
  - Continue rows, New session, the Courses and Projects lists, and "+ new".
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
    unanswered, because the last revise timed out. Let it finish, then End. End commits with no
    participant-scan refusal, and the ledger shows round 2 answered.
  - One document all the way round: Make, build, read, ink, "Say what's wrong", revise.
  - The round as pairs on the Colibri deck: tap the chip, a row and a pip, and mark pairs fine
    or not fixed.
  - Pinch-zoom on a paper and a deck in the one reader. Safari's page zoom never starts, ink
    stays on its words, and one finger scrolls a zoomed page sideways.
  - The notes canvas: a full-slate session whose End leaves a notes.md.
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

## The work it is for

Each item's open tasks live in its subject's TUTOR.md.

1. **Probability and Galois Theory homework**, with items 10 and 11 taking the friction out.
2. **The Colibri course** (`courses/Colibri`): the lesson from card 0048, and the pitch deck's
   rounds.
3. **Spirit-Forge:** Sparring spirit in Rust, then the Lean thread.
