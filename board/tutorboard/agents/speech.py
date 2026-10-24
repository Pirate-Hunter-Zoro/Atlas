"""Who speaks, who listens and who judges pronunciation: the speech table.

A table of its own beside `recipes.DEFAULT_CONFIG["agents"]`, because the
assistants that teach are not the ones that hear: DeepSeek has no audio model.
Three jobs, each a `kind`:

    tts      text to an m4a the board plays
    stt      a 16 kHz mono WAV to the words heard, with timings when known
    assess   a WAV against the words it was meant to say: per-syllable tones,
             a word diff and a verdict

`DEFAULT_SPEECH` holds the recipes, `azure`, `openai` and `local`, and
`order`, the order each kind tries them in. `config.json`'s `speech` block is
laid over it the way `agents` is: `recipes` merges one level deeper (`"replace":
true` replaces an entry) and `order` per kind. No vendor is load-bearing:
`chain(kind, lang)` passes over a recipe that is unkeyed, missing its command,
out of allowance, stood down or without the language, and ALWAYS ends with
`local`, which runs on this Mac alone and which the config cannot remove. `run()` walks the chain the way
`seeing.describe` walks vision routes, each refusal passing to the next, and
writes one cost line for the recipe that answered.

A recipe added in the config names the code that drives it with `via`
(`azure`, `openai` or `local`), so a second Azure region is one entry, tried
once `order` names it.
"""

import base64
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import uuid

from tutorboard import keys, machine, paths
from tutorboard.speech import audio

KINDS = ("tts", "stt", "assess")
LOCAL = "local"
TIMEOUT = 60

# A stood-down or limited recipe is passed over this long, unless the provider
# said for how long.
DARK_SECONDS = 600
LIMIT_SECONDS = 3600

DEFAULT_SPEECH = {
    "order": {"tts": ["azure", "openai", "local"],
              "stt": ["azure", "openai", "local"],
              "assess": ["azure", "openai", "local"]},
    "recipes": {
        "azure": {
            "label": "Azure Speech",
            "needs_key": "AZURE_SPEECH_KEY",
            "region_key": "AZURE_SPEECH_REGION",
            # TTS by SSML; the output is WAV, made m4a here.
            "tts": {"endpoint": "https://{region}.tts.speech.microsoft.com/"
                                "cognitiveservices/v1",
                    "format": "riff-24khz-16bit-mono-pcm"},
            # STT and assessment: the REST short-audio endpoint, WAV PCM
            # 16 kHz mono, at most 30 s; assessment adds the base64
            # Pronunciation-Assessment header.
            "stt": {"endpoint": "https://{region}.stt.speech.microsoft.com/"
                                "speech/recognition/conversation/"
                                "cognitiveservices/v1"},
            "assess": {"endpoint": "https://{region}.stt.speech.microsoft.com/"
                                   "speech/recognition/conversation/"
                                   "cognitiveservices/v1",
                       "langs": ["zh-CN", "zh-HK", "zh-TW", "en-US", "en-GB",
                                 "en-AU", "en-CA", "en-IN", "ja-JP", "ko-KR",
                                 "fr-FR", "fr-CA", "de-DE", "es-ES", "es-MX",
                                 "it-IT", "pt-BR", "pt-PT", "nl-NL", "ru-RU",
                                 "ar-SA", "vi-VN", "th-TH", "hi-IN", "pl-PL",
                                 "sv-SE", "nb-NO", "da-DK", "fi-FI", "ca-ES",
                                 "ta-IN", "ms-MY"]},
            "voices": {"zh-CN": "zh-CN-XiaoxiaoNeural",
                       "zh-TW": "zh-TW-HsiaoChenNeural",
                       "ja-JP": "ja-JP-NanamiNeural",
                       "ko-KR": "ko-KR-SunHiNeural",
                       "fr-FR": "fr-FR-DeniseNeural",
                       "de-DE": "de-DE-KatjaNeural",
                       "es-ES": "es-ES-ElviraNeural",
                       "it-IT": "it-IT-ElsaNeural",
                       "pt-BR": "pt-BR-FranciscaNeural",
                       "ru-RU": "ru-RU-SvetlanaNeural",
                       "en-US": "en-US-JennyNeural",
                       "en-GB": "en-GB-SoniaNeural",
                       "ga-IE": ["ga-IE-OrlaNeural", "ga-IE-ColmNeural"]},
            # USD; the free tier covers most of a week's use.
            "prices": {"tts_per_char": 0.000016, "stt_per_minute": 0.0167,
                       "assess_per_minute": 0.022},
        },
        "openai": {
            "label": "OpenAI",
            "needs_key": "OPENAI_API_KEY",
            "tts": {"endpoint": "https://api.openai.com/v1/audio/speech",
                    "model": "gpt-4o-mini-tts", "voice": "alloy"},
            # Multipart, built by hand.
            "stt": {"endpoint": "https://api.openai.com/v1/audio/transcriptions",
                    "model": "gpt-4o-mini-transcribe"},
            "prices": {"tts_per_minute": 0.015, "stt_per_minute": 0.003},
        },
        "local": {
            "label": "this Mac",
            # `say` to m4a; espeak-ng for a language macOS has no voice for,
            # Irish (ga) first among them.
            "tts": {"cmd": ["say"], "fallback_cmd": ["espeak-ng"]},
            "stt": {"cmd": ["whisper-cli"], "model": "ggml-small-q5_1.bin"},
            "assess": {"module": "tutorboard.speech.tones"},
            # A premium voice first, when it is downloaded.
            "voices": {"zh-CN": "Tingting", "ja-JP": "Kyoko",
                       "fr-FR": "Amélie", "fr-CA": "Amélie",
                       "en-US": "Samantha", "en-GB": "Daniel"},
        },
    },
}

