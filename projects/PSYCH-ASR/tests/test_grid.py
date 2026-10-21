"""The grid's plan, its sbatch commands, its driver and its RELAY: lines. No Slurm, no models."""

from psych_asr import config  # noqa: I001  -- first, as conftest explains

import os
import re
import shlex
import subprocess
import sys
import types
from pathlib import Path

import pytest

from psych_asr import grid
from psych_asr.asr import typists
from psych_asr.cli import grid_submit

ROOT = Path(config.WORKSPACE_ROOT)
STEM = "SESSIONX"


# ---- axes and cells ----

def test_forty_unique_cells_named_by_their_three_axes():
    all_cells = grid.cells(grid.TYPISTS, grid.STOPWATCHES, tuple(grid.NAME_TAGGERS))
    names = [c.name for c in all_cells]
    assert len(names) == 40 and len(set(names)) == 40
    for cell in all_cells:
        assert cell.name == f"{cell.typist}+{cell.stopwatch}+{cell.tagger}"
        assert cell.half == f"{cell.typist}+{cell.stopwatch}"
        assert "." not in cell.name and cell.name.count("+") == 2


def test_cells_come_in_canonical_order():
    all_cells = grid.cells(grid.TYPISTS, grid.STOPWATCHES, tuple(grid.NAME_TAGGERS))
    assert all_cells[0] == (grid.TYPISTS[0], grid.STOPWATCHES[0], config.ARM_BASELINE)
    assert [c.typist for c in all_cells[:10]] == [grid.TYPISTS[0]] * 10


def test_select_keeps_canonical_order_and_splits_colon_lists():
    assert grid.select(None, grid.TYPISTS, "typist") == grid.TYPISTS
    assert grid.select([], grid.TYPISTS, "typist") == grid.TYPISTS
    assert grid.select(["canary:parakeet", "canary"], grid.TYPISTS, "typist") == ("parakeet", "canary")
    assert grid.select(["wav2vec2-large"], grid.STOPWATCHES, "stopwatch") == ("wav2vec2-large",)


def test_select_refuses_an_unknown_name_listing_the_known_ones():
    with pytest.raises(SystemExit) as raised:
        grid.select(["whisper-tiny"], grid.TYPISTS, "typist")
    message = str(raised.value)
    assert "whisper-tiny" in message and all(t in message for t in grid.TYPISTS)


def test_name_taggers_are_the_five_config_arms():
    assert list(grid.NAME_TAGGERS) == [config.ARM_BASELINE, config.ARM_DIARIZEN,
                                       config.ARM_DIARIZEN_FREE, config.ARM_SORTFORMER,
                                       config.ARM_SORTFORMER_STREAMING]


# ---- the plan ----

def _full_plan(grid_id="t", rejoin=False):
    return grid.plan(grid.TYPISTS, grid.STOPWATCHES, tuple(grid.NAME_TAGGERS), grid_id, rejoin=rejoin)


def test_plan_has_four_transcribes_eight_aligns_five_diarizes_one_join():
    roles = [job.role for job in _full_plan()]
    assert [roles.count(r) for r in ("transcribe", "align", "diarize", "join")] == [4, 8, 5, 1]


def test_every_align_waits_on_its_own_typist_and_dies_with_it():
    for job in _full_plan():
        if job.role == "align":
            assert job.after_ok == [f"transcribe:{job.args[0]}"]
            assert job.kill_on_invalid_dep and not job.after_any


def test_no_diarize_job_waits_on_anything():
    for job in _full_plan():
        if job.role == "diarize":
            assert not job.after_ok and not job.after_any and not job.kill_on_invalid_dep


def test_the_join_waits_on_exactly_every_align_and_diarize():
    jobs = _full_plan()
    join = [job for job in jobs if job.role == "join"][0]
    expected = {job.key for job in jobs if job.role in ("align", "diarize")}
    assert set(join.after_any) == expected and len(join.after_any) == 13
    assert not join.after_ok and not join.kill_on_invalid_dep


def test_dependencies_precede_their_dependants():
    seen = set()
    for job in _full_plan():
        assert set(job.after_ok + job.after_any) <= seen
        seen.add(job.key)


def test_the_rejoin_plan_is_the_join_alone():
    jobs = _full_plan(rejoin=True)
    assert len(jobs) == 1 and jobs[0].role == "join"
    assert not jobs[0].after_ok and not jobs[0].after_any


