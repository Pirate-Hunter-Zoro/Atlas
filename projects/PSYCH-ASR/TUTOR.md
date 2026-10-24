# PSYCH-ASR

## Where things are

- Code in psych_asr/, jobs in slurm_jobs/, submitted from the subject root. slurm_jobs/stage1_grid.sbatch runs the grid (psych_asr/cli/grid_submit.py), one output directory per run; run_bakeoff.sh is the single-typist path the regression gate uses.
- Stage 1: 1a-i transcribe in the typist's env to `<stem>.<typist>.asr.json`; 1a-ii align (asr_env) to `<stem>.<typist>+<stopwatch>.aligned.json`; 1b one diarizer per arm to `<stem>.<arm>.rttm`; 1c join, no GPU. A grid run writes under `stage1/grid-<id>/`; run_bakeoff.sh writes `<stem>.aligned.json` in stage1/. Regression fixture: 1a, 1b with community-1, 1c reproduces job 2032471 exactly (489 segments, 7298 words, 2 speakers, 89 turns, 1 UNKNOWN segment).
- asr_env's pins are locked to whisperx 3.8.6; never bump one alone. diarizen_env, nemo_env and diar_eval_env are separate on purpose. Every job sets PYTHONNOUSERSITE=1 and HF_HUB_OFFLINE=1; models are pre-staged and loaded by path.
- docs/stage1_pipeline_walkthrough.pdf is the Stage 1 lesson, already taught. Point at it; do not re-teach.

## Now

Owner, 2026-09-21: the reference transcript is closed. What is next is the grid: expand Stage 1 into the sweep of typists, stopwatches (aligners) and name-taggers (diarizers), every cell run and its output kept. Running the arms, not judging them.

The grid is a cube: 4 typists x 2 aligners x 5 diarizers is 40 cells from 17 GPU jobs (4 transcribe, 8 align, 5 diarize) and one join, because diarization reads no words. Never rerun diarization per typist. A cell's arm name carries the triple (artifacts/naming.py).

- [ ] Walk the owner through docs/HANDOFF.md: stage, preflight, dry run, then the grid.
- [ ] Add a duration check to the 1a seam: check_segment_contract takes the audio duration and fails a typist whose last segment ends far short of it.
- [ ] Canary transcribes only the first 17.8 s of a session. Chunked inference would fix it, if canary is worth that work.
- [ ] Build the reference RTTM: re-align the reference transcript's words to the audio and write measured word times, with a UEM. The job reads the reference locally and prints counts only. No timing number is trustworthy before it.
- [ ] Then compare two aligners on the same words: the grid's second stopwatch, the large wav2vec2 bundle (WAV2VEC2_ASR_LARGE_LV60K_960H), against the base one. Ask the owner before writing anything that compares.
- [ ] The owner's own: listen to the recording beside its diarized transcript, mid-session. Do the labels flip at the right moments and stay consistent?
- [ ] Retain no_speech_prob in 1a (one generate argument) and compute compression_ratio from the text already written.

Waiting on other people: the overlap-stress recording (a collaborator's), the bake-off's real test; and the annotator's repair of error-log rows 16, 32, 62, 41, 50, 53 and 75.

Later, once measurement is settled: talk-time split against the reference's 78.6/21.4 (after the reference RTTM, or against its word share); whether each arm has a turn boundary near the 53 backchannels the baseline missed; the overlap recording's chunk_size experiment (30 s against 15 s); Stage 2's role-assignment proposal with its evidence in the header, never silent; then Stages 3a, 3b, 3c and 4.

## Open decisions

- How an arm is measured against the reference. It blocks every number and waits on the reference being validated; it may be a colibri pass rather than code.
- Which diarization arm. Record which wins and, separately, which can ship: arms A and B carry non-commercial weights, and C is the only strong one that does not.
- Is canary-1b-flash worth chunked inference, given parakeet already covers the NVIDIA design.
- Stage 3c: which model (decide by measured agreement) and which coding manual (a team decision).
- How large each human-coding subset is; whether video features are in scope.

## Done recently

- The reference transcript: colibri built it from the community-1 baseline and the annotator's error log, and she approved it. It lives under phi/. The correction algorithm, error-log reader, grader and scorers are deleted.
- Typist run, 2026-09-13: all four typists ran on the pilot session, every licence permissive. Parakeet segments far finer than whisperx (452 against 121). Both NVIDIA typists run a 50-minute file only with local attention.
- Bake-off, 2026-08-23: every arm agrees on 99.3-99.7% of words, so session 1 cannot decide it. Sortformer cannot be pinned to 2 speakers; DiariZen's label 0 is a phantom; arm C covers about 190 s more speech than the rest.
- The grid driver: stage1_grid.sbatch, 40 cells from 17 GPU jobs and one join, one output directory per run.
