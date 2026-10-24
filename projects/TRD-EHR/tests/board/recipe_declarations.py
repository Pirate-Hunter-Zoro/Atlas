"""The project's relay recipes declare their accepted arguments."""
from pathlib import Path
import sys
root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root.parents[1] / "board"))
from tutorboard import jobs
for name, wanted in (("neighbor_count_sweep", ["EMBEDDER", "REDRAW"]),
                     ("diagnose", ["EMBEDDER", "LOOK", "MODULE"])):
    names, problems = jobs.declarations((root / "slurm_jobs/quick_runs" / (name + ".sbatch")).read_text())
    assert not problems and sorted(names) == wanted, (name, names, problems)
assert jobs.diagnostics(str(root)) == [("slurm_jobs/quick_runs/diagnose.sbatch", ["EMBEDDER", "LOOK", "MODULE"])]
print("recipe declarations pass")
