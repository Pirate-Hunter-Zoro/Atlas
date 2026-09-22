<!-- chapter: 1. STAGE 1 — THE DIARIZATION GRID -->
The work in front of this project is expanding the Stage 1 diarization pipeline into a grid
search. Stage 1 runs end to end: 1a-i transcribe, 1a-ii align, 1b one job per arm, 1c join
and render, with the regression gate closing the 1c job. A grid cell is a typist, a
stopwatch and a name-tagger, and the arm name carries all three in the filename, so the
grid needs no new artifact convention — see *The arm name is what makes the model grid
free* in `psych_asr/artifacts/naming.py`.

### The reference transcript, and why it is not in here

The reference is a **human-adjudicated artifact**. colibrì produced it from the community-1
baseline transcript and the annotator's QC error log; the annotator reviewed the result and
approved it. It is the reference because she says it is.

It lives under `phi/`, which is outside git and inside the PHI fence. Every downstream
number therefore rests on a file git cannot see and no assistant working here can read.
Nothing in `psych_asr/` builds it, reads it, or reproduces it.

**How an arm is measured against it is an open decision**, and it waits on the reference
being validated. It may not turn out to be code.

### Where to pick up

`planning/PSYCH-ASR_TODO.txt` is the live task list and the answer to "what do we do next".
`README.md` is the pipeline architecture. Read the TODO first.
