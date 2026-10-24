#!/bin/bash
#SBATCH --job-name=p0t8b
#SBATCH --partition=c3_short
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=01:30:00
#SBATCH --output=logs/t8b_%j.out
#SBATCH --error=logs/t8b_%j.err
#
# FLEET-BUILD.md §9 tests 8b and 9: the standard helper on ONE A40 under
# 1/2/4/6/8 concurrent users, behind a 15k-token agent preamble.
set -uo pipefail
B=/media/studies/ehr_study/analysis/mferguson
MODEL=$B/models/vllm/Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit
export TMPDIR=$B/tmp
export HF_HUB_OFFLINE=1
export VLLM_LOGGING_LEVEL=INFO
export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-8}

# P0 finding 7: pip's writability probe is os.access(), and this Isilon
# synthesises the POSIX mode lossily from the real NFSv4 ACL, so os.access says
# the env is unwritable while an actual write succeeds. pip therefore
# "defaults to user installation" and 8.7 GB lands in ~/.local, which then
# SHADOWS the env at import time. PYTHONNOUSERSITE=1 is what actually settles
# it: it flips site.ENABLE_USER_SITE off, which pip checks before the probe.
export PYTHONNOUSERSITE=1

# P0 finding 8: there is no /usr/local/cuda on these nodes -- CUDA is a module.
# vLLM 0.29 defaults to the FlashInfer sampler, which JIT-COMPILES a CUDA kernel
# during warm-up and dies with "Could not find nvcc and default
# cuda_home='/usr/local/cuda' doesn't exist". CUDA_HOME fixes the lookup; the
# sampler is disabled anyway, because a kernel build inside the serving path is
# a cold-start hazard on a fleet whose whole promise is fast restarts.
module load CUDA/13.1.0 2>/dev/null
export CUDA_HOME=${EBROOTCUDA:-$CUDA_HOME}
export VLLM_USE_FLASHINFER_SAMPLER=0

# Keep every cache off the 100 GB home share, which is already 86% full.
export VLLM_CACHE_ROOT=$B/cache/vllm
export HF_HOME=$B/cache/hf
mkdir -p "$VLLM_CACHE_ROOT" "$HF_HOME"

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate $B/venvs/vllm_env

echo "node=$(hostname) job=$SLURM_JOB_ID gpus=$CUDA_VISIBLE_DEVICES start=$(date -Is)"
nvidia-smi --query-gpu=index,name,memory.total --format=csv,noheader
python -c "import vllm; print('vllm', vllm.__version__, 'from', vllm.__file__)"

T_START=$(date +%s)
vllm serve "$MODEL" \
  --served-model-name qwen3-coder-30b-a3b \
  --host 127.0.0.1 --port 8000 \
  --max-model-len 65536 \
  --gpu-memory-utilization 0.92 \
  --enable-prefix-caching \
  --tool-call-parser qwen3_coder --enable-auto-tool-choice \
  > logs/t8b_server_$SLURM_JOB_ID.log 2>&1 &
SRV=$!
trap 'kill $SRV 2>/dev/null' EXIT TERM

# readiness = the model answers, not that the socket is open
READY=0
for i in $(seq 1 180); do
  if curl -sf -m 3 http://127.0.0.1:8000/v1/models >/dev/null 2>&1; then READY=1; break; fi
  kill -0 $SRV 2>/dev/null || { echo "server died during load"; tail -40 logs/t8b_server_$SLURM_JOB_ID.log; exit 1; }
  sleep 5
done
[ $READY -eq 1 ] || { echo "server never became ready"; tail -60 logs/t8b_server_$SLURM_JOB_ID.log; exit 1; }
T_READY=$(date +%s)
echo "COLD_START_SECONDS=$((T_READY-T_START))"

python $B/fleet-p0/bench_tier1.py \
  --model qwen3-coder-30b-a3b \
  --tokenizer "$MODEL" \
  --preamble-tokens 15000 --max-tokens 500 \
  --levels 1,2,4,6,8 \
  --out $B/fleet-p0/results_t8b_$SLURM_JOB_ID.json
echo "bench rc=$?"
echo "done $(date -Is)"