def test_logs_are_unique_and_under_the_run_log_dir():
    jobs = _full_plan("t")
    paths = [job.out for job in jobs] + [job.err for job in jobs]
    assert len(set(paths)) == len(paths)
    assert all(Path(p).parent == grid.log_dir("t") for p in paths)


def test_every_referenced_sbatch_exists():
    for job in _full_plan():
        assert (ROOT / job.sbatch).is_file(), job.sbatch


def test_diarize_recipes_run_the_arm_their_name_says():
    text = {n: (ROOT / "slurm_jobs" / f"{stem}.sbatch").read_text() for n, stem in grid.NAME_TAGGERS.items()}
    assert "--num-speakers 0" in text[config.ARM_DIARIZEN_FREE]
    assert "--mode offline" in text[config.ARM_SORTFORMER]
    assert "--mode streaming" in text[config.ARM_SORTFORMER_STREAMING]


# ---- envs ----

def _activates(text):
    match = re.search(r"^activate_env\s+(\S+)", text, re.M)
    return match.group(1) if match else None


def test_each_typist_runs_in_its_registry_env():
    text = (ROOT / "slurm_jobs" / "stage1a_transcribe.sbatch").read_text()
    arms = {}
    for patterns, env in re.findall(r"^\s*([a-z0-9|-]+)\)\s*ENV_NAME=(\w+)", text, re.M):
        for name in patterns.split("|"):
            arms[name] = env
    for name, entry in typists.TYPISTS.items():
        assert arms.get(name) == entry["env"], name
    assert _activates(text) == '"${ENV_NAME}"'


def test_alignment_always_runs_in_asr_env():
    assert _activates((ROOT / "slurm_jobs" / "stage1a_align.sbatch").read_text()) == "asr_env"


# ---- the driver: dry run ----

def _forbid(*args, **kwargs):
    raise AssertionError("a dry run must call nothing")


def test_dry_run_prints_eighteen_sbatch_lines_and_calls_nothing(monkeypatch, capsys):
    monkeypatch.setattr(subprocess, "run", _forbid)
    assert grid_submit.main(["--dry-run", "--grid-id", "t"]) == 0
    out = capsys.readouterr().out.splitlines()
    commands = [shlex.split(line) for line in out if line.startswith("sbatch ")]
    assert len(commands) == 18

    placeholders = {job.key: "{%s}" % job.key for job in _full_plan("t")}
    expected = [grid.sbatch_argv(job, placeholders) for job in _full_plan("t")]
    assert commands == expected
    assert sum(1 for c in commands if "--kill-on-invalid-dep=yes" in c) == 8
    assert "RELAY: grid plan typists 4 stopwatches 2 taggers 5 cells 40" in out


def test_dry_run_without_a_grid_id_or_slurm_job_falls_back_to_a_local_id(monkeypatch, capsys):
    monkeypatch.delenv("SLURM_JOB_ID", raising=False)
    monkeypatch.setattr(subprocess, "run", _forbid)
    assert grid_submit.main(["--dry-run", "--typist", "parakeet"]) == 0
    assert "grid-local-" in capsys.readouterr().out


# ---- the driver: submitting ----

class FakeSlurm:
    """sbatch hands out 101, 102, ...; squeue answers from a script; scancel is recorded."""

    def __init__(self, fail_at=None, squeue=None):
        self.next_id = 101
        self.fail_at = fail_at
        self.squeue = list(squeue or [])
        self.sbatch_calls, self.envs, self.cancelled = [], [], []

    def __call__(self, argv, **kwargs):
        if argv[0] == "sbatch":
            self.sbatch_calls.append(argv)
            self.envs.append(kwargs.get("env"))
            if self.fail_at is not None and len(self.sbatch_calls) == self.fail_at:
                return types.SimpleNamespace(returncode=1, stdout="", stderr="sbatch: error")
            job_id = self.next_id
            self.next_id += 1
            return types.SimpleNamespace(returncode=0, stdout=f"{job_id}\n", stderr="")
        if argv[0] == "scancel":
            self.cancelled.extend(argv[1:])
            return types.SimpleNamespace(returncode=0, stdout="", stderr="")
        if argv[0] == "squeue":
            if "-n" in argv:          # the concurrency guard
                return types.SimpleNamespace(returncode=0, stdout="999\n", stderr="")
            return self.squeue.pop(0)
        raise AssertionError(argv)


