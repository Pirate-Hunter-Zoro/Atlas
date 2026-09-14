# PSYCH-ASR — the research journey

A plain-language narrative of this project: where it started, what we tried, what broke, what we
learned, and where it now stands. Written for a reader who wants the story and the current state
without reading the codebase.

`README.md` documents the pipeline architecture and carries no results. This file is its other
half — the narrative, the findings, and the reasoning behind them. Both live in this repository
now; until 2026-09-13 the narrative sat in a separate `Research-Journey` hub, which was retired so
that each project's writing, planning and documents live with the project they belong to.

The ordered task list is `planning/PSYCH-ASR_TODO.txt`, and it is the answer to "what do we do
next". The two sibling projects keep journeys of the same shape: `~/TRD-EHR/JOURNEY.md` for the
EHR prediction and counterfactual-selection papers, and `~/libr-local-llm/JOURNEY.md` for the
local LLM inference this project's on-prem constraint depends on.

---

## The slide decks

`docs/` holds this project's primary documents: two slide decks, each a `.tex` source plus its
built `.pdf`. Either is rebuilt with `pdflatex <name>.tex`, run twice so the outline resolves.

**`stage1_pipeline_walkthrough`** — how audio becomes a transcript, slide by slide, with the
input/output shape stated at every step. It was written against the since-retired single-job
script; the five calls it walks through now run as `psych_asr.cli.run_asr`, `diarize_pyannote`
and `join_speakers`.

**`stage2_reference_walkthrough`** — its sequel, *Did the Computer Hear It Right?*, and
deliberately the plainest document in the project. No term is used before it is explained in
everyday words, and the three Stage 1 models are called "the typist", "the stopwatch" and "the
name-tagger" throughout. Rewritten 2026-09-09 at 22 slides, 25 on 2026-09-10, **33 on
2026-09-11**; present tense throughout, no narration of past mistakes.

It covers the pipeline with **all three** boxes marked swappable; the 117-row human error log and
what its columns mean; how often each of the six labels occurs; the three shapes a row can take,
taught before the table that counts them; **the correction algorithm as six worked examples**,
each showing the literal spreadsheet row, the turns before, and the turns after; the two things
the reference cannot grade; then the model grid, which is a **cube** because three boxes are
swappable — 40 cells from 13 jobs.

**Part 5, new on 2026-09-11: grading the other 39 cells without listening to them.** Why the
answer key stands in for the audio, the three-pass order (line the words up blind, read the
cluster names off what matched, then classify), one worked pass emitting four findings on
invented lines, the single rule that reproduces her `Add Turn?` column, the frequency chart
redrawn two cells at a time, and the three things a computed grade cannot say. The example format
is deliberate and replaced a prose walkthrough that did not land.

Read the Stage 2 deck first if you want the state of the project in half an hour.

**Neither deck contains PHI.** The Stage 1 deck carries pipeline architecture and invented dummy
numbers only. The Stage 2 deck carries *real aggregate results* — turn counts, agreement
percentages, talk-time shares, how many spreadsheet rows applied — and no session content: its one
worked example of a corrected turn is invented dialogue, labelled as such on the slide, and no
participant code appears anywhere in it.

---

## The question on psychotherapy

Most NLP-for-clinical-outcome work runs on *text* interventions. This project starts from **spoken
psychotherapy session recordings** and asks whether we can, entirely on-prem: transcribe and diarize
them, extract early-session language / interaction / acoustic features, and use those features to
(a) predict treatment response *beyond* baseline severity and early symptom change, and (b) estimate
session- and item-level **therapist fidelity**. The near-term deliverable is not a clinical finding
but **feasibility data and reusable data-processing pathways** to support a grant application (R21,
possibly R01) for processing the full trial.

The feasibility framing is the whole point: the goal is not a perfect transcript but the ability to
**quantify transcript quality** (word- and diarization-error rates) and identify which feature types
stay reliable enough to trust despite ASR/diarization error.

## The hard constraint

Recordings are **identifiable PHI**, so every model — ASR, diarization, downstream NLP — runs
**locally on LIBR compute**. No audio, transcript, or derived feature ever leaves the node or touches
an external API. WhisperX and pyannote were chosen precisely because they run fully offline.

## The pilot

