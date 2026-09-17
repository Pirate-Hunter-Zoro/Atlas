#!/usr/bin/env bash
# ===========================================================================
#  tutor-serve.sbatch -- the allocation the board lives in, which renews itself.
#
#      tutor serve            submit the first generation  (this, with the
#                             partition, walltime and log the config names)
#      tutor serve status     which generation is up, where, and what it repaired
#      tutor serve stop       end the chain -- the flag AND the cancel
#
#  Before it does anything else, a generation submits the NEXT one with
#  `--dependency=afterany:<itself>`. That successor sits in the queue for the
#  whole walltime and starts the moment this job stops existing, for any reason:
#  the walltime, a node failure, a `scancel` of this job alone. So the board's
#  machine is renewed rather than lost, and the only thing that ends the chain is
#  something that means to -- `tutor serve stop`, or `scancel -u $USER`, which
#  takes the queued successor with it.
#
#  `afterany` and not `afterok`: a generation that crashed is exactly when the
#  next one is most needed.
#
#  Submit it by hand only from the repository root, and know that the log then
#  lands in the directory you submitted from. `tutor serve` passes an absolute
#  path under the state directory instead, because /tmp on a compute node is not
#  a place anybody can read from afterwards.
# ===========================================================================
#SBATCH --job-name=tutor-serve
#SBATCH --partition=c3_short
#SBATCH --time=09:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --signal=B:USR1@300
#SBATCH --open-mode=append
#SBATCH --requeue
#SBATCH --output=tutor-serve-%j.log

set -uo pipefail

# WHERE THE TOOL IS. Slurm copies a batch script into its own spool directory
# before running it, so `$0` here is that copy and a path derived from it points
# at nothing -- which is why this is handed over in the environment by whatever
# submitted the job. The fallback is the controller's own record of what was
# submitted, which is the original path, and is what a hand-submitted job gets.
TOOL="${TUTOR_BOARD_TOOL:-}"
if [ -z "$TOOL" ] && [ -n "${SLURM_JOB_ID:-}" ]; then
  said="$(scontrol show job "$SLURM_JOB_ID" 2>/dev/null \
          | sed -n 's/^ *Command=\([^ ]*\).*/\1/p' | head -1)"
  if [ -n "$said" ] && [ -f "$said" ]; then
    TOOL="$(cd "$(dirname "$said")/.." >/dev/null 2>&1 && pwd -P)"
  fi
fi
if [ -z "$TOOL" ] || [ ! -x "$TOOL/bin/tutor" ]; then
  echo "cannot find the board's own checkout from inside this job." >&2
  echo "TUTOR_BOARD_TOOL was '${TUTOR_BOARD_TOOL:-}' and scontrol did not help." >&2
  echo "NOTHING HAS BEEN QUEUED AFTER THIS, so the chain ends here: restart it" >&2
  echo "with 'tutor serve'." >&2
  exit 1
fi

# The tutor does not read stdin and nothing reads its stdout but this log.
# Everything else -- the successor, the tailnet, the boards, the tutors, the
# watch loop, the handoff when the walltime warning arrives -- is one command,
# because all of it has to be decided in one place and tested without a cluster.
#
# `exec`, so that this process IS the job's batch shell: `--signal=B:USR1@300`
# is delivered to that process, and a bash wrapper sitting in front of Python
# would eat the warning the handover depends on.
exec python3 "$TOOL/bin/tutor" serve inside