# `say` voices that are effects, not speakers.
NOVELTY = ("Albert", "Bad News", "Bahh", "Bells", "Boing", "Bubbles", "Cellos",
           "Good News", "Jester", "Organ", "Superstar", "Trinoids", "Whisper",
           "Wobble", "Zarvox", "Fred", "Junior", "Ralph", "Kathy")

LANG_RE = re.compile(r"\A[A-Za-z]{2,3}(?:[-_][A-Za-z0-9]{2,8}){0,2}\Z")


class Refused(Exception):
    """This recipe, or every recipe, could not do the job; the message says why."""


# ---------------------------------------------------------------------------
# the table, and this machine's config over it
# ---------------------------------------------------------------------------
def load(user=None):
    """`DEFAULT_SPEECH` with config.json's `speech` block laid over it.
    `user` stands in for the file's block (a test, or a caller holding it)."""
    cfg = json.loads(json.dumps(DEFAULT_SPEECH))
    if user is None:
        user = paths.config().get("speech")
    if not isinstance(user, dict):
        return cfg
    for name, spec in (user.get("recipes") or {}).items():
        have = cfg["recipes"].get(name)
        if spec is None:
            cfg["recipes"].pop(name, None)
        elif isinstance(spec, dict) and isinstance(have, dict) \
                and not spec.get("replace"):
            merged = dict(have)
            for k, v in spec.items():
                if isinstance(v, dict) and isinstance(merged.get(k), dict):
                    merged[k] = dict(merged[k], **v)
                else:
                    merged[k] = v
            cfg["recipes"][name] = merged
        elif isinstance(spec, dict):
            cfg["recipes"][name] = spec
    order = user.get("order")
    if isinstance(order, dict):
        for kind, names in order.items():
            if kind in KINDS and isinstance(names, list):
                cfg["order"][kind] = [n for n in names if isinstance(n, str)]
    _keep_local(cfg)
    return cfg


def _keep_local(cfg):
    """`local` ends every chain, so the config may tune it but never remove
    it: a recipe set to null or replaced gets back each job it lost, and it
    stays this Mac's, unkeyed and in every language."""
    have = cfg["recipes"].get(LOCAL)
    default = json.loads(json.dumps(DEFAULT_SPEECH["recipes"][LOCAL]))
    if not isinstance(have, dict):
        cfg["recipes"][LOCAL] = default
        return
    for kind in KINDS:
        if not isinstance(have.get(kind), dict):
            have[kind] = default[kind]
        else:
            have[kind].pop("langs", None)
    for field in ("via", "needs_key", "region_key", "langs", "replace"):
        have.pop(field, None)


def clean_lang(lang):
    """A BCP-47-ish tag, `zh-CN`, or None."""
    lang = str(lang or "").strip()
    if not LANG_RE.match(lang):
        return None
    bits = lang.replace("_", "-").split("-")
    return "-".join([bits[0].lower()] + [b.upper() if len(b) == 2 else b
                                         for b in bits[1:]])


def primary(lang):
    return (clean_lang(lang) or "").split("-")[0]


