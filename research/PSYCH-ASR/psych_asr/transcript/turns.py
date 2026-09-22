"""Collapsing segments into conversational turns.

STDLIB ONLY, and it is the piece two other modules need: the renderer groups turns to
read as dialogue and the regression gate counts them. One implementation, so the two
cannot drift apart.
"""

# assign_word_speakers sets "speaker" only where a transcript span overlaps a diarized
# turn, and fill_nearest is off by default -- so the key can simply be absent. Those
# segments get this label rather than being dropped or merged into a neighbour: a cluster
# of them is itself the diagnostic that diarization under-covered the audio.
UNKNOWN_SPEAKER = "UNKNOWN"


def segment_speaker(segment):
    """Tolerant lookup -- never index "speaker" directly (it is not guaranteed)."""
    return segment.get("speaker") or UNKNOWN_SPEAKER


def word_clock(segment_text, words, offset):
    """IN: one segment's text + its aligned words + where that text starts in the turn
    OUT: [(character offset in the turn, clock time)], increasing in both

    The map that makes "the annotator heard it at 12:03" into a character position. Forced
    alignment gives every word a start and an end, so a turn's text and its clock are
    anchored to each other at every word rather than only at the two ends -- which is the
    difference between placing an interjection within a word or two of where it was heard
    and placing it proportionally inside a ninety-second turn.

    A word the aligner could not time, or one whose text is not found where it should be,
    is skipped rather than guessed: the anchors either side of it still bracket it.
    """
    anchors, cursor = [], 0
    for word in words or []:
        spelling = str(word.get("word") or word.get("text") or "").strip()
        start, end = word.get("start"), word.get("end")
        if not spelling or start is None:
            continue
        position = segment_text.find(spelling, cursor)
        if position < 0:
            continue
        cursor = position + len(spelling)
        anchors.append((offset + position, float(start)))
        if end is not None:
            anchors.append((offset + cursor, float(end)))
    return anchors


def group_into_turns(segments, unknown=UNKNOWN_SPEAKER, keep_word_times=False):
    """Collapse consecutive same-speaker segments into conversational turns.

    IN:  list of segment dicts (start, end, text, speaker?), in time order
         keep_word_times -- attach a "clock" list of (character offset, time) anchors
                            built from the segments' aligned word times. Off by default
                            because only the correction pass needs it and every other
                            caller writes these turns straight out to JSON.
         unknown -- the label for a segment with no speaker key. Pass None to keep the
         raw absent-speaker value, which is what the backchannel scan wants: it must not
         merge two genuinely unlabeled stretches into one turn on the strength of a
         placeholder they never carried.
    OUT: list of turn dicts: {"speaker": str|None, "start": float, "end": float, "text": str}

    Alignment re-splits segments at sentence boundaries, so one speaker's uninterrupted
    minute arrives as a dozen segments. Grouping is what makes the file read as a
    conversation (one paragraph per turn) instead of one line per sentence.

    Empty-text segments are skipped entirely, so a silent segment never breaks a turn in
    half.
    """
    turns = []
    for segment in segments:
        speaker = segment.get("speaker") or unknown
        text = segment.get("text", "").strip()
        if not text:
            continue
        if turns and turns[-1]["speaker"] == speaker:
            offset = len(turns[-1]["text"]) + 1
            turns[-1]["text"] += " " + text
            turns[-1]["end"] = segment["end"]
        else:
            offset = 0
            turns.append({
                "speaker": speaker,
                "start": segment["start"],
                "end": segment["end"],
                "text": text,
            })
        if keep_word_times:
            turns[-1].setdefault("clock", []).extend(
                word_clock(text, segment.get("words"), offset))
    return turns
