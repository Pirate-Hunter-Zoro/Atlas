#!/bin/bash
#SBATCH --job-name=mathlib
#SBATCH --partition=c3_short
#SBATCH --time=09:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=92
#SBATCH --mem=256G
#SBATCH -o slurm_jobs/build_mathlib_out.txt
#SBATCH -e slurm_jobs/build_mathlib_err.txt

# ---------------------------------------------------------------------------
# Compile Mathlib from source, then the exercises.
#
# Why this exists: Mathlib normally comes prebuilt and `lake exe cache get`
# downloads it in minutes. That cache lives on Azure Blob Storage
# (lakecache.blob.core.windows.net), and this cluster's egress filtering accepts
# the TCP connection but drops the TLS handshake — so `cache get` hangs forever
# on the handshake instead of failing. Compiling from source is the way around
# it, and on a 96-core node it is a one-time cost of tens of minutes.
#
# The build is INCREMENTAL. Re-running after an interruption resumes from the
# artifacts already in .lake/ rather than starting over, so this job is safe to
# resubmit. It only does real work again when Mathlib is bumped.
#
# Submit from the repository root:  sbatch slurm_jobs/build_mathlib.sbatch
# ---------------------------------------------------------------------------

set -e

REPO="/home/librad.laureateinstitute.org/mferguson/Lean-Theorem-Proving"
cd "$REPO"

# elan is Lean's toolchain manager; it reads lean-toolchain and selects the
# compiler version this project pins (must match Mathlib's own pin).
export PATH="$HOME/.elan/bin:$PATH"

# Let Lake use every core the job was allocated.
export LEAN_NUM_THREADS="${SLURM_CPUS_PER_TASK}"

echo "host:      $(hostname)"
echo "started:   $(date '+%F %T')"
echo "toolchain: $(cat lean-toolchain)"
echo "cores:     ${SLURM_CPUS_PER_TASK}"
echo

# Do not let a failing build abort the script: a build that fails on one
# exercise still needs the status report below, which is the whole point of the
# run. Record the exit code, always report, then exit with it so Slurm still
# marks a genuine failure as FAILED.
set +e
lake build
build_status=$?
set -e

echo
echo "finished:  $(date '+%F %T')"
echo "lake build exit status: ${build_status}"
echo
echo "--- exercise status ---"
bash scripts/status.sh

exit "${build_status}"