def _lang_in(lang, langs):
    """Does `langs` (tags, primary tags or `*`) take `lang`?"""
    lang = clean_lang(lang) or ""
    for one in langs or ():
        one = str(one)
        if one == "*" or (clean_lang(one) or "") == lang \
                or ("-" not in one and one.lower() == primary(lang)):
            return True
    return False


def via(spec, name):
    return (spec or {}).get("via") or name


def _key_missing(spec):
    """The key (or region) this recipe needs and keys.env lacks, or None."""
    need = keys.unkeyed(spec)
    if need:
        return need
    region = (spec or {}).get("region_key")
    if region and not keys.have(region):
        return region
    return None


# ---------------------------------------------------------------------------
# what is on this machine, for the local recipe
# ---------------------------------------------------------------------------
_VOICES = {}


def say_voices(cmd="say"):
    """`[(name, lang)]` from `say -v ?`, cached ten minutes; [] without `say`."""
    held = _VOICES.get(cmd)
    if held and time.time() - held[0] < 600:
        return held[1]
    out = []
    if shutil.which(cmd):
        try:
            got = subprocess.run([cmd, "-v", "?"], stdout=subprocess.PIPE,
                                 stderr=subprocess.DEVNULL, timeout=20)
            text = got.stdout.decode("utf-8", "replace")
        except (OSError, subprocess.SubprocessError):
            text = ""
        for line in text.splitlines():
            m = re.match(r"^(.+?)\s+([a-z]{2,3}_[A-Za-z0-9]{2,4})\s+#", line)
            if m:
                out.append((m.group(1).strip(), clean_lang(m.group(2))))
    _VOICES[cmd] = (time.time(), out)
    return out


def say_voice(spec, lang, wanted=None):
    """The `say` voice for `lang`: `wanted` if it is one, then the recipe's
    preference, then the first speaker of that language; None when macOS has
    no voice for it."""
    lang = clean_lang(lang)
    voices = say_voices((((spec or {}).get("tts") or {}).get("cmd") or ["say"])[0])

    def short(name):
        return name.split(" (")[0]
    for pick in (wanted, ((spec or {}).get("voices") or {}).get(lang)):
        if pick and any(short(n) == pick and v == lang for n, v in voices):
            return pick
    for name, v in voices:
        if v == lang and short(name) not in NOVELTY:
            return short(name)
    for name, v in voices:
        if primary(v) == primary(lang) and short(name) not in NOVELTY:
            return short(name)
    return None


def model_path(spec):
    """The ggml model whisper-cli loads: the recipe's, else any in MODELS."""
    want = ((spec or {}).get("stt") or {}).get("model") or ""
    first = os.path.join(paths.MODELS, want) if want else ""
    if first and os.path.isfile(first):
        return first
    try:
        names = sorted(n for n in os.listdir(paths.MODELS)
                       if n.startswith("ggml-") and n.endswith(".bin"))
    except OSError:
        names = []
    return os.path.join(paths.MODELS, names[0]) if names else None


def _local_missing(spec, kind, lang):
    """Why the local recipe cannot do `kind` in `lang` here, or None."""
    job = (spec or {}).get(kind) or {}
    if kind == "tts":
        if shutil.which((job.get("cmd") or ["say"])[0]) and say_voice(spec, lang):
            return None
        alt = (job.get("fallback_cmd") or ["espeak-ng"])[0]
        if shutil.which(alt):
            return None
        return ("macOS has no voice for %s and `%s` is not installed (brew "
                "install espeak-ng)" % (lang, alt) if shutil.which("say")
                else "neither `say` nor `%s` is here" % alt)
    if kind == "stt":
        exe = (job.get("cmd") or ["whisper-cli"])[0]
        if not shutil.which(exe):
            return "`%s` is not installed (brew install whisper-cpp)" % exe
        if not model_path(spec):
            return ("no whisper model in %s (bash scripts/speech-model.sh)"
                    % paths.MODELS)
        return None
    return None


# ---------------------------------------------------------------------------
# allowance and stand-down: speech's own record, so a spent speech key never
# reads as the tutor's allowance in `board limit` or /health
# ---------------------------------------------------------------------------
def _record_path():
    return os.path.join(paths.STATE_DIR, "speech.json")


def _record():
    try:
        with open(_record_path(), "r", encoding="utf-8") as fh:
            rec = json.load(fh)
    except (OSError, ValueError):
        return {}
    return rec if isinstance(rec, dict) else {}


