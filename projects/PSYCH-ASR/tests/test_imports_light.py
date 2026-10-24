"""The grid's driver, join, preflight and plan import without any model library.

They run on a login node, in the driver's one-CPU job and in a test, so a top-level
whisperx or torch import would cost a GPU env's start-up -- or fail outright.
"""

from psych_asr import config  # noqa: I001  -- first, as conftest explains

import subprocess
import sys

HEAVY = ("whisperx", "torch", "torchaudio", "nemo", "transformers")
MODULES = ("psych_asr.grid", "psych_asr.preflight", "psych_asr.cli.grid_submit",
           "psych_asr.cli.join_grid", "psych_asr.cli.preflight_models")


def test_grid_modules_import_no_model_library():
    code = (
        "import importlib, sys\n"
        f"for name in {MODULES!r}:\n"
        "    importlib.import_module(name)\n"
        f"print(sorted(m for m in {HEAVY!r} if m in sys.modules))\n"
    )
    out = subprocess.run([sys.executable, "-c", code], cwd=str(config.WORKSPACE_ROOT),
                         stdout=subprocess.PIPE, universal_newlines=True, check=True).stdout
    assert out.strip() == "[]"