- Parent trial: ~70/group randomized; ~65–68/group attended at least one session.
- Pilot subset: **N≈20** from the behavioral-activation arm — 10 good responders, 10 poor.
- Scope: **sessions 1–3 only.** Powered for feasibility and pattern detection, not confirmatory
  prediction. At N=20, any responder/non-responder separation is hypothesis-generating for the
  grant, never a result.

## The make-or-break

The pilot recordings are a **single mixed mono channel**, so diarization cannot lean on channel
separation to tell therapist from patient. The whole project therefore lives or dies on one
question: can mono diarization separate the two speakers on *our* recordings? The plan builds
straight to **the first check that matters** — eyeballing a few minutes of diarized transcript
against the audio — before a single downstream feature is built.

## The pipeline

Stage 0 standardizes each recording to 16 kHz mono WAV. Stage 1 runs **WhisperX** (Whisper +
word-level forced alignment + pyannote diarization in one pass) into a speaker-labeled, timestamped,
confidence-scored transcript, plus a readable play-script rendering of the same content. Stage 2 is
human-in-the-loop QC: map anonymous speakers to therapist/patient, fix mid-session swaps, and
hand-correct a stratified subset to measure WER/DER. Stage 3 extracts features in reliability order.
Stage 4 asks whether those features separate responders from non-responders beyond baseline severity.

## Choosing a diarizer rather than inheriting one

(Added 2026-08-17.) pyannote's `community-1` is in place because WhisperX defaults to it, which is a
reason to start there and not a reason to stop there. Diarization is the bottleneck the whole project
is gated on, and three open-weight challengers now exist — BUT's **DiariZen** and NVIDIA's two
**Sortformer** checkpoints, one offline and one streaming — that model overlapping speech directly,
where community-1's configuration protects its speaker profiles by discarding overlapped regions
instead. In a corpus where therapist backchannels over patient speech are constant *and* are
themselves a structural feature, that difference is not incidental.

So the plan is a measured bake-off rather than an argument. Two things make it affordable. First,
Stage 2 already schedules a hand-corrected stratified subset to estimate WER and DER; that subset is
the test set, provided the correction covers speaker turns and not only words. Second, WhisperX's
speaker join turns out to read only three fields — start, end, speaker — off whatever diarization it
is handed, so any diarizer that emits a standard RTTM substitutes in with no change to the
transcription side at all.

That seam is what the accompanying refactor is built on: Stage 1 splits into ASR-plus-alignment,
diarization, and the join, exchanging RTTM between them. The motive is methodological rather than
economic — the whole job costs about three minutes on one A40, but re-running Whisper per candidate
would let the transcript vary across arms and confound the very comparison being run. Each competing
diarizer also pins its own `torch`, so each gets its own conda env, alongside a deliberately
torch-free scoring env: one scorer, one collar, every arm, or the exercise measures the scorer.

One constraint carries beyond the accuracy question. DiariZen's and offline Sortformer's *weights*
are CC BY-NC — fine for feasibility work at a nonprofit institute, awkward for something whose stated
deliverable is an R21/R01. Only the streaming Sortformer carries a license without that restriction.
Which arm wins and which arm can ship are two separate findings, and both get recorded.

## Measuring a diarizer nobody is allowed to read

(Added 2026-09-04.) The bake-off ran in August and produced an uncomfortable non-result: all five
arms recover the same two-speaker structure, the same 79/21 talk-time split, and agree with each
other on 99.3–99.7% of words. Session 1 is close to the easiest case diarization ever sees — two
people, clean turn-taking, one didactic speaker — which is exactly the regime where a model that
handles overlapping speech well has nothing to show for it. Nothing separates the arms, and the two
things that would are both out of reach: the collaborator's overlap-heavy recording has not
arrived, and scoring against truth needs a hand-corrected reference that does not exist yet.

Underneath that sits a constraint that is easy to state and shapes everything: **the assistant
helping with this project is not permitted to read any of its data.** Not as an instruction it
agrees to follow — as a hook that refuses the read. Transcripts, word-level alignments, speaker
turn tables, the rendered play-scripts, the raw audio, and even the arm-comparison file (which
quotes disputed transcript spans) are all closed to it. What stays open is deliberately narrow:
the pipeline code, the job logs, filenames and sizes, and the one artifact that holds nothing but
numbers — the scoring output. The mechanism lives in `libr-local-llm` and is documented there.