@pytest.fixture
def driver_env(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "WORKSPACE_ROOT", tmp_path)
    monkeypatch.setenv("SLURM_JOB_ID", "999")
    monkeypatch.setenv("SLURM_CPUS_PER_TASK", "1")
    monkeypatch.setenv("RELAY_STAGE", "x")
    monkeypatch.setenv("GRID_DRY_RUN", "0")
    return tmp_path


def test_submit_wires_real_ids_and_a_clean_child_environment(driver_env, capsys):
    slurm = FakeSlurm()
    assert grid_submit.main(["--grid-id", "t", "--no-preflight"], run=slurm) == 0
    assert len(slurm.sbatch_calls) == 18

    ids = {job.key: str(101 + i) for i, job in enumerate(_full_plan("t"))}
    for job, argv in zip(_full_plan("t"), slurm.sbatch_calls):
        assert argv == grid.sbatch_argv(job, ids)
    align = slurm.sbatch_calls[4]
    assert "--dependency=afterok:101" in align

    for env in slurm.envs:
        assert not any(k.startswith(("SLURM_", "RELAY_", "GRID_")) for k in env)
        assert env["PSYCH_ASR_GRID"] == "t"

    rows = (driver_env / grid.log_dir("t") / "jobs.tsv").read_text().splitlines()
    assert len(rows) == 1 + 18
    assert "RELAY: grid submitted jobs 18" in capsys.readouterr().out


def test_a_failed_sbatch_cancels_what_was_submitted(driver_env, capsys):
    slurm = FakeSlurm(fail_at=5)
    assert grid_submit.main(["--grid-id", "t", "--no-preflight"], run=slurm) == 2
    assert slurm.cancelled == ["101", "102", "103", "104"]
    assert "RELAY: grid submit failed at align" in capsys.readouterr().out


