# Lean Theorem Proving

## Where things are

- Lean 4 with Mathlib. Exercises/<Topic>/ENN_Name.lean holds one exercise each, imported by Exercises.lean. exercises.tsv is the order of study (order, topic, module, title).
- An exercise's status is whether its file still contains sorry; scripts/status.sh prints it, and scripts/new-exercise.sh adds a file and its row.
- LeanTP/ holds shared definitions and tactics. scripts/build.sh is the build, and slurm_jobs/build_mathlib.sbatch builds Mathlib on the cluster.

## Now

All 26 exercises in exercises.tsv still contain sorry.

## Open decisions

## Done recently
