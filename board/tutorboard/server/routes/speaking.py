"""Speech: a take heard.

    POST /speech/say         session   one take, multipart: the `audio` file and
                                       the fields `answers`, `ref`, `lang` and
                                       `pinyin`. Saved under the session's
                                       speech/, converted, transcribed, judged
                                       when there is a `ref`; one turn record
                                       and one waking `[speech]` line naming
                                       the `.heard.json`, never the audio
    GET  /speech/last.json   session   the newest heard record, or null

The classes are `handler.UNPREFIXED`'s.
"""

import json
import os
import re
import time

from . import NOT_MINE
from .. import multipart
from ..registry import is_sessionless
from ...agents import speech
from ...course import config
from ...lesson import turns
from ...runner import service as runner
from ...speech import audio, hear

# A 30 s take is well under a megabyte; a 48 kHz stereo WAV of it is ~11 MB.
MAX_TAKE = 32 * 1024 * 1024



def subject_speech(repo):
    """The subject's `speech` block (`config.read_config`), or {}."""
    return config.read_config(repo.root).get("speech") or {}


def get(h, repo, path):
    if path == "/speech/last.json" and repo is not None and not is_sessionless(repo):
        return h.send_json({"ok": True, "heard": hear.newest(repo.live)})
    return NOT_MINE


def post(h, repo, path):
    if path == "/speech/say":
        return say(h, repo)
    return NOT_MINE


def _refuse(h, status, error):
    # The body may be unread: this connection carries nothing more.
    h.close_connection = True
    return h.send_json({"ok": False, "error": error}, status=status)


def say(h, repo):
    """`POST /speech/say`: one take, heard and handed to the tutor as words."""
    if is_sessionless(repo):
        return _refuse(h, 400, "a take is a session's: /s/<id>/speech/say")
    m = re.search(r"boundary=([^;]+)", h.headers.get("Content-Type", ""))
    if not m:
        return _refuse(h, 400, "no boundary")
    try:
        length = int(h.headers.get("Content-Length") or "")
    except ValueError:
        return _refuse(h, 411, "a take says its length")
    if length > MAX_TAKE:
        return _refuse(h, 413, "a take is at most %d MB" % (MAX_TAKE >> 20))
    boundary = m.group(1).strip().strip('"').encode("utf-8")
    folder = os.path.join(repo.live, "speech")
    os.makedirs(folder, exist_ok=True)
    tid = turns.next_turn_id(repo)
    rev = turns.turn_revision(repo, tid)
    base = "%s-r%d" % (tid, rev)
    fields, types = {}, []

    def name_for(index, filename):
        ext = hear.ext_for(filename, types[index] if index < len(types) else "")
        return os.path.join(folder, base + ("" if index == 0 else "-%d" % index)
                            + ext)
    try:
        got = multipart.save_parts(h.rfile, length, boundary, folder, name_for,
                                   fields=fields, types=types)
    except multipart.Broken as exc:
        h.note("speech take refused: %s" % exc)
        return _refuse(h, 400, "the take did not arrive whole: %s" % exc)
    except OSError as exc:
        return _refuse(h, 500, "the take could not be written: %s" % exc)
    if not got or not got[0][2]:
        return h.send_json({"ok": False, "error": "no audio in the take"}, status=400)
    for _f, extra, _s in got[1:]:
        try:
            os.remove(extra)
        except OSError:
            pass
    recording = got[0][1]
    mine = subject_speech(repo)
    lang = speech.clean_lang(fields.get("lang")) or speech.clean_lang(mine.get("lang"))
    if not lang:
        return h.send_json({"ok": False, "error": "say which language: `lang`, "
                            "or `speech.lang` in the subject's tutorboard.json"},
                           status=400)
    ref = (fields.get("ref") or "").strip()[:500] or None
    pinyin = (fields.get("pinyin") or "").strip()[:500] or None
    answers = (fields.get("answers") or "").strip() or turns.newest_question(repo)
    voice = mine.get("voice") if speech.clean_lang(mine.get("lang")) == lang else None
    try:
        rec = hear.take(repo.live, recording, lang, ref=ref, pinyin=pinyin,
                        voice=voice, answers=answers)
    except (speech.Refused, audio.Unconvertible) as exc:
        h.note("speech take %s not heard: %s" % (base, exc))
        return h.send_json({"ok": False, "error": "not heard: %s" % exc,
                            "audio": os.path.basename(recording)}, status=502)
    got = rec.get("assess") or {}
    record = {
        "id": tid, "rev": rev, "kind": "speech",
        "answers": answers,
        "t": time.time(), "iso": time.strftime("%Y-%m-%d %H:%M:%S"),
        "from": "student",
        "text": rec["heard"], "target": rec["target"], "pinyin": rec["pinyin"],
        "lang": lang, "verdict": rec["verdict"],
        "tones": [{k: s.get(k) for k in ("syllable", "pinyin", "expect", "heard",
                                         "confidence")}
                  for s in got.get("syllables") or []],
        "prototype": bool(got.get("prototype")),
        "heard": "/speech/%s.heard.json" % base,
        "read": False,
    }
    turns.write_turn(repo, record)
    msg = dict(record, text=hear.line(rec), heard=rec["file"])
    msg.pop("tones", None)
    with open(repo.messages_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(msg, ensure_ascii=False) + "\n")
    runner.wake(repo)
    h.hub.worker.dirty.set()
    h.note("speech take %s: heard %r by %s in %.1f s" % (
        base, rec["heard"][:60], rec.get("stt_by"), rec.get("took") or 0))
    return h.send_json({"ok": True, "turn": tid, "rev": rev, "heard": rec})
