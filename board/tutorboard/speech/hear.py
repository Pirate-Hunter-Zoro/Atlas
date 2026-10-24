"""One take: converted, transcribed, judged, and written beside the audio.

    sessions/<id>/speech/<base>.<ext>          the recording as it arrived
                                               (`<base>.orig.wav` for a WAV)
    sessions/<id>/speech/<base>.wav            16 kHz mono, what every listener reads
    sessions/<id>/speech/<base>.heard.json     what was heard and the verdict

The tutor is handed the `.heard.json`, never the audio: `line` is the waking
inbox line and `summary` what `board hear` prints. Sessions are ignored by
git and the audit refuses audio, so a recording never leaves this disk.
"""

import json
import os
import shutil
import tempfile
import time

from tutorboard.agents import speech
from tutorboard.speech import audio, synth

AUDIO_EXTS = (".m4a", ".mp4", ".webm", ".ogg", ".oga", ".opus", ".wav", ".caf",
              ".aac", ".mp3")


def ext_for(filename, ctype=""):
    """The extension a take is saved under: its own when it is audio."""
    ext = os.path.splitext(str(filename or "").lower())[1]
    if ext in AUDIO_EXTS:
        return ext
    ctype = str(ctype or "").lower()
    for word, ext in (("webm", ".webm"), ("ogg", ".ogg"), ("mp4", ".m4a"),
                      ("wav", ".wav"), ("aac", ".m4a")):
        if word in ctype:
            return ext
    return ".m4a"


def reference_wav(lang, ref, pinyin, voice, live, box):
    """The phrase as TTS says it, as a 16 kHz WAV in `box`, or None."""
    try:
        _name, m4a = synth.ensure(lang, ref, pinyin, voice, live)
        return audio.to_wav16k(m4a, os.path.join(box, "reference.wav"))
    except (speech.Refused, audio.Unconvertible, OSError):
        return None


def take(live, recording, lang, ref=None, pinyin=None, voice=None, cfg=None,
         answers=None):
    """Hear the recording at `recording` (inside `live/speech/`): write
    `<base>.wav` and `<base>.heard.json` beside it and return the record.
    Raises `speech.Refused` when nobody could transcribe it, and
    `audio.Unconvertible` when it could not be read; either way no `.wav`
    is left beside the recording."""
    lang = speech.clean_lang(lang)
    if not lang:
        raise speech.Refused("a language tag such as zh-CN is needed")
    folder = os.path.dirname(os.path.abspath(recording))
    base = os.path.splitext(os.path.basename(recording))[0]
    wav = os.path.join(folder, base + ".wav")
    if os.path.abspath(recording) == wav:
        # A WAV take keeps its own bytes beside the 16 kHz one.
        kept = os.path.join(folder, base + ".orig.wav")
        os.replace(recording, kept)
        recording = kept
    # Written whole or not at all; and a take nobody could hear leaves only
    # the recording, never a 16 kHz copy that no record names.
    wav = audio.to_wav16k(recording, wav)
    began = time.time()
    try:
        heard, stt_by = speech.run("stt", lang, {"wav": wav}, live=live, cfg=cfg)
    except BaseException:
        if os.path.exists(wav):
            os.remove(wav)
        raise
    rec = {"base": base, "lang": lang, "target": ref or "", "pinyin": pinyin or "",
           "answers": answers, "heard": heard.get("text") or "",
           "words": heard.get("words") or [], "stt_by": stt_by,
           "seconds": round(audio.seconds(wav), 2),
           "audio": os.path.basename(recording), "t": time.time(),
           "iso": time.strftime("%Y-%m-%d %H:%M:%S")}
    rec["assess"] = None
    if ref:
        box = tempfile.mkdtemp(prefix="speech-ref-")
        try:
            reference = (reference_wav(lang, ref, pinyin, voice, live, box)
                         if speech.primary(lang) == "zh" else None)
            try:
                rec["assess"], rec["assess_by"] = speech.run("assess", lang, {
                    "wav": wav, "ref": ref, "pinyin": pinyin,
                    "words": rec["words"], "heard": rec["heard"],
                    "reference": reference}, live=live, cfg=cfg)
            except speech.Refused as exc:
                rec["assess_error"] = str(exc)
        finally:
            shutil.rmtree(box, ignore_errors=True)
    rec["verdict"] = verdict(rec)
    rec["took"] = round(time.time() - began, 2)
    rec["file"] = os.path.join(folder, base + ".heard.json")
    with open(rec["file"] + ".tmp", "w", encoding="utf-8") as fh:
        json.dump(rec, fh, ensure_ascii=False, indent=1)
    os.replace(rec["file"] + ".tmp", rec["file"])
    return rec


