<!-- chapter: 1. THE TYPIST BAKE-OFF — VARY THE ASR MODEL -->
This was a DOING sitting on plan step 1, the typist bake-off. The stance was set
for the sitting only; the repository's standing answer is teach.

WHERE IT GOT TO. The bake-off has run end to end on the pilot session and has its
first number. `slurm_jobs/run_typist_bakeoff.sh` submits nine jobs: transcribe and
align per typist, then one CPU job joining every typist's words onto ONE
name-tagger's turn table and grading the lot. Stopwatch and name-tagger held fixed,
so the word columns move with the typist alone. Commits 5b6e060 and 7bcb37d. 125
tests pass. The grid is in planning/PSYCH-ASR_TODO.txt under step 1.

WHAT IT MEASURED. large-v3 1.4% WER, and its row reproduces the incumbent
community-1 row exactly, which is the split path's regression check passing on real
audio. large-v3-turbo 3.9%. parakeet 5.8%. The incumbent wins on words, and it is
not close.

THE ONE FINDING WORTH FOLLOWING. Parakeet has the BEST speaker column in the whole
grid -- 1.4% against 2.4-2.5% everywhere else. It emits 452 segments where
whisperx's VAD emits 121, and the finer segments give the Stage 1c join better
boundaries for its speaker labels. That is a result about segmentation, not words,
and nothing in the plan predicted it.

WHAT IS BROKEN. Canary transcribed 17.8 seconds of a 3038-second session and
stopped -- an attention encoder-decoder out of output length, not an attention-window
problem. It needs chunked inference. Its 100.5% row is a broken transcript, not a
word error rate, and must never be quoted as canary's.

TEACH THIS NEXT: the seam has no duration check. check_segment_contract passed
canary's one segment as well-formed because it does not know how long the audio was.
One argument and one comparison stops a typist writing a file that covers 0.6% of a
recording. It is small, it is the user's own decision to make, and the run just
showed why it matters.

There is no student reading yet this session -- the only signal was "begin", so
nothing is known about how they work.