The obvious reading is that this makes the assistant useless on the one part of the project that
matters most. The more useful reading is that it forces a discipline the work wanted anyway: **the
thing that crosses back has to be a number.** Arranged that way, most of the ground-truth problem
turns out not to need the data at all.

Four routes, and only the last one actually scores the arms:

- **Calibrate the scorer with errors you put there yourself.** Today the scoring harness has been
  verified by scoring one arm against itself, which returns a perfect zero. That proves the
  identity case and nothing else — not that boundary error lands in the right bucket, not that a
  speaker swap is charged to confusion rather than to a deletion plus an insertion, not that the
  tolerance window behaves as claimed. Generating a turn table, corrupting it one way at a time by
  a known amount, and checking the scorer recovers each amount in the right component is a day's
  work, needs no audio, and can run on an entirely synthetic turn table — so it happens outside the
  fence entirely. This is the literal reading of a one-line note that had been sitting in the code
  repo: *reconstruct a true file with errors and use it as a ground metric.* Every number the other
  three routes produce passes through this scorer, so it goes first.
- **Build the overlap the recording was going to supply.** Two non-PHI voices, laid on a timeline
  with a known turn structure, mixed at a swept overlap fraction from zero to thirty percent. The
  reference is written by the mixer rather than by a human, so error is exact and free at every
  point on the sweep — which yields each arm's accuracy *as a function of overlap*, the precise
  claim the challengers exist to make and the one session 1 cannot test. It also settles whether an
  end-to-end model survives a long file, at any length convenient to synthesize. What it is not is
  therapy audio: one room, one microphone, real reverberation, real backchannels, real disfluency
  and the register of a clinical conversation are not reproduced by mixing read speech. It is a
  screen and a falsifier — an arm that fails on clean synthetic overlap will not do better on the
  real thing — and it is never the headline.
- **Two things that need no truth at all.** Re-run each arm under a perturbation that must not
  change the answer (a sub-second shift, a small gain change) and score it against its own first
  run: a model that disagrees with *itself* is unreliable wherever the truth lies, and the number
  compares across arms without anybody knowing it. And score each arm against the majority vote of
  the others — not accuracy, since all of them can be wrong together, but it names the outlier
  without a human. That last one bears directly on the single anomaly the August run turned up: the
  streaming Sortformer covers about 190 seconds more speech than every other arm, which is either
  better recall of quiet speech or false alarm, and it happens to be the only arm whose licence
  permits shipping.
- **The hand-corrected reference, which is still the only thing that decides.** Nothing above
  replaces it. What changes is who does what: the listening is human and cannot be delegated, and
  everything around it — pulling the audio for a chosen span, turning corrected boundaries back
  into a valid turn table, deriving the evaluation region, validating the reference before anything
  is scored, and reporting the whole thing back as counts — is assistant work that touches
  timestamps and never renders a word. The scarce resource here is human attention, so all of it
  gets built before anyone sits down with headphones.

Two judgements stay with the human and are not plumbing. **Which spans get corrected**: correcting
only the regions where the arms disagree measures where they *differ*, not where they are all
*wrong*, and biases the result in a direction no later discipline recovers — so the sample needs a
random spine that no model's output influenced. And **how the strata are weighted back together**:
if hard spans are oversampled, the pooled number is accuracy-on-the-hard-parts wearing a
session-level label, which is worse than reporting nothing.

## The road from a transcript to a prediction

A mentor meeting on **2026-08-13** turned four questions into what is now the concrete plan for
Stages 2–4. The plan's organizing principle is that the three feature families **fail
independently**, and they are ordered by how badly each one needs the transcript to be correct.

- **Structural features need only timestamps.** Talk-time ratio, turn counts and lengths, speech
  rate, pause structure, turn-taking latency, overlap and interruptions. A mediocre transcript does
  not touch them, which is why they are built first and why they are the features most likely to
  survive into the grant whatever the word error rate turns out to be. Getting the interruption
  family at all requires a change upstream, though: the raw pyannote **turn table** is currently
  computed and thrown away, and it is the only artifact in which overlapping speech survives — the
  joined transcript gives every word exactly one speaker by construction, so two people talking at
  once is structurally unrepresentable in it.
