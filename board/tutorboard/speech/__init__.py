"""Speech: audio in and out of a session, and the local pronunciation check.

    audio.py   reading, writing and converting WAV and m4a (afconvert, ffmpeg)
    tones.py   the local Mandarin tone check, stdlib only (a prototype)
    synth.py   phrases synthesised once into the speech cache, `<sha>.m4a`
    hear.py    one take: converted, transcribed, judged, written beside it

Which provider does each job is `agents/speech.py`'s table.
"""
