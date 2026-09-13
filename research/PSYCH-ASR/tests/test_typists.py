"""The Stage 1a seam: the contract every typist must meet, checked without a GPU.

Nothing here loads a model. The point of splitting Stage 1a was that the SHAPE passing
between a typist and a stopwatch is the whole interface, and a shape is testable on a
login node in milliseconds.
"""

import pytest

from psych_asr import config
from psych_asr.asr import typists


def test_the_registry_imports_with_neither_whisperx_nor_nemo_installed():
    """If this module ever grows a top-level heavy import, --typist stops being checkable
    before a GPU is allocated and every typo costs a queue wait."""
    assert set(typists.TYPISTS) == {"large-v3", "large-v3-turbo", "parakeet", "canary"}
    for entry in typists.TYPISTS.values():
        assert entry["backend"] in {"faster-whisper", "nemo"}
        assert entry["env"] in {"asr_env", "nemo_env"}
        assert config.MODELS_ROOT in entry["checkpoint"].parents


def test_no_two_typists_share_a_checkpoint():
    """Two names pointing at one directory would put the same words in the bake-off twice
    and read as agreement between models."""
    staged = [entry["checkpoint"] for entry in typists.TYPISTS.values()]
    assert len(set(staged)) == len(staged)


def test_an_unknown_typist_prints_the_menu_rather_than_raising_keyerror():
    with pytest.raises(SystemExit) as raised:
        typists.describe("large-v4")
    assert "large-v3-turbo" in str(raised.value)


def test_a_nemo_hypothesis_becomes_whisper_shaped_segments():
    """The ONLY difference between a NeMo transcript and a whisper one, downstream: NeMo
    calls the text "segment"."""
    converted = typists.segments_from_nemo([
        {"start": 0.0, "end": 4.0, "segment": "So how was the week."},
        {"start": 4.0, "end": 10.0, "segment": "It was rough."},
    ])
    assert converted == [
        {"text": "So how was the week.", "start": 0.0, "end": 4.0},
        {"text": "It was rough.", "start": 4.0, "end": 10.0},
    ]
    typists.check_segment_contract(converted)


def test_out_of_order_segments_are_refused_at_the_seam():
    """An aligner handed these would re-time the words against the wrong audio, produce a
    transcript that reads perfectly, and say nothing. The grader cannot see it either."""
    with pytest.raises(SystemExit) as raised:
        typists.check_segment_contract([
            {"text": "second", "start": 10.0, "end": 12.0},
            {"text": "first", "start": 0.0, "end": 4.0},
        ])
    assert "time order" in str(raised.value)


def test_a_segment_that_ends_before_it_starts_is_refused():
    with pytest.raises(SystemExit):
        typists.check_segment_contract([{"text": "backwards", "start": 9.0, "end": 4.0}])


def test_a_segment_with_no_times_is_refused():
    with pytest.raises(SystemExit):
        typists.check_segment_contract([{"text": "untimed"}])


def test_an_empty_segment_is_allowed_through():
    """A VAD chunk with nothing in it is a real thing a typist can say. Dropping it here
    would change the segment count the job log reports, which is a number people read."""
    typists.check_segment_contract([{"text": "", "start": 1.0, "end": 1.4}])


def test_touching_segments_are_not_read_as_out_of_order():
    """One segment ending exactly where the next begins is the normal case, and float
    equality is not something to leave to chance."""
    typists.check_segment_contract([
        {"text": "a", "start": 0.0, "end": 4.0},
        {"text": "b", "start": 4.0, "end": 10.0},
    ])


def test_the_summary_reports_covered_seconds_not_only_a_count():
    """A typist that ran, succeeded, and heard a tenth of the session has a plausible
    segment count and an obviously wrong covered duration."""
    lines = typists.format_transcription_summary("large-v3", {
        "segments": [{"text": "a", "start": 0.0, "end": 4.0},
                     {"text": "b", "start": 10.0, "end": 12.0}],
        "language": "en",
    })
    assert any("Covered seconds    : 6.0" in line for line in lines)
    assert any("Segments           : 2" in line for line in lines)