- **Acoustic and paralinguistic features read the raw waveform**, using the transcript only to say
  *where to look*. This is what answers the meeting's question about extracting tone per word:
  mechanically yes — forced alignment already placed acoustically-correct word boundaries, so pitch,
  loudness and duration can be read off any word — but with the caveat that a ~300 ms word is long
  enough to measure *emphasis* and far too short to measure *emotion*. Affect is a turn-level
  quantity, and the right output for it is continuous arousal/valence/dominance rather than discrete
  emotion labels. The whole lane runs off one acoustic pass per session at a 10 ms frame hop
  (openSMILE's eGeMAPS set, the standard in computational paralinguistics), aggregated afterwards at
  word, turn, or session granularity as each feature needs. One rule governs the entire lane: every
  prosodic feature is z-scored **within speaker within session**, because absolute pitch is mostly a
  fact about a person's vocal tract and comparing a therapist's raw F0 to a patient's is close to
  comparing their sexes.
- **Sighs, huffs, breaths and laughter get their own detector**, and deliberately not Whisper's.
  Whisper does sometimes emit bracketed non-speech tags, but they are suppressed by default and
  wholly dependent on what its training subtitles happened to annotate — that is not a measurement
  channel. An AudioSet-pretrained audio-event classifier is, and the AudioSet ontology contains
  exactly the categories at issue (*Sigh*, *Gasp*, *Breathing*, *Groan*, *Throat clearing*,
  *Laughter*, *Crying*). The design trick that makes it cheap and accurate is to run it **on the
  gaps rather than on the speech**: word timestamps already partition the session, sighs live in the
  silences, and classifying only the non-speech windows removes both most of the compute and the
  dominant false-positive source. This is a real clinical feature rather than a curiosity — an
  audible sigh is precisely the moment that would justify a therapist pivoting to grounding.
- **Behavioral and content coding is the LLM lane**, and the only one that genuinely depends on the
  words being right. The unit of analysis is the **therapist turn, not the session**: asking a model
  to score a 50-minute session on a fidelity scale yields one unverifiable number, whereas coding
  each turn yields hundreds of individually checkable judgments that aggregate into a session score
  with a known composition — and matches how human process-coding manuals are actually built, which
  is what makes agreement measurable at all. A turn is uncodeable out of context (whether an
  utterance is a *reflection* is defined relative to what the patient just said), so the prompt unit
  is a short window, not an isolated string. Serving reuses TRD-EHR's vLLM pattern wholesale —
  per-task servers publishing endpoint files, guided-JSON structured decoding, sharded SQLite
  judgment cache with a merge reduce — with prefix caching mattering *more* here than it did there,
  since the coding manual is a long shared prefix across every turn in the corpus. It has to run
  from a **separate conda env**: vLLM carries its own torch pin and would drag the whisperx-anchored
  ASR stack with it.

The meeting's remaining question — how to tell therapist from patient — became a Stage 2 design
item with a trap already identified. The intuitive heuristic ("the therapist talks less") **inverts
in session 1**, the didactic session where the therapist delivers the treatment rationale, so a
talk-time rule would be confidently wrong on a third of the pilot corpus. What does discriminate is
lexical and compared *between the two speakers within a session* rather than against any absolute
threshold: second-person versus first-person-singular pronoun rates (the strongest cue, and robust
to word error because function words are what ASR gets right), question rate, whole turns that are
nothing but backchannels, turn-initial agenda-framing moves, and treatment-manual vocabulary. The
output is a **proposal carrying its own evidence**, confirmed by the human who is doing QC anyway —
never a silent auto-assignment. Its accuracy against the 60 human labels is then itself a
feasibility result, because it is the difference between "someone must listen to every session" and
"someone must spot-check."

Finally, Stage 4 is governed entirely by N=20. The feature set has to be cut to single digits
*before* modeling and chosen on reliability evidence rather than by searching for separation; the
10-good/10-poor design is **extreme-group sampling**, which inflates apparent effect sizes relative
to the parent trial, so anything measured here is a power input for the R21 rather than an estimate
of the effect the full study would see; and "beyond baseline severity and early symptom change" is a
nested-model claim that twenty participants cannot credibly power — the honest form reports the
marginal and partial associations with intervals and says plainly that the incremental claim is what
the grant is for.

## Where the time went (and the traps already paid for)

- **Offline compute nodes.** The login node has internet; the `c3_accel` compute nodes generally do
  not — a download attempted on a compute node hangs until the wall-clock kills it. Every model is
  pre-staged once where there is internet and loaded by absolute path with `HF_HUB_OFFLINE=1`.
  (One node was later observed to reach the Hub anyway; the pre-staging discipline stands regardless,
  since a node's connectivity is not something a job should ever depend on.)
- **`HF_HUB_OFFLINE` does not cover everything.** WhisperX's English forced-alignment model is *not*
  a HuggingFace artifact — it is a torchaudio bundle fetched from `download.pytorch.org` into the
  Torch cache. It slips straight past the HuggingFace offline guard, so it has to be warmed
  separately and given a persistent `TORCH_HOME` on study storage. There turned out to be a
  *third* such leak: the alignment step also loads NLTK sentence-splitter data and silently
  falls back to downloading it. Each library consults its own environment variable, so "offline"
  is not one switch but three, and every job must export all of them.
- **The pyannote 3.1 dead-end.** pyannote.audio 4.x loads a PLDA component unconditionally, which the
  classic `speaker-diarization-3.1` config predates, so it dies offline. The fix is the
  self-contained `speaker-diarization-community-1` model (WhisperX 3.8.6's default anyway).
- **The venv ACL trap.** The study-storage venvs directory reports itself unwriteable to `pip` even
  though real writes succeed, so pip silently falls back to a `--user` install and scatters the stack
  into the wrong place; setting `PYTHONNOUSERSITE=1` before every pip/sbatch is mandatory.
- **GPU stack validated.** The cu12 Torch 2.8 wheel and ctranslate2 float16 both run on an A40 under
  Slurm with no segfault; `stage1_whisperx.sbatch` is the job scaffold to clone.
- **A rule that has to be remembered is not a control.** (Added 2026-09-04.) Recording filenames
  carry participant session codes, so the project's oldest hard constraint is that a code never
  enters a tracked file. It was written down twice and broken twice — once before the first push,
  and again in the August bake-off writeup, which reached the *public* code repository and sat
  there for eleven days. Both histories were rewritten and force-pushed on 2026-09-04, and both
  repositories now refuse the commit outright: a pre-commit hook blocks any staged filename or
  added line carrying the pattern. The lesson is not "be more careful" — the previous fix was
  being more careful, and it failed the same way. Anything pre-2026-09-04 cloned from either repo
  is stale and must be re-cloned rather than pulled.

## Status on psychotherapy

- **Stage 0:** done — a standardizer script and a proven pilot WAV on disk.
- **GPU + offline scaffold:** done and validated.
- **Diarization weights:** done (2026-08-07) — the gate was already accepted, but the download had
  silently half-failed, leaving empty model subfolders behind. Re-staged in full and confirmed to
  load offline as a `SpeakerDiarization` pipeline with no network reach.
- **Model staging:** done (2026-08-10) — the full-size ASR checkpoint, the torchaudio
  forced-alignment bundle, and NLTK's sentence-splitter data are all on study storage, each
  confirmed by an actual offline load rather than by the directory existing. A single staging
  script now performs all three on the login node.
- **Stage 1 (WhisperX run):** **built and run clean on a full ~50-minute session** (2026-08-12).
  All four passes — ASR, forced alignment, diarization, and the readable render — are written,
  reviewed, and documented, and the whole job takes roughly three minutes of wall clock on one A40,
  so the two-hour request is generous by orders of magnitude and GPU memory never had to be freed
  between passes. The output covers the audio end to end with exactly two speaker labels and
  essentially no unattributed speech. That validates the plumbing and shows diarization produced a
  *plausible* two-speaker structure; it does not validate accuracy, which is what the listening
  check below is for.
- **Stage 1 walkthrough documentation:** done (2026-08-12) — `docs/` now holds a
  slide deck explaining the Stage 1 script component by component, with input/output shapes at every
  step and dummy worked examples, and the script itself carries matching shape annotations. It exists
  because the pipeline was becoming a black box its own author could not reason about: three separate
  models, three separate representations of the same audio, and one widely-held misconception worth
  killing in writing — diarization does **not** reuse anything Whisper computed. It re-reads the raw
  waveform, converts each speech region into a fixed-length "voice fingerprint" vector, and clusters
  *those*. Voice identity is independent of words, which is why the two halves never need to meet
  until the final timestamp join.
- **Human-readable transcript rendering:** done (2026-08-12) — the diarized JSON is unreadable
  against playing audio, so the pipeline also emits a play-script text file: one timestamped block
  per speaker turn, with a summary header carrying per-speaker talk time and share of speech.
  Unattributed segments are printed as `UNKNOWN` rather than hidden, because a cluster of them is
  itself the diagnostic that diarization under-covered the audio. The talk-time split in that header
  is the cheapest possible collapse detector — two people in a room do not split 97/3 — so a failed
  clustering is visible from the job log before anyone opens the audio.
- **The mono-diarization viability check:** **not yet done — this is the active blocker.** The
  artifact is written and waiting; what remains is a human reading a mid-session stretch of it
  against the recording. The crude failure is already ruled out by the header. Only listening rules
  out the subtle one: labels that are internally consistent but attached to the wrong person, or a
  quiet mid-session swap where one label becomes the other. The opening minutes are worthless as a
  test — greeting and small talk with clean turn-taking is the easiest case diarization ever sees.
- **The overlapping-speech stress test:** **pending a recording from a collaborator** (expected as
  of 2026-08-13). The first pilot session is close to the easy case; a session with substantial
  simultaneous speech is the real test of mono diarization. Two things want to be true before it
  arrives so that processing it is turnkey — the turn table is being persisted (without it an
  overlap test cannot be scored at all), and the expected failure mode is written down in advance,
  since overlap will *not* appear as dual-labeled words but as words attributed to the wrong
  speaker, words masked out of the ASR entirely, and turn boundaries in the wrong place. Judging the
  run against the wrong expectation would read a transcript artifact as a diarization failure or the
  reverse.
- **The diarization bake-off:** **built and run end to end** (2026-08-23). Stage 1 was split into
  ASR-plus-alignment, diarization, and the join so that all five arms sit on one identical word
  sequence; four conda environments, five arm scripts, the join, a regression gate, the word-level
  arm diff and the scoring harness all exist and have executed on the full first session. The split
  reproduced the pre-split fixture byte-identically, so differences between arms are attributable to
  the diarizers rather than to the refactor. **No arm is scored yet**, because scoring needs a
  reference and there is none. What the run did settle: the offline Sortformer survives a 50-minute
  file only through windowing it itself, DiariZen can be pinned to two speakers but not through the
  argument that looks like the right one, and the streaming Sortformer covers ~190 s more speech
  than every other arm — which is either better recall or false alarm and cannot be told apart
  without truth.
- **The ground-truth strategy:** **designed 2026-09-04, none of it built.** Four routes, three of
  which need no reference and two of which need no audio; the section above is the account. The
  order is settled even though the work is not: calibrate the scorer against injected errors first,
  because every other number runs through it.
- **Stages 2–4 (QC/metrics, features, modeling):** designed but not started — gated on the viability
  check. The design is the roadmap above; the architecture is documented in `PSYCH-ASR/README.md`
  and the ordered task list in `planning/PSYCH-ASR_TODO.txt`.

---

## Current state at a glance

| | PSYCH-ASR |
| --- | --- |
| **Core question** | Can we transcribe/characterize therapy sessions to predict response + fidelity? |
| **Pipeline** | Stages 0–1 built and run clean on a full session; Stage 1 since split into ASR/diarize/join and a five-arm diarization bake-off built and run end to end (2026-08-23), with the turn table now persisted as RTTM — but **no arm scored**, because there is no reference. A four-route ground-truth strategy is designed as of 2026-09-04 and none of it is built. Stages 2–4 designed, not started |
| **Headline result** | None yet — pre-feasibility |
| **Manuscript** | N/A — feasibility data for an R21/R01 grant |
| **Immediate next step** | **ACTIVE** — the mono-diarization viability check (listen to a mid-session stretch against the transcript) is still the human blocker and nothing replaces it. In parallel, and needing neither audio nor a reference: calibrate the scoring harness against injected errors of known size (its only verification today is scoring an arm against itself, which proves the identity case and nothing else), then split the arm-diff writer so a numbers-only summary crosses the PHI fence. The synthetic overlap sweep is the route that stops the bake-off waiting on a collaborator's recording |

The sibling projects' columns of this table live in their own journeys:
`~/TRD-EHR/JOURNEY.md` and `~/libr-local-llm/JOURNEY.md`.