def _mark(field, name, until, why=""):
    rec = _record()
    rec.setdefault(field, {})[name] = {"until": float(until), "why": str(why)[:300],
                                       "node": machine.node_name()}
    try:
        os.makedirs(paths.STATE_DIR, exist_ok=True)
        tmp = _record_path() + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(rec, fh, indent=2)
        os.replace(tmp, _record_path())
    except OSError:
        pass


def _marked(field, name, now=None):
    got = (_record().get(field) or {}).get(name)
    if not isinstance(got, dict):
        return None
    try:
        if float(got.get("until") or 0) <= (now or time.time()):
            return None
    except (TypeError, ValueError):
        return None
    return got


def mark_limited(name, until=None, why=""):
    _mark("limited", name, until or time.time() + LIMIT_SECONDS, why)


def mark_dark(name, why="", until=None):
    _mark("dark", name, until or time.time() + DARK_SECONDS, why)


def clear(name):
    rec = _record()
    for field in ("limited", "dark"):
        (rec.get(field) or {}).pop(name, None)
    try:
        if rec:
            with open(_record_path(), "w", encoding="utf-8") as fh:
                json.dump(rec, fh, indent=2)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# the chain
# ---------------------------------------------------------------------------
def unavailable(cfg, name, kind, lang, now=None):
    """Why recipe `name` cannot do `kind` in `lang` here now, or None: no
    recipe, no such job, unkeyed, its command missing, limited, stood down,
    or lacking the language."""
    spec = (cfg.get("recipes") or {}).get(name)
    if not isinstance(spec, dict):
        return "there is no speech recipe called '%s'" % name
    job = spec.get(kind)
    if not isinstance(job, dict):
        return "'%s' does no %s" % (name, kind)
    need = _key_missing(spec)
    if need:
        return "%s is not in %s" % (need, keys.store())
    kind_of = via(spec, name)
    if kind_of == LOCAL:
        gone = _local_missing(spec, kind, lang)
        if gone:
            return gone
    elif job.get("cmd") and not shutil.which(job["cmd"][0]):
        return "`%s` is not on the path here" % job["cmd"][0]
    held = _marked("limited", name, now)
    if held:
        return "its allowance is gone until %s" % time.strftime(
            "%H:%M", time.localtime(held["until"]))
    dark = _marked("dark", name, now)
    if dark:
        return "it is stood down until %s (%s)" % (
            time.strftime("%H:%M", time.localtime(dark["until"])),
            dark.get("why") or "it did not answer")
    langs = job.get("langs") if "langs" in job else spec.get("langs")
    if kind_of == "azure" and langs is None:
        langs = list((spec.get("voices") or {}).keys()) if kind == "tts" else ["*"]
    if langs is not None and not _lang_in(lang, langs):
        return "'%s' has no %s for %s" % (name, kind, lang)
    return None


def _names(cfg, kind):
    """The recipes `order` names for `kind`, in its order, and `local` last
    whatever the order says. A recipe added in the config is tried once the
    order names it."""
    said = [n for n in (cfg.get("order") or {}).get(kind) or [] if n != LOCAL]
    return list(dict.fromkeys(said)) + [LOCAL]


def explain(kind, lang, cfg=None, now=None):
    """`[(name, why-not or None)]` for every recipe of `kind`, in chain order."""
    cfg = load() if cfg is None else cfg
    return [(n, unavailable(cfg, n, kind, lang, now)) for n in _names(cfg, kind)]


def chain(kind, lang, cfg=None, now=None):
    """The recipes `run` tries for `kind` in `lang`, in order: each that can
    do it here, and `local` last, always, so its reason is the last word."""
    if kind not in KINDS:
        raise ValueError("a speech kind is one of %s" % ", ".join(KINDS))
    return [n for n, why in explain(kind, lang, cfg, now)
            if not why or n == LOCAL]