def verdict(rec):
    if not rec.get("heard"):
        return "Nothing was heard."
    if rec.get("assess"):
        return rec["assess"].get("verdict") or ""
    if rec.get("assess_error"):
        return "Not judged: %s" % rec["assess_error"]
    return "No target was set, so nothing was judged."


def line(rec):
    """The waking inbox line: what was heard, what was meant, the verdict."""
    return "[speech] heard: '%s'. Target: '%s'. %s" % (
        rec.get("heard") or "", rec.get("target") or "", rec.get("verdict") or "")


def summary(rec):
    """What `board hear` prints of a heard record."""
    out = ["heard:   %s  (%s, %s)" % (rec.get("heard") or "(nothing)",
                                      rec.get("lang"), rec.get("stt_by")),
           "target:  %s%s" % (rec.get("target") or "(none)",
                              "  [%s]" % rec["pinyin"] if rec.get("pinyin") else ""),
           "verdict: %s" % (rec.get("verdict") or "")]
    got = rec.get("assess") or {}
    if got.get("syllables"):
        out.append("tones:   " + "  ".join(
            "%s %s->%s (%.2f)" % (s.get("syllable") or s.get("pinyin") or "?",
                                  s.get("expect") or "?", _heard_as(s),
                                  s.get("confidence") or 0)
            for s in got["syllables"]))
        if any(_heard_as(s).endswith("?") for s in got["syllables"]):
            out.append("         (a tone with ? is an unconfirmed hint, never a "
                       "wrong tone)")
    off = [w for w in got.get("words") or [] if w.get("op") != "equal"]
    if off:
        out.append("words:   " + ", ".join(
            "%s '%s'%s" % (w["op"], w.get("target") or w.get("heard"),
                           " as '%s'" % w["heard"] if w["op"] == "wrong" else "")
            for w in off))
    if got.get("prototype"):
        out.append("(%s)" % (got.get("label") or "a prototype"))
    return "\n".join(out)


def _heard_as(s):
    """A syllable's tone as `board hear` prints it: the tone confirmed,
    `wrong` only where the recipe failed it, a hint with a question mark; a
    record from before `call` never has a mismatch read as wrong."""
    heard = s.get("heard") or "unknown"
    if s.get("call") == "wrong":
        return "wrong"
    if s.get("hint"):
        return "%s?" % s["hint"]
    if not s.get("call") and heard not in ("unknown", s.get("expect")):
        return "%s?" % heard
    return heard


def newest(live):
    """The newest heard record in a session, or None."""
    folder = os.path.join(live, "speech")
    try:
        names = [n for n in os.listdir(folder) if n.endswith(".heard.json")]
    except OSError:
        return None
    best = None
    for n in names:
        p = os.path.join(folder, n)
        try:
            m = os.path.getmtime(p)
        except OSError:
            continue
        if best is None or m > best[0]:
            best = (m, p)
    if not best:
        return None
    try:
        with open(best[1], "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def has_heard(live):
    """Does this session hold a heard file?"""
    try:
        return any(n.endswith(".heard.json")
                   for n in os.listdir(os.path.join(live, "speech")))
    except OSError:
        return False
