#!/bin/bash
set -euo pipefail
B=/media/studies/ehr_study/analysis/mferguson
export TMPDIR=$B/tmp
export PYTHONNOUSERSITE=1
source "$(conda info --base)/etc/profile.d/conda.sh"
if [ ! -d "$B/venvs/vllm_env" ]; then
  conda create -y -p "$B/venvs/vllm_env" python=3.12
fi
conda activate "$B/venvs/vllm_env"
python -V
# --no-user is load-bearing on this filer: pip's os.access() writability probe
# reads the POSIX mode, which the Isilon synthesises lossily from the real
# NFSv4 ACL, so pip decides the env is unwritable and silently installs into
# ~/.local instead — 8.7 GB onto a 100 GB home share. See README.md trap 25.
pip install --no-user --upgrade pip
pip install --no-user vllm
python -c "import vllm, torch; print('vllm', vllm.__version__, 'torch', torch.__version__, 'cuda', torch.version.cuda); print('from', vllm.__file__)"
