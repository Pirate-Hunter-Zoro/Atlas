"""Phrases synthesised once, into the speech cache, by content.

    ~/.cache/tutor-board/speech/<sha>.m4a      (paths.SPEECH)

A card's `say` fence and a card read aloud are both a phrase: a language, the
words, an optional pinyin and voice. `sha` names it, so the same phrase in two
sessions is made once and served from one URL, `/speech/<sha>.m4a`. A phrase
nobody could synthesise leaves `<sha>.err` saying why, which is tried again
after `RETRY_SECONDS`, since a voice may be downloaded or a key added since.
Outside the tree, so audio can never be committed.
"""

import hashlib
import json
import os
import re
import tempfile
import time

from tutorboard import paths

SHA_RE = re.compile(r"\A[0-9a-f]{32}\Z")
RETRY_SECONDS = 3600


def cache():
    return paths.SPEECH


def sha(lang, text, pinyin=None, voice=None):
    """The phrase's name in the cache."""
    key = json.dumps([lang or "", text or "", pinyin or "", voice or ""],
                     ensure_ascii=False)
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]


def path(name):
    """The m4a of a phrase, or None for a name that is not a sha."""
    if not SHA_RE.match(str(name or "")):
        return None
    return os.path.join(cache(), name + ".m4a")


def status(name, where=None):
    """`ready`, `error` (recently failed) or `pending`."""
    where = where or cache()
    if os.path.isfile(os.path.join(where, name + ".m4a")):
        return "ready"
    try:
        if time.time() - os.path.getmtime(os.path.join(where, name + ".err")) \
                < RETRY_SECONDS:
            return "error"
    except OSError:
        pass
    return "pending"


def job(lang, text, pinyin=None, voice=None, live=None):
    """`(name, src)`: the compiler's job for one phrase (`server/tikz.py`)."""
    return sha(lang, text, pinyin, voice), json.dumps(
        {"lang": lang, "text": text, "pinyin": pinyin, "voice": voice,
         "live": live}, ensure_ascii=False)


def _fail(where, name, why):
    fd, tmp = tempfile.mkstemp(dir=where, prefix=".err-")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(str(why))
    os.replace(tmp, os.path.join(where, name + ".err"))


def make(where, name, src):
    """Synthesise one queued phrase into `<where>/<name>.m4a`, or write
    `<name>.err` saying why not. Never raises for a refusal."""
    from tutorboard.agents import speech
    os.makedirs(where, exist_ok=True)
    try:
        said = json.loads(src)
    except ValueError as exc:
        _fail(where, name, "not a phrase: %s" % exc)
        return
    try:
        speech.run("tts", said.get("lang"), {
            "text": said.get("text") or "", "pinyin": said.get("pinyin"),
            "voice": said.get("voice"),
            "dest": os.path.join(where, name + ".m4a")}, live=said.get("live"))
    except speech.Refused as exc:
        _fail(where, name, str(exc))
        return
    try:
        os.remove(os.path.join(where, name + ".err"))
    except OSError:
        pass


def ensure(lang, text, pinyin=None, voice=None, live=None):
    """The phrase's `(sha, m4a path)`, synthesised now if it is not cached.
    Raises `agents.speech.Refused` when nobody could."""
    from tutorboard.agents import speech
    name, src = job(lang, text, pinyin, voice, live)
    target = os.path.join(cache(), name + ".m4a")
    if os.path.isfile(target):
        return name, target
    make(cache(), name, src)
    if os.path.isfile(target):
        return name, target
    try:
        with open(os.path.join(cache(), name + ".err"), "r", encoding="utf-8") as fh:
            why = fh.read().strip()
    except OSError:
        why = "the phrase was not made"
    raise speech.Refused(why)