def test_a_real_run_needs_a_slurm_job_id(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(config, "WORKSPACE_ROOT", tmp_path)
    monkeypatch.delenv("SLURM_JOB_ID", raising=False)
    slurm = FakeSlurm()
    assert grid_submit.main(["--no-preflight"], run=slurm) == 2
    assert not slurm.sbatch_calls
    assert "RELAY: grid refused: no Slurm job id" in capsys.readouterr().out


def test_another_live_driver_refuses(driver_env, capsys):
    class Busy(FakeSlurm):
        def __call__(self, argv, **kwargs):
            if argv[0] == "squeue" and "-n" in argv:
                return types.SimpleNamespace(returncode=0, stdout="999\n555\n", stderr="")
            return super().__call__(argv, **kwargs)

    slurm = Busy()
    assert grid_submit.main(["--grid-id", "t", "--no-preflight"], run=slurm) == 2
    assert not slurm.sbatch_calls
    assert "RELAY: grid refused: another grid driver is running" in capsys.readouterr().out


# ---- the driver: waiting ----

def _queue(stdout="", returncode=0, stderr=""):
    return types.SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


def _manifest(joined=40, missing=0, failed=0, stem_in_error=False):
    records = []
    all_cells = grid.cells(grid.TYPISTS, grid.STOPWATCHES, tuple(grid.NAME_TAGGERS))
    statuses = [grid.JOINED] * joined + [grid.MISSING] * missing + [grid.FAILED] * failed
    for cell, status in zip(all_cells, statuses):
        record = {"cell": cell.name, "status": status}
        if status == grid.FAILED:
            record["error"] = "RuntimeError"
        records.append(record)
    inputs = {"asr": {t: grid.PRESENT for t in grid.TYPISTS},
              "aligned": {f"{t}+{s}": grid.PRESENT for t in grid.TYPISTS for s in grid.STOPWATCHES},
              "rttm": {n: grid.PRESENT for n in grid.NAME_TAGGERS}}
    if missing:
        inputs["rttm"][config.ARM_SORTFORMER] = grid.MISSING
        inputs["aligned"]["canary+wav2vec2-large"] = grid.EMPTY
    axes = {"typists": grid.TYPISTS, "stopwatches": grid.STOPWATCHES,
            "taggers": tuple(grid.NAME_TAGGERS)}
    return grid.build_manifest("t", axes, inputs, records)


def test_wait_ends_when_the_ids_are_gone_and_reports_the_manifest(driver_env, capsys):
    import json
    log = driver_env / grid.log_dir("t")
    log.mkdir(parents=True)
    (log / "manifest.json").write_text(json.dumps(_manifest(joined=38, missing=2)))
    os.utime(log / "manifest.json", (1, 1))

    def touch_manifest(_seconds):
        os.utime(log / "manifest.json", None)

    slurm = FakeSlurm(squeue=[_queue("101\n102\n"), _queue("118\n"),
                              _queue(returncode=1, stderr="slurm_load_jobs error: Invalid job id specified")])
    assert grid_submit.main(["--grid-id", "t", "--no-preflight", "--wait"],
                            run=slurm, sleep=touch_manifest) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[-1] == "RELAY: grid cells 40 joined 38 missing 2 failed 0"


def test_ten_squeue_failures_in_a_row_lose_the_queue(driver_env, capsys):
    slurm = FakeSlurm(squeue=[_queue(returncode=1, stderr="timeout")] * 10)
    assert grid_submit.main(["--grid-id", "t", "--no-preflight", "--wait"],
                            run=slurm, sleep=lambda s: None) == 2
    assert "RELAY: grid lost the queue" in capsys.readouterr().out


def test_no_manifest_after_the_wait_fails(driver_env, capsys):
    slurm = FakeSlurm(squeue=[_queue("")])
    assert grid_submit.main(["--grid-id", "t", "--no-preflight", "--wait"],
                            run=slurm, sleep=lambda s: None) == 1
    assert "RELAY: grid join wrote no manifest" in capsys.readouterr().out


# ---- RELAY: lines and the exit code ----

def test_exit_code_fails_on_a_failed_cell_or_nothing_joined_only():
    assert grid.exit_code(_manifest(joined=38, missing=2)) == 0
    assert grid.exit_code(_manifest(joined=39, failed=1)) == 1
    assert grid.exit_code(_manifest(joined=0, missing=40)) == 1


@pytest.mark.parametrize("manifest", [
    _manifest(), _manifest(joined=38, missing=2), _manifest(joined=0, failed=40),
    _manifest(joined=0, missing=40),
])
def test_relay_lines_are_short_pathless_and_end_with_the_totals(manifest):
    lines = grid.relay_summary(manifest)
    assert 3 <= len(lines) <= 35
    for line in lines:
        assert line.startswith("RELAY: grid ") and len(line) <= 190
        assert "/" not in line and "." not in line and STEM not in line
    assert lines[-3].startswith("RELAY: grid plan typists 4 stopwatches 2 taggers 5 cells 40")
    assert lines[-2].startswith("RELAY: grid inputs asr ")
    assert lines[-1].startswith("RELAY: grid cells 40 joined ")


def test_relay_lines_name_what_did_not_land():
    lines = grid.relay_summary(_manifest(joined=38, missing=2))
    assert "RELAY: grid rttm sortformer missing" in lines
    assert "RELAY: grid aligned canary+wav2vec2-large empty" in lines
    assert "RELAY: grid inputs asr 4 of 4 aligned 7 of 8 rttm 4 of 5" in lines


def test_relay_lines_name_a_failed_cell_by_exception_type():
    lines = grid.relay_summary(_manifest(joined=39, failed=1))
    assert any(re.fullmatch(r"RELAY: grid cell \S+ failed RuntimeError", line) for line in lines)


# ---- config ----

def _stage1_dir(extra_env):
    env = {k: v for k, v in os.environ.items() if k != "PSYCH_ASR_STAGE1_DIR"}
    env.update(extra_env)
    code = "from psych_asr import config; print(config.STAGE1_DIR); print(config.DATA_ROOT)"
    out = subprocess.run([sys.executable, "-c", code], cwd=str(ROOT), env=env,
                         stdout=subprocess.PIPE, universal_newlines=True, check=True).stdout
    return out.splitlines()


def test_stage1_dir_follows_the_job_environment():
    stage1, _ = _stage1_dir({"PSYCH_ASR_STAGE1_DIR": "/nowhere/stage1/grid-t"})
    assert stage1 == "/nowhere/stage1/grid-t"
    stage1, data_root = _stage1_dir({})
    assert stage1 == str(Path(data_root) / "stage1")
