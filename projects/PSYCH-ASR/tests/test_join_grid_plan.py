"""The grid's join, driven with an injected join: input states, cell statuses, the manifest.

Every file here is a synthetic placeholder in tmp_path, named through the naming helpers.
"""

from psych_asr import config  # noqa: I001  -- first, as conftest explains

import json

import pytest

from psych_asr import grid
from psych_asr.artifacts import naming
from psych_asr.cli import join_grid

STEM = "SESSIONX"
COUNTS = {"segments": 3, "words": 12, "turns": 4, "labels": 2,
          "unlabeled_segments": 0, "unlabeled_words": 1}


def _put(path, text="x"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_input_state_tells_missing_from_empty_from_present(tmp_path):
    path = tmp_path / "a"
    assert grid.input_state(path) == grid.MISSING
    _put(path, "")
    assert grid.input_state(path) == grid.EMPTY
    _put(path, "x")
    assert grid.input_state(path) == grid.PRESENT


@pytest.fixture
def stage1(tmp_path):
    """One typist, one stopwatch, three taggers: present, empty, missing."""
    d = tmp_path / "stage1" / "grid-t"
    _put(naming.asr_path(d, STEM, "large-v3"))
    _put(naming.aligned_path(d, STEM, "large-v3+wav2vec2-base"))
    _put(naming.rttm_path(d, STEM, config.ARM_BASELINE))
    _put(naming.rttm_path(d, STEM, config.ARM_DIARIZEN), "")
    return d


def _cells():
    return grid.cells(("large-v3",), ("wav2vec2-base",),
                      (config.ARM_BASELINE, config.ARM_DIARIZEN, config.ARM_SORTFORMER))


def test_cells_join_only_when_both_inputs_landed(stage1):
    calls = []

    def join(aligned, rttm, stem, arm, output_dir):
        calls.append((aligned, rttm, stem, arm, output_dir))
        return COUNTS

    records = join_grid.run_cells(_cells(), stage1, STEM, join)
    assert [r["status"] for r in records] == [grid.JOINED, grid.MISSING, grid.MISSING]
    assert records[0]["counts"] == COUNTS
    assert records[1]["inputs"] == {"aligned": grid.PRESENT, "rttm": grid.EMPTY}
    assert records[2]["inputs"] == {"aligned": grid.PRESENT, "rttm": grid.MISSING}
    assert calls == [(naming.aligned_path(stage1, STEM, "large-v3+wav2vec2-base"),
                      naming.rttm_path(stage1, STEM, config.ARM_BASELINE),
                      STEM, "large-v3+wav2vec2-base+community-1", stage1)]


@pytest.mark.parametrize("error", [SystemExit(f"{STEM} holds no turns"), RuntimeError(f"/x/{STEM}.rttm")])
def test_a_raising_join_is_failed_by_type_alone(stage1, error, capsys):
    def join(*args):
        raise error

    records = join_grid.run_cells(_cells(), stage1, STEM, join)
    assert records[0]["status"] == grid.FAILED
    assert records[0]["error"] == type(error).__name__
    assert STEM not in capsys.readouterr().out


def test_the_manifest_carries_no_stem_and_no_path(stage1, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(config, "WORKSPACE_ROOT", tmp_path / "ws")

    def join(*args):
        return COUNTS

    code = join_grid.main(["--stem", STEM, "--stage1-dir", str(stage1), "--grid-id", "t",
                           "--typist", "large-v3", "--stopwatch", "wav2vec2-base"], join=join)
    manifest_path = tmp_path / "ws" / grid.log_dir("t") / "manifest.json"
    text = manifest_path.read_text()
    assert STEM not in text and str(tmp_path) not in text
    manifest = json.loads(text)
    assert manifest["totals"] == {"cells": 5, "joined": 1, "missing": 4, "failed": 0}
    assert manifest["inputs"]["asr"] == {"large-v3": grid.PRESENT}
    assert manifest["inputs"]["rttm"][config.ARM_DIARIZEN] == grid.EMPTY
    assert code == 0

    out = capsys.readouterr().out
    assert STEM not in out and str(tmp_path) not in out
    assert out.splitlines()[-1] == "RELAY: grid cells 5 joined 1 missing 4 failed 0"


def test_nothing_joined_exits_nonzero(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "WORKSPACE_ROOT", tmp_path / "ws")
    code = join_grid.main(["--stem", STEM, "--stage1-dir", str(tmp_path / "empty"),
                           "--grid-id", "t"], join=lambda *a: COUNTS)
    assert code == 1