# ---------------------------------------------------------------------------
# running a job
# ---------------------------------------------------------------------------
def run(kind, lang, job, live=None, cfg=None):
    """Do `kind` through the first recipe in `chain` that can: `(result,
    name)`. Raises Refused with every recipe's reason when none could.

    `job` per kind:
      tts     {text, dest, voice?, pinyin?}            -> {path}
      stt     {wav}                                    -> {text, words}
      assess  {wav, ref, pinyin?, words?, heard?, reference?}
                                                       -> tones.assess's shape

    One line goes to `live/cost.jsonl` (the session's), or to the state
    directory's `speech-cost.jsonl` when there is no session.
    """
    cfg = load() if cfg is None else cfg
    lang = clean_lang(lang)
    if not lang:
        raise Refused("a language tag such as zh-CN is needed")
    if kind not in KINDS:
        raise ValueError("a speech kind is one of %s" % ", ".join(KINDS))
    said = []
    for name, why in explain(kind, lang, cfg):
        spec = cfg["recipes"].get(name) or {}
        if why:
            said.append("%s: %s" % (name, why))
            continue
        began = time.time()
        try:
            got = DRIVERS[(via(spec, name), kind)](spec, name, lang, job)
        except KeyError:
            said.append("%s: no driver for %s through '%s'"
                        % (name, kind, via(spec, name)))
            continue
        except (Refused, audio.Unconvertible) as exc:
            said.append("%s: %s" % (name, exc))
            continue
        got = dict(got or {}, by=name)
        record_cost(live, name, kind, lang, spec, job, got, time.time() - began)
        return got, name
    raise Refused("nobody could do %s in %s -- %s" % (kind, lang, " -- then ".join(said)))


def _usd(spec, kind, job, got):
    prices = (spec or {}).get("prices") or {}
    secs = float(got.get("seconds") or 0)
    if kind == "tts" and prices.get("tts_per_char"):
        return prices["tts_per_char"] * len(job.get("text") or "")
    per_min = prices.get("%s_per_minute" % kind)
    return per_min * secs / 60.0 if per_min else 0.0


