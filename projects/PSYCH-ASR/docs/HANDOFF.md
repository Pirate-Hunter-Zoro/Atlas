# The owner's cluster steps for the Stage 1 grid

The tutor walks the owner through this one step at a time. The owner's part is steps 1 to 4, on
the LIBR login node, plus the hand submission in step 5 only if the relay never answers.
Everything else is filed from the iPad. The grid runs 40 cells (4 typists,
2 stopwatches, 5 name-taggers) and keeps every output. Nothing in it scores, compares or ranks
an arm.

## 1. Confirm the build reached the cluster

The build is on origin. The relay fast-forwards the cluster checkout on every pass, about every
2 minutes, so the owner never pulls by hand. On the login node, this must show a commit whose
subject starts `PSYCH-ASR: Stage 1 grid`:

```bash
git -C ~/Atlas log --oneline -3
```

## 2. Token and gate, only if community-1 is not staged

`pyannote/speaker-diarization-community-1` is the one gated repo, and staging asks for a token
only when its directory is missing or empty. Check first:

```bash
ls -A /media/studies/ehr_study/analysis/mferguson/models/pyannote-speaker-diarization-community-1 2>/dev/null | head
```

A list of files means it is staged; skip to step 3. Nothing printed means:

1. **Make a read token.** At <https://huggingface.co/settings/tokens>, create a token of type
   *Read*.
2. **Put it in the `.env` the staging script reads.** The file is git-ignored; never commit it.
   Type the token into the file, not into the shell: the script sources `.env` with auto-export
   so `hf` inherits it, and a token set in the shell without export never reaches the download,
   which then fails 401.

   ```bash
   cd ~/Atlas/projects/PSYCH-ASR
   nano .env                 # one line: HF_TOKEN=hf_...
   chmod 600 .env
   git check-ignore .env     # must print .env
   ```

3. **Accept the gate.** Logged in as the token's account, open
   <https://huggingface.co/pyannote/speaker-diarization-community-1> and click
   *Agree and access repository*. Access is instant. Accept community-1, not
   `pyannote/speaker-diarization-3.1`: 3.1 does not load offline on pyannote.audio 4.0.7, whose
   pipeline needs a PLDA model the 3.1 config predates.

Every other repo the script stages has no gate:

| Repo | Gate | Weights licence |
| --- | --- | --- |
| [pyannote/speaker-diarization-community-1](https://huggingface.co/pyannote/speaker-diarization-community-1) | **click-through** | CC BY 4.0 |
| [pyannote/wespeaker-voxceleb-resnet34-LM](https://huggingface.co/pyannote/wespeaker-voxceleb-resnet34-LM) | none | CC BY 4.0 |
| [Systran/faster-whisper-large-v3](https://huggingface.co/Systran/faster-whisper-large-v3) | none | MIT |
| [deepdml/faster-whisper-large-v3-turbo-ct2](https://huggingface.co/deepdml/faster-whisper-large-v3-turbo-ct2) | none | MIT |
| [nvidia/parakeet-tdt-0.6b-v2](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v2) | none | CC BY 4.0 |
| [nvidia/canary-1b-flash](https://huggingface.co/nvidia/canary-1b-flash) | none | CC BY 4.0 |
| [BUT-FIT/diarizen-wavlm-large-s80-md-v2](https://huggingface.co/BUT-FIT/diarizen-wavlm-large-s80-md-v2) | none | CC BY-NC 4.0 |
| [nvidia/diar_sortformer_4spk-v1](https://huggingface.co/nvidia/diar_sortformer_4spk-v1) | none | CC BY-NC 4.0 |
| [nvidia/diar_streaming_sortformer_4spk-v2.1](https://huggingface.co/nvidia/diar_streaming_sortformer_4spk-v2.1) | none | NVIDIA Open Model License |

## 3. Stage (login node)

```bash
cd ~/Atlas/projects/PSYCH-ASR
bash scripts/stage_models.sh
```

- **Staged directories are kept.** Each prints `kept <name> (already staged; delete it to
  re-fetch)`, because `hf download` resolves to the latest revision and would move the weights
  earlier runs used.
- **The skip trusts any non-empty directory.** A download that died can leave only README.md
  and empty weight folders, and the skip keeps that too. Step 4 catches it.
- **Two caches are not Hugging Face, and need no token.** Both torchaudio stopwatch bundles come
  from download.pytorch.org into `models/torch_home`. The base bundle (360 MB) is reused; the
  large one (about 1.2 GB) is the new download. nltk's `punkt_tab` is re-warmed.
- Each bundle prints a block ending `Checkpoint <file> in TORCH_HOME: yes`.
- The script creates `slurm_jobs/logs/`, which Slurm needs and git ignores, then runs the
  preflight with `--load` and exits with its status.

## 4. Read the preflight

A pass prints 15 asset lines, all starting `ok`, then `loaded` lines and `load not attempted`
lines for NeMo and DiariZen (those need their own envs; expected). The last line is:

```text
RELAY: preflight assets 15 ok 15 empty 0 missing 0 incomplete 0 load-failed 0 inbox-wav 1
```

Anything else stops here:

- **`empty` or `incomplete`.** A partial download. Delete that one directory (its path is on its
  asset line) and rerun step 3.
- **`missing stopwatch wav2vec2-large` after a block that said `in TORCH_HOME: NO`.** The cache
  filename in `config.STOPWATCH_CHECKPOINTS` differs from torchaudio's. The tutor fixes the
  code; the owner does nothing.
- **`load-failed <axis> <name> <ExceptionType>`.** The tutor's to diagnose from that line.
- **`missing shared <env>`.** That conda env is not built: `bash scripts/setup_envs.sh`.
- **`inbox-wav` other than 1, or `data root PSYCH_ASR_DATA does not exist`.** Every grid job reads
  the one session WAV in the inbox of the fenced data directory inside this checkout. The owner,
  and nobody else, puts exactly one .wav in ~/Atlas/projects/PSYCH-ASR/phi/inbox/.

Rerun only the check, with no `.env` and no download:

```bash
bash scripts/stage_models.sh --check
```

## 5. Launch (the tutor, through the relay)

The dry run first. It uses no GPU and submits nothing. It is the subject's first relay round
trip, proves `job_env.sh` finds the data root, and runs the file-tier preflight from a compute
node:

```bash
board job -- slurm_jobs/stage1_grid.sbatch GRID_DRY_RUN=1
```

A healthy report ends:

```text
RELAY: preflight assets 15 ok 15 empty 0 missing 0 incomplete 0 load-failed 0 inbox-wav 1
RELAY: grid plan typists 4 stopwatches 2 taggers 5 cells 40
RELAY: grid dry run jobs 18
```

Then the grid:

```bash
board job -- slurm_jobs/stage1_grid.sbatch
```

- **Subsets** take colon lists: `GRID_TYPISTS` (large-v3, large-v3-turbo, parakeet, canary),
  `GRID_STOPWATCHES` (wav2vec2-base, wav2vec2-large), `GRID_TAGGERS` (community-1, diarizen,
  diarizen-free, sortformer, sortformer-streaming). Re-file a failed arm as a subset, not the
  whole grid.
- **One driver at a time.** A second is refused with `RELAY: grid refused: another grid driver
  is running`.
- **If only the join died**, re-join that run's kept inputs without any GPU job. Pass the same
  `GRID_*` subsets the run had, and leave the same WAV in the inbox:

  ```bash
  board job -- slurm_jobs/stage1_grid.sbatch GRID_REJOIN=<driver job id>
  ```

- **Only if the relay never answers**, the owner submits the driver by hand:

  ```bash
  cd ~/Atlas/projects/PSYCH-ASR && sbatch slurm_jobs/stage1_grid.sbatch
  ```

## 6. While it runs

The driver (CPU, c3_accel, no GPU) submits 18 jobs and polls `squeue` every 2 minutes:

- 4 transcribe and 8 align jobs, each with a 2 h limit. An align waits for its own typist, and
  is cancelled if that typist failed.
- 5 diarize jobs, each with a 2 to 4 h limit, waiting on nothing.
- 1 CPU join, after every align and diarize has ended, however it ended.

The 17 GPU jobs share c3_accel's GPUs, so they run a few at a time. `squeue -u $USER` shows the
driver and up to 18 children. Leave the inbox alone until the driver ends: every job reads its
one WAV.

## 7. Where everything lands

Outputs go in the fenced data directory, under `stage1/grid-<driver job id>/`. No run touches
an earlier run's files.

| Files | Count |
| --- | --- |
| `<stem>.<typist>.asr.json` | 4 |
| `<stem>.<typist>+<stopwatch>.aligned.json` | 8 |
| `<stem>.<tagger>.rttm`, plus community-1's `.exclusive.rttm` | 5 + 1 |
| `<stem>.<typist>+<stopwatch>+<tagger>.diarized.json` and `.transcript.txt` | 40 each |

Logs, `jobs.tsv` (each job's key, role and id) and `manifest.json` (per-input states and
per-cell counts, no stem, no text) go to `slurm_jobs/logs/grid-<driver job id>/`. The driver's
own log, which the relay reads, is `slurm_jobs/logs/stage1_grid_<driver job id>_out.txt`.

A healthy report ends:

```text
RELAY: grid plan typists 4 stopwatches 2 taggers 5 cells 40
RELAY: grid inputs asr 4 of 4 aligned 8 of 8 rttm 5 of 5
RELAY: grid cells 40 joined 40 missing 0 failed 0
```

- **A crashed upstream job** shows above those lines as `RELAY: grid <asr|aligned|rttm> <arm>
  missing` and makes its cells `missing`. That is reported, not fatal: the job fails only when a
  join raised or no cell joined.
- **A failed cell** shows as `RELAY: grid cell <cell> failed <ExceptionType>`.
- **Canary's cells cover only the first 18 s or so** of the session. That is a known limit of
  the typist, not a failure.
