"""The Stage 1 filename convention. Getting this wrong mislabels which model produced what."""

from psych_asr.artifacts import naming


def test_stem_and_arm_survive_a_hyphenated_arm_name():
    assert naming.stem_from_aligned("d/S1.aligned.json") == "S1"
    assert naming.arm_from("d/S1.sortformer-streaming.rttm", "S1", naming.RTTM_SUFFIX) == "sortformer-streaming"
    assert naming.arm_from("d/S1.community-1.diarized.json", "S1", naming.DIARIZED_SUFFIX) == "community-1"


def test_an_arm_name_containing_a_dot_is_not_truncated():
    """Splitting on "." would return "v2" here. Suffix stripping returns the whole arm."""
    assert naming.arm_from("d/S1.sortformer-v2.1.rttm", "S1", naming.RTTM_SUFFIX) == "sortformer-v2.1"


def test_a_stem_containing_dots_still_resolves():
    """Real stems carry a participant code and a session number. The placeholder here is
    deliberately not code-shaped -- the pre-commit hook refuses a staged BL### and it is
    right to, since a fixture that looks like a real one is how a real one gets committed."""
    assert naming.stem_from_aligned("d/PILOT.session1.aligned.json") == "PILOT.session1"
    assert naming.arm_from("d/PILOT.session1.diarizen.rttm", "PILOT.session1",
                           naming.RTTM_SUFFIX) == "diarizen"


def test_an_unexpected_filename_labels_itself_visibly_rather_than_raising():
    assert naming.arm_from("d/handmade.rttm", "S1", naming.RTTM_SUFFIX) == "handmade"


def test_the_single_job_path_and_the_split_do_not_collide():
    """The gate identifies the fixture by the ABSENCE of an arm, so the two names are not
    interchangeable."""
    assert naming.diarized_path("d", "S1").name == "S1.diarized.json"
    assert naming.diarized_path("d", "S1", "community-1").name == "S1.community-1.diarized.json"
    assert naming.transcript_path("d", "S1").name == "S1.transcript.txt"
    assert naming.transcript_path("d", "S1", "diarizen").name == "S1.diarizen.transcript.txt"


def test_discovery_skips_the_overlap_free_view(tmp_path):
    """.exclusive.rttm is a diagnostic on the baseline arm, not an arm of its own -- joining
    it would produce a fifth transcript that no model actually produced."""
    for name in ["S1.community-1.rttm", "S1.community-1.exclusive.rttm",
                 "S1.diarizen.rttm", "S1.sortformer-streaming.rttm"]:
        (tmp_path / name).write_text("")
    assert [arm for arm, _ in naming.find_arm_rttms(tmp_path, "S1")] == [
        "community-1", "diarizen", "sortformer-streaming"]


def test_a_crashed_arm_is_absent_rather_than_fatal(tmp_path):
    (tmp_path / "S1.community-1.diarized.json").write_text("{}")
    assert [arm for arm, _ in naming.find_arm_transcripts(tmp_path, "S1")] == ["community-1"]


def test_more_than_one_session_in_the_directory_is_refused(tmp_path):
    import pytest
    (tmp_path / "A.aligned.json").write_text("{}")
    (tmp_path / "B.aligned.json").write_text("{}")
    with pytest.raises(SystemExit):
        naming.find_sole_stem(tmp_path)


def test_the_stage_1a_seam_names_the_typist_and_the_stopwatch():
    """A grid cell is a typist, a stopwatch and a name-tagger. Stage 1a names the first two;
    Stage 1b appends the third, so a two-part arm here is half a cell name on purpose."""
    assert naming.asr_path("d", "S1", "parakeet").name == "S1.parakeet.asr.json"
    assert naming.aligned_path("d", "S1").name == "S1.aligned.json"
    assert (naming.aligned_path("d", "S1", "large-v3+wav2vec2-base").name
            == "S1.large-v3+wav2vec2-base.aligned.json")


def test_a_typist_name_containing_a_dot_survives_the_round_trip():
    """"large-v3.1" splits into "large-v3" under any naive parse. Suffix stripping does not."""
    written = naming.asr_path("d", "S1", "large-v3.1")
    assert naming.arm_from(written, "S1", naming.ASR_SUFFIX) == "large-v3.1"


def test_a_typist_whose_job_crashed_is_absent_rather_than_fatal(tmp_path):
    for name in ["S1.large-v3.asr.json", "S1.parakeet.asr.json"]:
        (tmp_path / name).write_text("{}")
    assert [typist for typist, _ in naming.find_asr_transcripts(tmp_path, "S1")] == [
        "large-v3", "parakeet"]


def test_the_asr_seam_is_not_discovered_as_a_diarization_arm(tmp_path):
    """Stage 1a-i's artifact lives beside Stage 1b's. If the arm globs picked it up, the
    typist would enrol itself as a sixth diarizer in the bake-off it is an axis of."""
    (tmp_path / "S1.parakeet.asr.json").write_text("{}")
    (tmp_path / "S1.community-1.rttm").write_text("")
    assert [arm for arm, _ in naming.find_arm_rttms(tmp_path, "S1")] == ["community-1"]
    assert naming.find_arm_transcripts(tmp_path, "S1") == []