def record_cost(live, name, kind, lang, spec, job, got, took):
    """One line: who did which job, how much audio or text, and what it cost."""
    rec = {"t": time.time(), "iso": time.strftime("%Y-%m-%d %H:%M:%S"),
           "kind": "speech", "speech": kind, "agent": "speech:%s" % name,
           "lang": lang, "requests": 1, "tokens": 0,
           "chars": len(job.get("text") or "") if kind == "tts" else 0,
           "seconds": round(float(got.get("seconds") or 0), 2),
           "took": round(took, 2),
           "usd": round(_usd(spec, kind, job, got), 6),
           "host": machine.node_name()}
    where = os.path.join(live, "cost.jsonl") if live else os.path.join(
        paths.STATE_DIR, "speech-cost.jsonl")
    try:
        os.makedirs(os.path.dirname(where), exist_ok=True)
        with open(where, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError:
        pass
    return rec


# ---------------------------------------------------------------------------
# HTTP, for the hosted recipes
# ---------------------------------------------------------------------------
def _endpoint(spec, kind):
    url = ((spec.get(kind) or {}).get("endpoint") or "")
    if "{region}" in url:
        url = url.replace("{region}", keys.get(spec.get("region_key")) or "")
    return url


def _post(name, url, body, headers):
    """The response body, or Refused. A host that does not answer is stood
    down; a 429 or a spent balance marks the recipe limited."""
    req = urllib.request.Request(url, data=body, method="POST", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:300].strip()
        if exc.code in (402, 429):
            mark_limited(name, why=detail)
        raise Refused("%s answered %s: %s" % (url.split("?")[0], exc.code, detail))
    except (urllib.error.URLError, OSError, ValueError) as exc:
        mark_dark(name, why=str(exc))
        raise Refused("%s could not be reached: %s" % (url.split("?")[0], exc))


def _json(raw, what):
    try:
        got = json.loads(raw.decode("utf-8", "replace"))
    except ValueError:
        raise Refused("%s did not answer JSON: %r" % (what, raw[:200]))
    if not isinstance(got, dict):
        raise Refused("%s answered %r" % (what, got))
    return got


def _wav_bytes(job):
    with open(job["wav"], "rb") as fh:
        return fh.read()


def _landed_wav(raw, dest):
    """Synthesised WAV bytes to the m4a at `dest`."""
    box = tempfile.mkdtemp(prefix="speech-tts-")
    try:
        wav = os.path.join(box, "said.wav")
        with open(wav, "wb") as fh:
            fh.write(raw)
        if not audio.wav_shape(wav):
            raise Refused("the audio that came back is not WAV")
        secs = audio.seconds(wav)
        audio.to_m4a(wav, dest)
        return {"path": dest, "seconds": secs}
    finally:
        shutil.rmtree(box, ignore_errors=True)


def _xml(text):
    return (str(text).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;").replace("'", "&apos;"))


def azure_voice(spec, lang, wanted=None):
    voices = (spec.get("voices") or {})
    got = voices.get(lang) or next((v for k, v in voices.items()
                                    if primary(k) == primary(lang)), None)
    choices = got if isinstance(got, list) else [got] if got else []
    if wanted and (wanted in choices or str(wanted).startswith(lang + "-")):
        return wanted
    return choices[0] if choices else None


def ssml(lang, voice, text, pinyin=None):
    """The SSML Azure reads. Mandarin with `pinyin` is spoken from the pinyin
    (SAPI phones, `ni 3 hao 3`), so a polyphone is read as taught."""
    said = _xml(text)
    if pinyin and primary(lang) == "zh":
        phones = " ".join("%s %s" % (s[:-1], s[-1]) if s[-1:].isdigit() else s
                          for s in pinyin_syllables(pinyin))
        said = '<phoneme alphabet="sapi" ph="%s">%s</phoneme>' % (_xml(phones), said)
    return ("<speak version='1.0' xml:lang='%s' "
            "xmlns='http://www.w3.org/2001/10/synthesis'>"
            "<voice name='%s'>%s</voice></speak>" % (lang, _xml(voice), said))


def _azure_tts(spec, name, lang, job):
    voice = azure_voice(spec, lang, job.get("voice"))
    if not voice:
        raise Refused("no Azure voice for %s" % lang)
    raw = _post(name, _endpoint(spec, "tts"),
                ssml(lang, voice, job["text"], job.get("pinyin")).encode("utf-8"),
                {"Ocp-Apim-Subscription-Key": keys.get(spec.get("needs_key")) or "",
                 "Content-Type": "application/ssml+xml",
                 "X-Microsoft-OutputFormat": (spec.get("tts") or {}).get("format")
                 or "riff-24khz-16bit-mono-pcm",
                 "User-Agent": "tutor-board"})
    return _landed_wav(raw, job["dest"])


def assessment_header(ref):
    """The Pronunciation-Assessment header: base64 of its JSON."""
    params = {"ReferenceText": ref, "GradingSystem": "HundredMark",
              "Granularity": "Phoneme", "Dimension": "Comprehensive",
              "EnableMiscue": True}
    return base64.b64encode(json.dumps(params, ensure_ascii=False)
                            .encode("utf-8")).decode("ascii")


def _azure_recognise(spec, name, lang, job, ref=None):
    kind = "assess" if ref else "stt"
    url = _endpoint(spec, kind) + "?language=%s&format=detailed" % lang
    headers = {"Ocp-Apim-Subscription-Key": keys.get(spec.get("needs_key")) or "",
               "Content-Type": "audio/wav; codecs=audio/pcm; samplerate=16000",
               "Accept": "application/json"}
    if ref:
        headers["Pronunciation-Assessment"] = assessment_header(ref)
    got = _json(_post(name, url, _wav_bytes(job), headers), "Azure")
    status = got.get("RecognitionStatus")
    if status in ("NoMatch", "InitialSilenceTimeout", "BabbleTimeout"):
        return got, None
    if status != "Success":
        raise Refused("Azure could not recognise it: %s" % status)
    best = (got.get("NBest") or [{}])[0]
    return got, best


def _ticks(t):
    try:
        return float(t) / 1e7
    except (TypeError, ValueError):
        return None


def _azure_stt(spec, name, lang, job):
    got, best = _azure_recognise(spec, name, lang, job)
    words = []
    for w in (best or {}).get("Words") or []:
        start = _ticks(w.get("Offset"))
        dur = _ticks(w.get("Duration")) or 0
        words.append({"text": w.get("Word", ""), "start": start,
                      "end": start + dur if start is not None else None})
    return {"text": (got.get("DisplayText") or "").strip(), "words": words,
            "seconds": audio.seconds(job["wav"])}


def _pa(obj, field):
    """A pronunciation score, flat or under `PronunciationAssessment`."""
    if field in obj:
        return obj.get(field)
    return (obj.get("PronunciationAssessment") or {}).get(field)


ERROR_OPS = {"None": "equal", "Omission": "missing", "Insertion": "extra",
             "Mispronunciation": "wrong", "UnexpectedBreak": "equal",
             "MissingBreak": "equal", "Monotone": "equal"}


def _azure_assess(spec, name, lang, job):
    from tutorboard.speech import tones
    got, best = _azure_recognise(spec, name, lang, job, ref=job["ref"])
    secs = audio.seconds(job["wav"])
    if best is None:
        return dict(tones.unheard(job["ref"], lang, job.get("pinyin")),
                    seconds=secs)
    targets = tones.targets(job.get("pinyin"))
    syllables, words, n = [], [], 0
    for w in best.get("Words") or []:
        acc = _pa(w, "AccuracyScore")
        op = ERROR_OPS.get(str(_pa(w, "ErrorType") or "None"), "wrong")
        words.append({"op": op,
                      "target": w.get("Word", "") if op != "extra" else "",
                      "heard": w.get("Word", "") if op != "missing" else "",
                      "score": acc})
        if op == "extra":
            continue
        chars = [c for c in w.get("Word", "") if not c.isspace()] \
            if primary(lang) == "zh" else [w.get("Word", "")]
        for ch in chars:
            t = targets[n] if n < len(targets) else None
            n += 1
            sure = (acc or 0) / 100.0
            syllables.append({
                "syllable": ch, "target": t and t["target"],
                "expect": t and t["expect"],
                "heard": (t and t["expect"]) if sure >= 0.8 and op == "equal"
                else "unknown",
                "confidence": round(sure, 2)})
    score = _pa(best, "PronScore")
    if score is None:
        score = _pa(best, "AccuracyScore")
    off = [w["target"] or w["heard"] for w in words if w["op"] != "equal"]
    verdict = ("score %s/100" % int(round(score or 0))
               + (": check %s" % ", ".join("'%s'" % o for o in off[:4]) if off
                  else ", every word as written"))
    return {"verdict": verdict, "score": score, "syllables": syllables,
            "words": words, "heard": (got.get("DisplayText") or "").strip(),
            "scores": {k: _pa(best, k) for k in ("AccuracyScore", "FluencyScore",
                                                  "CompletenessScore", "PronScore")},
            "prototype": False, "seconds": secs}


def _openai_tts(spec, name, lang, job):
    tts = spec.get("tts") or {}
    body = json.dumps({
        "model": tts.get("model") or "gpt-4o-mini-tts",
        "input": job["text"],
        "voice": job.get("voice") if job.get("voice") in OPENAI_VOICES
        else tts.get("voice") or "alloy",
        "response_format": "wav",
        "instructions": "Speak this in the language tagged %s, clearly and at a "
                        "learner's pace." % lang}).encode("utf-8")
    raw = _post(name, _endpoint(spec, "tts"), body, {
        "Authorization": "Bearer %s" % (keys.get(spec.get("needs_key")) or ""),
        "Content-Type": "application/json"})
    return _landed_wav(raw, job["dest"])


OPENAI_VOICES = ("alloy", "ash", "ballad", "coral", "echo", "fable", "nova",
                 "onyx", "sage", "shimmer", "verse")


def multipart_body(fields, files):
    """`(body, content type)`: a multipart/form-data body built by hand.
    `fields` is `[(name, value)]`; `files` is `[(name, filename, type, bytes)]`."""
    boundary = "----tutorboard%s" % uuid.uuid4().hex
    out = []
    for name, value in fields:
        out.append(("--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n"
                    % (boundary, name)).encode("utf-8"))
        out.append(str(value).encode("utf-8") + b"\r\n")
    for name, filename, ctype, data in files:
        out.append(("--%s\r\nContent-Disposition: form-data; name=\"%s\"; "
                    "filename=\"%s\"\r\nContent-Type: %s\r\n\r\n"
                    % (boundary, name, filename, ctype)).encode("utf-8"))
        out.append(data + b"\r\n")
    out.append(("--%s--\r\n" % boundary).encode("utf-8"))
    return b"".join(out), "multipart/form-data; boundary=%s" % boundary


def _openai_stt(spec, name, lang, job):
    stt = spec.get("stt") or {}
    body, ctype = multipart_body(
        [("model", stt.get("model") or "gpt-4o-mini-transcribe"),
         ("language", primary(lang)), ("response_format", "json")],
        [("file", "take.wav", "audio/wav", _wav_bytes(job))])
    got = _json(_post(name, _endpoint(spec, "stt"), body, {
        "Authorization": "Bearer %s" % (keys.get(spec.get("needs_key")) or ""),
        "Content-Type": ctype}), "OpenAI")
    return {"text": (got.get("text") or "").strip(), "words": [],
            "seconds": audio.seconds(job["wav"])}


def _local_tts(spec, name, lang, job):
    text = job["text"]
    box = tempfile.mkdtemp(prefix="speech-say-")
    try:
        said = os.path.join(box, "text.txt")
        with open(said, "w", encoding="utf-8") as fh:
            fh.write(text)
        voice = say_voice(spec, lang, job.get("voice"))
        tts = spec.get("tts") or {}
        if voice and shutil.which((tts.get("cmd") or ["say"])[0]):
            out = os.path.join(box, "said.m4a")
            _cmd((tts.get("cmd") or ["say"]) + [
                "-v", voice, "-o", out, "--file-format=m4af", "--data-format=aac",
                "-f", said])
            shutil.move(out, job["dest"])
            return {"path": job["dest"], "voice": voice}
        alt = tts.get("fallback_cmd") or ["espeak-ng"]
        if not shutil.which(alt[0]):
            raise Refused("macOS has no voice for %s, and `%s` is not installed"
                          % (lang, alt[0]))
        wav = os.path.join(box, "said.wav")
        _cmd(alt + ["-v", primary(lang), "-w", wav, "-f", said])
        audio.to_m4a(wav, job["dest"])
        return {"path": job["dest"], "voice": "%s %s" % (alt[0], primary(lang)),
                "seconds": audio.seconds(wav)}
    finally:
        shutil.rmtree(box, ignore_errors=True)


def _cmd(argv, timeout=TIMEOUT):
    try:
        done = subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, timeout=timeout)
    except FileNotFoundError:
        raise Refused("`%s` is not on the path here" % argv[0])
    except subprocess.TimeoutExpired:
        raise Refused("`%s` took more than %d s" % (argv[0], timeout))
    if done.returncode != 0:
        raise Refused("`%s` exited %d: %s" % (
            argv[0], done.returncode,
            (done.stdout or b"").decode("utf-8", "replace").strip()[-300:]))
    return (done.stdout or b"").decode("utf-8", "replace")


# Whisper writes Mandarin as traditional characters unless told otherwise.
WHISPER_PROMPTS = {"zh": "以下是普通话的句子。"}


def _local_stt(spec, name, lang, job):
    stt = spec.get("stt") or {}
    model = model_path(spec)
    if not model:
        raise Refused("no whisper model in %s" % paths.MODELS)
    box = tempfile.mkdtemp(prefix="speech-whisper-")
    try:
        base = os.path.join(box, "heard")
        argv = (stt.get("cmd") or ["whisper-cli"]) + [
            "-m", model, "-l", primary(lang), "-f", job["wav"], "-oj", "-of", base,
            "-ml", "1", "-np"]
        if WHISPER_PROMPTS.get(primary(lang)):
            argv += ["--prompt", WHISPER_PROMPTS[primary(lang)]]
        _cmd(argv, timeout=120)
        try:
            with open(base + ".json", "r", encoding="utf-8", errors="replace") as fh:
                got = json.load(fh)
        except (OSError, ValueError) as exc:
            raise Refused("whisper-cli wrote no transcript: %s" % exc)
    finally:
        shutil.rmtree(box, ignore_errors=True)
    return dict(whisper_words(got), seconds=audio.seconds(job["wav"]))


def whisper_words(got):
    """`{text, words}` from whisper-cli's `-oj` output, one segment a word
    under `-ml 1`."""
    words, text = [], ""
    for seg in (got or {}).get("transcription") or []:
        said = seg.get("text") or ""
        text += said
        off = seg.get("offsets") or {}
        if said.strip():
            words.append({"text": said.strip(),
                          "start": (off.get("from") or 0) / 1000.0,
                          "end": (off.get("to") or 0) / 1000.0})
    return {"text": text.strip(), "words": words}


def _local_assess(spec, name, lang, job):
    from tutorboard.speech import tones
    return tones.assess(job["wav"], job["ref"], lang, pinyin=job.get("pinyin"),
                        words=job.get("words"), heard=job.get("heard"),
                        reference=job.get("reference"))


def pinyin_syllables(pinyin):
    from tutorboard.speech import tones
    return [s["syllable"] + (s["target"][1:] if s["target"] and
                             s["target"].startswith("T") else "5")
            for s in tones.targets(pinyin)]


DRIVERS = {
    ("azure", "tts"): _azure_tts,
    ("azure", "stt"): _azure_stt,
    ("azure", "assess"): _azure_assess,
    ("openai", "tts"): _openai_tts,
    ("openai", "stt"): _openai_stt,
    ("local", "tts"): _local_tts,
    ("local", "stt"): _local_stt,
    ("local", "assess"): _local_assess,
}


def listing(lang="en-US", cfg=None):
    """What `board doctor --dry` prints: per kind, each recipe and why not."""
    cfg = load() if cfg is None else cfg
    return dict((kind, explain(kind, lang, cfg)) for kind in KINDS)
