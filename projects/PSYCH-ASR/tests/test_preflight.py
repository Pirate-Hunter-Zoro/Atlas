"""The preflight's file tier over synthetic model directories, and its summary and exit."""

from psych_asr import config  # noqa: I001  -- first, as conftest explains

import io
import tarfile

import pytest

from psych_asr import preflight
from psych_asr.cli import preflight_models

Asset = preflight.Asset


def _put(path, data=b"x"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _tar(path, members=("model_config.yaml", "model_weights.ckpt")):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(path, "w") as archive:
        for name in members:
            info = tarfile.TarInfo("./" + name)
            info.size = 1
            archive.addfile(info, io.BytesIO(b"x"))


def _whisper(root):
    for name in ("model.bin", "config.json", "tokenizer.json", "vocabulary.json"):
        _put(root / name)


def test_a_missing_directory_is_missing(tmp_path):
    assert preflight.check(Asset("typist", "large-v3", tmp_path / "no", "whisper")).status == preflight.MISSING


def test_a_readme_and_an_empty_folder_is_empty(tmp_path):
    root = tmp_path / "m"
    _put(root / "README.md", b"")
    (root / "weights").mkdir()
    assert preflight.check(Asset("typist", "large-v3", root, "whisper")).status == preflight.EMPTY


def test_a_zero_byte_required_file_is_incomplete(tmp_path):
    root = tmp_path / "m"
    _whisper(root)
    _put(root / "model.bin", b"")
    assert preflight.check(Asset("typist", "large-v3", root, "whisper")).status == preflight.INCOMPLETE


def test_a_partial_download_with_the_weights_absent_is_incomplete(tmp_path):
    root = tmp_path / "m"
    _put(root / ".cache" / "huggingface" / "download" / "x.incomplete")
    assert preflight.check(Asset("typist", "large-v3", root, "whisper")).status == preflight.INCOMPLETE


def test_every_required_file_non_zero_is_ok_and_counted(tmp_path):
    root = tmp_path / "m"
    _whisper(root)
    _put(root / ".cache" / "huggingface" / "x.metadata")
    result = preflight.check(Asset("typist", "large-v3", root, "whisper"))
    assert result == preflight.Result(preflight.OK, 4, 4)


def test_a_nemo_that_is_not_a_tar_is_incomplete(tmp_path):
    root = tmp_path / "parakeet"
    _put(root / "parakeet.nemo", b"not a tar archive")
    assert preflight.check(Asset("typist", "parakeet", root, "nemo-dir")).status == preflight.INCOMPLETE
    _tar(root / "parakeet.nemo")
    assert preflight.check(Asset("typist", "parakeet", root, "nemo-dir")).status == preflight.OK


def test_a_sortformer_file_must_be_a_tar(tmp_path):
    path = tmp_path / "s" / "s.nemo"
    _put(path, b"nope")
    assert preflight.check(Asset("tagger", "sortformer", path, "nemo-file")).status == preflight.INCOMPLETE


def test_diarizen_without_plda_is_incomplete(tmp_path, monkeypatch):
    wespeaker = tmp_path / "wespeaker" / "pytorch_model.bin"
    _put(wespeaker)
    monkeypatch.setattr(config, "WESPEAKER_EMBEDDING_FILE", wespeaker)
    root = tmp_path / "diarizen"
    _put(root / "config.toml")
    _put(root / "pytorch_model.bin")
    asset = Asset("tagger", "diarizen", root, "diarizen")
    assert preflight.check(asset).status == preflight.INCOMPLETE
    _put(root / "plda" / "mu.npy")
    assert preflight.check(asset).status == preflight.OK


def test_pyannote_needs_config_and_a_weight_file(tmp_path):
    root = tmp_path / "community-1"
    _put(root / "config.yaml")
    asset = Asset("tagger", "community-1", root, "pyannote")
    assert preflight.check(asset).status == preflight.INCOMPLETE
    _put(root / "segmentation" / "pytorch_model.bin")
    assert preflight.check(asset).status == preflight.OK


def test_an_absent_stopwatch_checkpoint_is_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("TORCH_HOME", str(tmp_path / "torch_home"))
    found = {a.name: a for a in preflight.assets(stopwatch_names=("wav2vec2-large",),
                                                 typist_names=(), tagger_names=())}
    asset = found["wav2vec2-large"]
    assert asset.path == (tmp_path / "torch_home" / "hub" / "checkpoints"
                          / config.STOPWATCH_CHECKPOINTS["wav2vec2-large"])
    assert preflight.check(asset).status == preflight.MISSING
    _put(asset.path)
    assert preflight.check(asset).status == preflight.OK


def test_assets_cover_every_axis_and_the_shared_envs():
    found = preflight.assets()
    axes = [a.axis for a in found]
    assert axes.count("typist") == 4 and axes.count("stopwatch") == 2 and axes.count("tagger") == 5
    assert {a.name for a in found if a.kind == "env"} == set(preflight.ENVS)
    assert all("/" not in a.name and "." not in a.name for a in found)


def test_stopwatch_checkpoints_cover_every_stopwatch():
    assert set(config.STOPWATCH_CHECKPOINTS) == set(config.STOPWATCHES)


@pytest.mark.parametrize("count", [0, 1, 2])
def test_the_inbox_is_counted_never_named(tmp_path, count):
    for i in range(count):
        _put(tmp_path / "inbox" / f"synthetic{i}.wav")
    _put(tmp_path / "inbox" / "notes.txt")
    assert preflight.check_data(tmp_path) == (True, count)


def test_a_missing_data_root_counts_nothing(tmp_path):
    assert preflight.check_data(tmp_path / "absent") == (False, 0)


def test_summary_line_and_pass_rule():
    statuses = [preflight.OK, preflight.OK, preflight.EMPTY, preflight.MISSING, preflight.INCOMPLETE]
    assert preflight.summary_line(statuses, 1, 0) == (
        "RELAY: preflight assets 5 ok 2 empty 1 missing 1 incomplete 1 load-failed 1 inbox-wav 0")
    assert preflight.summary_line([preflight.OK], 0, None).endswith("inbox-wav skipped")
    assert preflight.passed([preflight.OK] * 3, 0, 1)
    assert not preflight.passed([preflight.OK] * 3, 0, 2)
    assert not preflight.passed([preflight.OK] * 3, 1, 1)
    assert not preflight.passed([preflight.OK, preflight.EMPTY], 0, 1)
    assert preflight.passed([preflight.OK], 0, None)


def _assets_in(tmp_path, ok):
    root = tmp_path / "m"
    if ok:
        _whisper(root)
    return lambda *a, **k: [Asset("typist", "large-v3", root, "whisper")]


def test_the_cli_exits_zero_only_when_all_is_ok_and_one_wav_waits(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(preflight, "assets", _assets_in(tmp_path, ok=True))
    monkeypatch.setattr(config, "DATA_ROOT", tmp_path / "data")
    _put(tmp_path / "data" / "inbox" / "synthetic.wav")
    assert preflight_models.main([]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[-1] == ("RELAY: preflight assets 1 ok 1 empty 0 missing 0 incomplete 0 "
                       "load-failed 0 inbox-wav 1")
    assert not any(line.startswith("RELAY:") and "synthetic" in line for line in out)

    _put(tmp_path / "data" / "inbox" / "synthetic2.wav")
    assert preflight_models.main([]) == 1
    assert preflight_models.main(["--skip-data"]) == 0


def test_the_cli_names_every_asset_that_is_not_ok(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(preflight, "assets", _assets_in(tmp_path, ok=False))
    assert preflight_models.main(["--skip-data"]) == 1
    out = capsys.readouterr().out.splitlines()
    assert "RELAY: preflight missing typist large-v3" in out


def test_the_load_tier_never_fetches_an_unstaged_stopwatch(tmp_path, monkeypatch, capsys):
    pytest.importorskip("torchaudio")
    torch_home = tmp_path / "torch_home"
    monkeypatch.setenv("TORCH_HOME", str(torch_home))
    only_stopwatches = preflight.assets(typist_names=(), tagger_names=())
    only_stopwatches = [a for a in only_stopwatches if a.axis == "stopwatch"]
    monkeypatch.setattr(preflight, "assets", lambda *a, **k: only_stopwatches)
    assert preflight_models.main(["--load", "--skip-data"]) == 1
    assert not torch_home.exists()
    assert "RELAY: preflight missing stopwatch wav2vec2-large" in capsys.readouterr().out
