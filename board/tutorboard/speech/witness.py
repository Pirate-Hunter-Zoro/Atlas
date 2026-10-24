"""`board doctor`'s speech lines: what this Mac can speak, hear and judge, and
one word spoken and heard back.

    dry      per kind, the chain `agents/speech.chain` would walk with each
             recipe's reason when it is passed over, then the local recipe's
             state: `say` and its voices, espeak-ng, whisper-cli and its
             model, the tone check
    witness  one word, picked at random, through the TTS chain and back
             through the STT chain; it passes only when the word comes back

Nothing is written outside a scratch directory but the cost lines the state
directory keeps for sessionless speech.
"""

import os
import random
import re
import shutil
import tempfile

from tutorboard import paths
from tutorboard.agents import speech
from tutorboard.speech import audio

WORDS = ("orange", "window", "garden", "seven", "yellow", "river", "music",
         "pencil")
LANG = "en-US"


def _chain_line(kind, lang, cfg):
    said = []
    for name, why in speech.explain(kind, lang, cfg):
        said.append(name if not why else "%s (%s)" % (name, why))
    return "speech %-7s %s: %s" % (kind, lang, ", then ".join(said))


def local_state(cfg=None):
    """`[(ok, line)]`: the local recipe's TTS, STT and assessment, as they
    stand on this machine."""
    cfg = speech.load() if cfg is None else cfg
    spec = (cfg.get("recipes") or {}).get(speech.LOCAL) or {}
    out = []
    say = shutil.which(((spec.get("tts") or {}).get("cmd") or ["say"])[0])
    voices = speech.say_voices(say) if say else []
    langs = sorted(set(v for _n, v in voices if v))
    picks = ", ".join("%s %s" % (lang, speech.say_voice(spec, lang))
                      for lang in ("zh-CN", "ja-JP", "fr-FR", "en-US")
                      if speech.say_voice(spec, lang))
    espeak = shutil.which("espeak-ng")
    out.append((bool(say or espeak), "local tts:    %s; %s" % (
        "say, %d voices in %d languages (%s)" % (len(voices), len(langs), picks)
        if say else "no `say`",
        "espeak-ng %s (Irish and any language macOS lacks)" % espeak if espeak
        else "espeak-ng MISSING, so Irish (ga) has no local voice "
             "(brew install espeak-ng)")))
    whisper = shutil.which(((spec.get("stt") or {}).get("cmd") or ["whisper-cli"])[0])
    model = speech.model_path(spec)
    out.append((bool(whisper and model), "local stt:    %s" % (
        "whisper-cli %s with %s" % (whisper, model) if whisper and model
        else "whisper-cli MISSING (brew install whisper-cpp)" if not whisper
        else "whisper-cli %s, but no model in %s (bash scripts/speech-model.sh)"
        % (whisper, paths.MODELS))))
    conv = [t for t in ("afconvert", "ffmpeg") if shutil.which(t)]
    out.append((True, "local assess: tutorboard/speech/tones.py, a prototype: "
                      "Mandarin tones and a word diff; others the word diff"))
    out.append((bool(conv), "audio:        %s" % (
        " and ".join(conv) + ("" if "ffmpeg" in conv else
                              "; ffmpeg MISSING, so a WebM take cannot be read")
        if conv else "neither afconvert nor ffmpeg: no take can be read")))
    return out


def witness(cfg=None):
    """`(ok, line)`: one word spoken by the TTS chain and heard by the STT
    chain."""
    cfg = speech.load() if cfg is None else cfg
    word = random.choice(WORDS)
    box = tempfile.mkdtemp(prefix="speech-witness-")
    try:
        m4a = os.path.join(box, "said.m4a")
        try:
            _got, spoke = speech.run("tts", LANG, {"text": word, "dest": m4a}, cfg=cfg)
            wav = audio.to_wav16k(m4a, os.path.join(box, "said.wav"))
            heard, heard_by = speech.run("stt", LANG, {"wav": wav}, cfg=cfg)
        except (speech.Refused, audio.Unconvertible) as exc:
            return False, "FAIL speech    %s" % " ".join(str(exc).split())[:400]
        said = heard.get("text") or ""
        if word not in re.findall(r"[a-z]+", said.lower()):
            return False, ("FAIL speech    %s spoke '%s' and %s heard '%s'"
                           % (spoke, word, heard_by, said[:80]))
        return True, ("ok   speech    %s spoke '%s' and %s heard it back"
                      % (spoke, word, heard_by))
    finally:
        shutil.rmtree(box, ignore_errors=True)


def report(dry=False, cfg=None, out=print):
    """Print the speech lines; True when nothing failed. Dry, the state alone
    never fails: a Mac without whisper still teaches."""
    cfg = speech.load() if cfg is None else cfg
    for kind in speech.KINDS:
        out(_chain_line(kind, LANG if kind != "assess" else "zh-CN", cfg))
    for _ok, line in local_state(cfg):
        out(line)
    if dry:
        return True
    ok, line = witness(cfg)
    out(line)
    return ok
