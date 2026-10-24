#!/usr/bin/env python3
"""Speech: every tutor speaks, listens and judges pronunciation.

    python3 test/speech.py

Nothing here needs a network, a key or a speech binary. A local http.server
stands in for Azure and OpenAI; a script stands in for whisper-cli and another
for `say`; every WAV is synthesised at run time with `wave`.

  - THE TABLE: azure, openai and local, in that order for every kind; the
    config's `speech` block is laid over it; `chain` passes over a recipe
    that is unkeyed, missing its command, limited, stood down or without the
    language, and always ends with local.
  - THE HOSTED RECIPES, against the stand-in: Azure's SSML, its short-audio
    STT and the base64 Pronunciation-Assessment header; OpenAI's speech JSON
    and the multipart built by hand. A refusal passes the job on; a 429
    marks the recipe limited and an unreachable host stands it down. Each job
    writes one cost line.
  - THE TONE CHECK, on sine sweeps: T1-T4 in any order, through voiced runs
    and through whisper's timings; a split syllable merged back; silence is
    unknown; pinyin parsed with sandhi; DTW; the word diff; the prototype
    label on every result.
  - THE ROUTE, end to end with STT stubbed: a take saved under the session's
    speech/, heard, judged, a turn record and a waking `[speech]` line whose
    `file:` is the heard record and never the audio; an ended session 409;
    phrases served by a strict sha name; a card read without its math.
  - THE CARDS: a `say` fence becomes a placeholder and a job for the cache.
  - SETUP: the model download is checksummed and a second run fetches nothing.
  - THE REAL BINARIES, when this Mac has them: one word spoken and heard back.
    Absent, that witness is SKIPPED, loudly.
"""

import base64
import contextlib
import http.client
import http.server
import importlib.machinery
import importlib.util
import io
import json
import math
import os
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ATLAS_ROOT = os.path.dirname(ROOT)
sys.path.insert(0, ROOT)

box = os.path.realpath(tempfile.mkdtemp(prefix="speech-test-"))
atlas = os.path.join(box, "Atlas")
os.environ["BOARD_STATE_DIR"] = os.path.join(box, "state")
os.environ["TUTORBOARD_TRASH"] = os.path.join(box, "trash")
os.environ["XDG_CONFIG_HOME"] = os.path.join(box, "config")
os.environ["TUTORBOARD_COURSES"] = atlas
os.environ["TUTORBOARD_PAGES"] = os.path.join(box, "pages")
os.environ["TUTORBOARD_SPEECH"] = os.path.join(box, "speech-cache")
os.environ["TUTORBOARD_MODELS"] = os.path.join(box, "models")
os.environ.setdefault("BOARD_NO_TAILNET", "1")
os.environ.pop("TUTORBOARD_TURN", None)

from tutorboard import audit, keys, paths, sense             # noqa: E402
from tutorboard import sessions                               # noqa: E402
from tutorboard.agents import speech                          # noqa: E402
from tutorboard.course import config                          # noqa: E402
from tutorboard.course import repo as course_repo             # noqa: E402
from tutorboard.lesson import cards, inbox                    # noqa: E402
from tutorboard.server import handler, multipart              # noqa: E402
from tutorboard.server.routes import speaking                 # noqa: E402
from tutorboard.speech import audio, synth, tones             # noqa: E402

fails = []
R = 16000
CONVERTS = bool(shutil.which("afconvert") or shutil.which("ffmpeg"))


def check(name, cond, detail=""):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)
        if detail:
            for line in str(detail).splitlines()[:12]:
                print("       " + line)


def skip(name, why):
    print("SKIPPED %s -- %s" % (name, why))


# ---------------------------------------------------------------------------
# audio, made here
# ---------------------------------------------------------------------------
CONTOURS = {
    "T1": lambda t: 230.0,
    "T2": lambda t: 170.0 + 100.0 * t,
    "T3": lambda t: (185.0 - 55.0 * t / 0.6) if t < 0.6 else (130.0 + 35.0 * (t - 0.6) / 0.4),
    "T4": lambda t: 270.0 - 130.0 * t,
}


def syllable(f_of_t, dur=0.3, amp=0.5):
    """A voiced syllable: three harmonics on a pitch contour, with soft edges."""
    out, ph, n = [], 0.0, int(dur * R)
    edge = 0.02 * R
    for i in range(n):
        ph += 2 * math.pi * f_of_t(i / float(n)) / R
        env = min(1.0, i / edge, (n - i) / edge)
        out.append(amp * env * (math.sin(ph) + 0.5 * math.sin(2 * ph)
                                + 0.25 * math.sin(3 * ph)) / 1.75)
    return out


def silence(dur=0.12):
    return [0.0] * int(dur * R)


def phrase(names, dur=0.3, gap=0.12):
    """Syllables in these tones, separated by silence; with the span of each."""
    out, spans = silence(gap), []
    for name in names:
        start = len(out) / float(R)
        out += syllable(CONTOURS[name], dur)
        spans.append((start, len(out) / float(R)))
        out += silence(gap)
    return out, spans


def wav(path, samples):
    return audio.write_wav(path, samples, R)


# ---------------------------------------------------------------------------
# keys and config
# ---------------------------------------------------------------------------
def write_keys(**pairs):
    os.makedirs(paths.CONFIG_DIR, exist_ok=True)
    with open(paths.KEYS, "w") as fh:
        for k, v in pairs.items():
            fh.write("%s=%s\n" % (k, v))
    os.chmod(paths.KEYS, stat.S_IRUSR | stat.S_IWUSR)
    keys.forget()


def write_config(block):
    os.makedirs(paths.CONFIG_DIR, exist_ok=True)
    with open(paths.CONFIG, "w") as fh:
        json.dump({"speech": block}, fh)


def clear_marks():
    try:
        os.remove(os.path.join(paths.STATE_DIR, "speech.json"))
    except OSError:
        pass


try:
    # =======================================================================
    # 1. THE TABLE
    # =======================================================================
    D = speech.DEFAULT_SPEECH
    check("the table holds azure, openai and local",
          set(D["recipes"]) == {"azure", "openai", "local"})
    check("and tries them in that order for every kind",
          all(D["order"][k] == ["azure", "openai", "local"] for k in speech.KINDS))
    az = D["recipes"]["azure"]
    check("azure takes AZURE_SPEECH_KEY and AZURE_SPEECH_REGION",
          az["needs_key"] == "AZURE_SPEECH_KEY"
          and az["region_key"] == "AZURE_SPEECH_REGION")
    check("azure's Irish voices are Orla and Colm",
          az["voices"]["ga-IE"] == ["ga-IE-OrlaNeural", "ga-IE-ColmNeural"])
    oa = D["recipes"]["openai"]
    check("openai speaks with gpt-4o-mini-tts and hears with gpt-4o-mini-transcribe",
          oa["tts"]["model"] == "gpt-4o-mini-tts"
          and oa["stt"]["model"] == "gpt-4o-mini-transcribe"
          and "assess" not in oa)
    lo = D["recipes"]["local"]
    check("local is say (espeak-ng after it), whisper-cli and the tone check",
          lo["tts"]["cmd"] == ["say"] and lo["tts"]["fallback_cmd"] == ["espeak-ng"]
          and lo["stt"]["cmd"] == ["whisper-cli"]
          and lo["assess"]["module"] == "tutorboard.speech.tones"
          and not lo.get("needs_key"))

    cfg = speech.load({"order": {"tts": ["openai", "azure"]},
                       "recipes": {"azure": {"voices": {"zh-CN": "zh-CN-YunxiNeural"}},
                                   "spare": {"via": "azure", "needs_key": "X",
                                             "tts": {"endpoint": "http://x"}},
                                   "openai": None}})
    check("the config's speech block is laid over the table: order per kind",
          cfg["order"]["tts"] == ["openai", "azure"]
          and cfg["order"]["stt"] == ["azure", "openai", "local"])
    check("a recipe merges one level deeper, keeping what it does not name",
          cfg["recipes"]["azure"]["voices"]["zh-CN"] == "zh-CN-YunxiNeural"
          and cfg["recipes"]["azure"]["voices"]["ja-JP"] == "ja-JP-NanamiNeural"
          and cfg["recipes"]["azure"]["needs_key"] == "AZURE_SPEECH_KEY"
          and cfg["recipes"]["azure"]["tts"]["format"] == "riff-24khz-16bit-mono-pcm")
    check("a new recipe is added and null removes one",
          "spare" in cfg["recipes"] and "openai" not in cfg["recipes"])
    for said, block in (("null", None),
                        ("replaced", {"replace": True, "tts": {"cmd": ["say"]}}),
                        ("made hosted", {"via": "azure", "needs_key": "NOPE",
                                         "langs": ["fr"],
                                         "stt": {"cmd": ["whisper-cli"], "langs": ["fr"]}})):
        kept = speech.load({"recipes": {"local": block}})["recipes"]["local"]
        check("the config cannot take local away: %s, it still does every job "
              "here, unkeyed, in every language" % said,
              all(isinstance(kept.get(k), dict) for k in speech.KINDS)
              and not any(f in kept for f in ("via", "needs_key", "region_key", "langs"))
              and not any("langs" in kept[k] for k in speech.KINDS)
              and speech.unavailable({"recipes": {"local": kept}}, "local", "assess",
                                     "zh-CN") is None, kept)
    check("the defaults themselves are never changed by a load",
          "openai" in speech.DEFAULT_SPEECH["recipes"])

    # A fake `say`: it lists voices, and writes bytes where -o says.
    bin_dir = os.path.join(box, "bin")
    os.makedirs(bin_dir)
    fake_say = os.path.join(bin_dir, "fake-say")
    with open(fake_say, "w") as fh:
        fh.write("#!/bin/sh\n"
                 "if [ \"$2\" = '?' ]; then\n"
                 "  echo 'Tingting (Chinese (China mainland)) zh_CN    # hi'\n"
                 "  echo 'Bubbles             en_US    # hi'\n"
                 "  echo 'Samantha            en_US    # hi'\n"
                 "  exit 0; fi\n"
                 "while [ $# -gt 0 ]; do\n"
                 "  if [ \"$1\" = -o ]; then shift; printf 'fake m4a' > \"$1\"; fi\n"
                 "  if [ \"$1\" = -v ]; then shift; echo \"$1\" >> %r; fi\n"
                 "  shift; done\n" % os.path.join(box, "say-voices.log"))
    os.chmod(fake_say, 0o755)

    # A fake whisper-cli: the transcript and timings a test puts in WHISPER_SAYS.
    fake_whisper = os.path.join(bin_dir, "fake-whisper")
    with open(fake_whisper, "w") as fh:
        fh.write("#!/usr/bin/env python3\n"
                 "import json, os, sys\n"
                 "a = sys.argv[1:]\n"
                 "out = a[a.index('-of') + 1]\n"
                 "assert os.path.isfile(a[a.index('-m') + 1]), 'no model'\n"
                 "assert os.path.isfile(a[a.index('-f') + 1]), 'no wav'\n"
                 "import time\n"
                 "time.sleep(float(os.environ.get('WHISPER_SLEEP') or 0))\n"
                 "said = json.load(open(os.environ['WHISPER_SAYS']))\n"
                 "if 'raw_hex' in said:\n"
                 "    open(out + '.json', 'wb').write(bytes.fromhex(said['raw_hex']))\n"
                 "    sys.exit(0)\n"
                 "said['argv'] = a\n"
                 "json.dump(said, open(out + '.json', 'w'))\n")
    os.chmod(fake_whisper, 0o755)
    os.makedirs(paths.MODELS)
    with open(os.path.join(paths.MODELS, "ggml-small-q5_1.bin"), "wb") as fh:
        fh.write(b"not really a model")

    LOCAL = {"tts": {"cmd": [fake_say], "fallback_cmd": [os.path.join(bin_dir, "no-espeak")]},
             "stt": {"cmd": [fake_whisper]}}

    write_keys()
    cfg = speech.load({"recipes": {"local": LOCAL}})
    check("unkeyed, azure and openai are passed over and local is the chain",
          speech.chain("tts", "zh-CN", cfg) == ["local"]
          and speech.chain("stt", "zh-CN", cfg) == ["local"])
    why = dict(speech.explain("stt", "zh-CN", cfg))
    check("and each is named with the key it lacks",
          "AZURE_SPEECH_KEY" in why["azure"] and "OPENAI_API_KEY" in why["openai"])
    gone = speech.load({"recipes": {"local": {"stt": {"cmd": [os.path.join(bin_dir, "nope")]}}}})
    check("local ends the chain even when it cannot do the job, so its reason is last",
          speech.chain("stt", "zh-CN", gone) == ["local"]
          and "not installed" in dict(speech.explain("stt", "zh-CN", gone))["local"])
    try:
        speech.run("stt", "zh-CN", {"wav": "/nowhere.wav"}, cfg=gone)
        said = ""
    except speech.Refused as exc:
        said = str(exc)
    check("and run refuses in every recipe's words",
          "azure:" in said and "openai:" in said and "local:" in said, said)
    check("Irish has no local voice without espeak-ng, and says so",
          "espeak-ng" in (dict(speech.explain("tts", "ga-IE", cfg))["local"] or ""))

    write_keys(AZURE_SPEECH_KEY="az-key", AZURE_SPEECH_REGION="westeurope",
               OPENAI_API_KEY="oa-key")
    full = speech.load({"recipes": {"local": LOCAL}})
    check("keyed, the chain is azure, openai, local",
          speech.chain("tts", "zh-CN", full) == ["azure", "openai", "local"])
    check("openai does no assessment, so assess is azure then local",
          speech.chain("assess", "zh-CN", full) == ["azure", "local"])
    check("a language a recipe lacks passes it over: no Azure assessment of Irish",
          speech.chain("assess", "ga-IE", full) == ["local"]
          and speech.chain("tts", "ga-IE", full)[0] == "azure")
    check("and no Azure voice for Swahili",
          "azure" not in speech.chain("tts", "sw-KE", full))
    swapped = speech.load({"order": {"tts": ["openai", "local", "azure"]},
                           "recipes": {"local": LOCAL}})
    check("the order the config gives is the order tried, local still last",
          speech.chain("tts", "zh-CN", swapped) == ["openai", "azure", "local"])
    only = speech.load({"order": {"stt": ["local"]}, "recipes": {"local": LOCAL}})
    check("and a recipe the order does not name is not tried",
          speech.chain("stt", "zh-CN", only) == ["local"])
    speech.mark_limited("azure", time.time() + 600, "429")
    check("a limited recipe is passed over",
          speech.chain("stt", "zh-CN", full) == ["openai", "local"]
          and "allowance" in dict(speech.explain("stt", "zh-CN", full))["azure"])
    clear_marks()
    speech.mark_dark("openai", "no route", time.time() + 600)
    check("so is a stood-down one",
          speech.chain("stt", "zh-CN", full) == ["azure", "local"]
          and "stood down" in dict(speech.explain("stt", "zh-CN", full))["openai"])
    clear_marks()
    from tutorboard import limits
    check("and speech's marks never read as the tutor's allowance",
          not limits.limit_record())

    # =======================================================================
    # 2. THE HOSTED RECIPES, against a stand-in
    # =======================================================================
    seen = []
    behave = {"azure_tts": 200, "openai_stt": 200, "azure_stt": 200}
    reply_wav = os.path.join(box, "reply.wav")
    wav(reply_wav, syllable(CONTOURS["T1"], 0.4))
    with open(reply_wav, "rb") as fh:
        REPLY = fh.read()

    class Fake(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            n = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(n)
            rec = {"path": self.path, "headers": self.headers, "body": body}
            seen.append(rec)
            if self.path.startswith("/azure/tts"):
                status = behave["azure_tts"]
                return self.answer(status, REPLY if status == 200 else b"no", "audio/wav")
            if self.path.startswith("/azure/stt"):
                if behave["azure_stt"] != 200:
                    return self.answer(behave["azure_stt"], b"slow down", "text/plain")
                pa = self.headers.get("Pronunciation-Assessment")
                if pa:
                    rec["pa"] = json.loads(base64.b64decode(pa).decode("utf-8"))
                    got = {"RecognitionStatus": "Success", "DisplayText": "你好。",
                           "NBest": [{"PronScore": 82.5, "AccuracyScore": 80,
                                      "FluencyScore": 90, "CompletenessScore": 100,
                                      "Words": [
                                          {"Word": "你", "AccuracyScore": 95,
                                           "ErrorType": "None"},
                                          {"Word": "好", "AccuracyScore": 40,
                                           "ErrorType": "Mispronunciation"}]}]}
                else:
                    got = {"RecognitionStatus": "Success", "DisplayText": "你好。",
                           "NBest": [{"Display": "你好。", "Words": [
                               {"Word": "你好", "Offset": 1200000,
                                "Duration": 6000000}]}]}
                return self.answer(200, json.dumps(got).encode("utf-8"),
                                   "application/json")
            if self.path.startswith("/openai/speech"):
                return self.answer(200, REPLY, "audio/wav")
            if self.path.startswith("/openai/transcriptions"):
                if behave["openai_stt"] != 200:
                    return self.answer(behave["openai_stt"], b"down", "text/plain")
                fields, folder = {}, tempfile.mkdtemp(dir=box)
                boundary = self.headers["Content-Type"].split("boundary=")[1].encode()
                got = multipart.save_parts(io.BytesIO(body), len(body), boundary,
                                           folder, lambda i, f: os.path.join(folder, f),
                                           fields=fields)
                with open(got[0][1], "rb") as fh:
                    rec["file"] = fh.read()
                rec["fields"], rec["filename"] = fields, got[0][0]
                return self.answer(200, json.dumps({"text": "你好"}).encode("utf-8"),
                                   "application/json")
            return self.answer(404, b"?", "text/plain")

        def answer(self, status, data, ctype):
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    fake = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Fake)
    threading.Thread(target=fake.serve_forever, daemon=True).start()
    base = "http://127.0.0.1:%d" % fake.server_port
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        dead = "http://127.0.0.1:%d" % s.getsockname()[1]
    HOSTED = {"azure": {"tts": {"endpoint": base + "/azure/tts/{region}"},
                        "stt": {"endpoint": base + "/azure/stt/{region}"},
                        "assess": {"endpoint": base + "/azure/stt/{region}"}},
              "openai": {"tts": {"endpoint": base + "/openai/speech"},
                         "stt": {"endpoint": base + "/openai/transcriptions"}},
              "local": LOCAL}
    live = os.path.join(box, "live")
    os.makedirs(live)
    take_wav = os.path.join(box, "take.wav")
    samples, spans = phrase(["T2", "T3"])
    wav(take_wav, samples)
    with open(take_wav, "rb") as fh:
        TAKE = fh.read()

    cfg = speech.load({"recipes": HOSTED})
    if CONVERTS:
        dest = os.path.join(box, "zh.m4a")
        got, by = speech.run("tts", "zh-CN", {"text": "你好", "pinyin": "ni3 hao3",
                                              "dest": dest}, live=live, cfg=cfg)
        req = seen[-1]
        check("azure speaks first: SSML to the regional endpoint with the key",
              by == "azure" and req["path"].endswith("/westeurope")
              and req["headers"].get("Ocp-Apim-Subscription-Key") == "az-key"
              and req["headers"].get("Content-Type") == "application/ssml+xml"
              and req["headers"].get("X-Microsoft-OutputFormat")
              == "riff-24khz-16bit-mono-pcm", req["headers"])
        ssml = req["body"].decode("utf-8")
        check("in the language's voice, the pinyin read as SAPI phones",
              "zh-CN-XiaoxiaoNeural" in ssml and "xml:lang='zh-CN'" in ssml
              and 'alphabet="sapi" ph="ni 3 hao 3"' in ssml, ssml)
        check("and the WAV it answers lands as an m4a",
              os.path.getsize(dest) > 0 and open(dest, "rb").read(12)[4:8] == b"ftyp")
        costs = [json.loads(l) for l in open(os.path.join(live, "cost.jsonl"))]
        check("one cost line, priced per character",
              len(costs) == 1 and costs[0]["agent"] == "speech:azure"
              and costs[0]["kind"] == "speech" and costs[0]["speech"] == "tts"
              and costs[0]["chars"] == 2 and costs[0]["usd"] > 0, costs)
        behave["azure_tts"] = 500
        got, by = speech.run("tts", "zh-CN", {"text": "你好", "dest": dest},
                             live=live, cfg=cfg)
        req = json.loads(seen[-1]["body"].decode("utf-8"))
        check("azure refusing, openai speaks: gpt-4o-mini-tts, WAV back",
              by == "openai" and req["model"] == "gpt-4o-mini-tts"
              and req["input"] == "你好" and req["response_format"] == "wav"
              and seen[-1]["headers"].get("Authorization") == "Bearer oa-key", req)
        check("and the refusal alone marks nothing",
              speech.chain("tts", "zh-CN", cfg)[0] == "azure")
        behave["azure_tts"] = 200
    else:
        skip("hosted TTS to m4a", "neither afconvert nor ffmpeg is installed")

    got, by = speech.run("stt", "zh-CN", {"wav": take_wav}, live=live, cfg=cfg)
    req = seen[-1]
    check("azure hears first: the short-audio endpoint, WAV PCM 16 kHz, detailed",
          by == "azure" and "language=zh-CN" in req["path"]
          and "format=detailed" in req["path"]
          and req["headers"].get("Content-Type")
          == "audio/wav; codecs=audio/pcm; samplerate=16000"
          and req["body"] == TAKE and "Pronunciation-Assessment" not in req["headers"])
    check("and its words come back with their timings",
          got["text"] == "你好。" and got["words"][0]["text"] == "你好"
          and abs(got["words"][0]["start"] - 0.12) < 1e-6
          and abs(got["words"][0]["end"] - 0.72) < 1e-6, got)

    got, by = speech.run("assess", "zh-CN", {"wav": take_wav, "ref": "你好",
                                             "pinyin": "ni3 hao3", "heard": "你好"},
                         live=live, cfg=cfg)
    pa = seen[-1].get("pa") or {}
    check("assessment sends the base64 Pronunciation-Assessment header",
          pa == {"ReferenceText": "你好", "GradingSystem": "HundredMark",
                 "Granularity": "Phoneme", "Dimension": "Comprehensive",
                 "EnableMiscue": True}, pa)
    check("and reads back a score, a word diff and per-syllable confidence",
          by == "azure" and got["score"] == 82.5
          and [w["op"] for w in got["words"]] == ["equal", "wrong"]
          and got["syllables"][0]["heard"] == "T2"
          and got["syllables"][1]["heard"] == "unknown"
          and got["syllables"][1]["confidence"] == 0.4
          and "好" in got["verdict"], got)

    behave["azure_stt"] = 429
    got, by = speech.run("stt", "zh-CN", {"wav": take_wav}, live=live, cfg=cfg)
    req = seen[-1]
    check("a 429 passes the job on, to openai's transcriptions",
          by == "openai" and got["text"] == "你好"
          and req["headers"].get("Authorization") == "Bearer oa-key")
    check("with the multipart built by hand: model, language and the WAV whole",
          req.get("fields") == {"model": "gpt-4o-mini-transcribe", "language": "zh",
                                "response_format": "json"}
          and req.get("file") == TAKE and req.get("filename") == "take.wav",
          req.get("fields"))
    check("and marks azure limited, so the next job does not ask it",
          speech.chain("stt", "zh-CN", cfg) == ["openai", "local"])
    behave["azure_stt"] = 200
    clear_marks()
    n = len(seen)
    unreach = speech.load({"recipes": dict(HOSTED, azure={
        "stt": {"endpoint": dead + "/stt/{region}"}})})
    got, by = speech.run("stt", "zh-CN", {"wav": take_wav}, live=live, cfg=unreach)
    check("an unreachable host is stood down and the next recipe answers",
          by == "openai" and speech.chain("stt", "zh-CN", unreach)[0] == "openai")
    clear_marks()
    costs = [json.loads(l) for l in open(os.path.join(live, "cost.jsonl"))]
    check("every job that answered wrote exactly one cost line",
          len(costs) == (6 if CONVERTS else 4)
          and all(c["requests"] == 1 and c["tokens"] == 0 for c in costs), costs)
    body, ctype = speech.multipart_body([("a", "1")], [("f", "x.wav", "audio/wav", b"RIFF")])
    check("the hand-built multipart ends with its closing boundary",
          body.endswith(("--%s--\r\n" % ctype.split("boundary=")[1]).encode()))

    from tutorboard.agents import usage
    out = io.StringIO()
    with open(os.path.join(live, "cost.jsonl"), "a") as fh:
        fh.write(json.dumps({"turn": 1, "agent": "claude", "tokens": 1000,
                             "requests": 2, "usd": 0.5}) + "\n")
    with contextlib.redirect_stdout(out):
        usage.cost_report({}, {"dir": "live", "root": live})
    check("`board cost` counts a speech job apart from the turns",
          "1 turn(s)" in out.getvalue() and "speech:" in out.getvalue(), out.getvalue())

    # whisper-cli under -ml 1 cuts a segment per token, and a Chinese
    # character of two tokens ends one segment halfway through its UTF-8.
    ni = "你".encode("utf-8")
    raw = (b'{"transcription": ['
           b'{"offsets": {"from": 100, "to": 200}, "text": "' + ni[:2] + b'"},'
           b'{"offsets": {"from": 200, "to": 300}, "text": "' + ni[2:] + b'"},'
           b'{"offsets": {"from": 300, "to": 330}, "text": "\xef\xbc\x8c"},'
           b'{"offsets": {"from": 330, "to": 600}, "text": "' + "好".encode() + b'"}]}')
    split_says = os.path.join(box, "whisper-split.json")
    with open(split_says, "w") as fh:
        json.dump({"raw_hex": raw.hex()}, fh)
    os.environ["WHISPER_SAYS"] = split_says
    got, by = speech.run("stt", "zh-CN", {"wav": take_wav},
                         cfg=speech.load({"order": {"stt": ["local"]},
                                          "recipes": {"local": LOCAL}}))
    check("a character whisper cut in two is joined whole, never U+FFFD",
          by == "local" and got["text"] == "你，好" and "\ufffd" not in got["text"], got)
    check("with the first half's start and the second's end, and punctuation "
          "no word",
          [(w["text"], w["start"], w["end"]) for w in got["words"]]
          == [("你", 0.1, 0.3), ("好", 0.33, 0.6)], got["words"])
    check("so whisper's timings still count out to the syllables past a comma",
          tones.from_words([{"text": "你", "start": 0.1, "end": 0.3},
                            {"text": "，", "start": 0.3, "end": 0.33},
                            {"text": "好", "start": 0.33, "end": 0.6}], 2)
          == [[10, 30], [33, 60]])
    os.environ.pop("WHISPER_SAYS", None)

    # =======================================================================
    # 3. THE TONE CHECK
    # =======================================================================
    for order in (["T1", "T2", "T3", "T4"], ["T4", "T3", "T2", "T1"],
                  ["T3", "T1", "T4", "T2"]):
        samples, spans = phrase(order)
        path = os.path.join(box, "sweep.wav")
        wav(path, samples)
        pin = " ".join("ma%s" % t[1] for t in order)
        got = tones.assess(path, "妈麻马骂", "zh-CN", pinyin=pin)
        heard = [s["heard"] for s in got["syllables"]]
        check("sine sweeps %s are heard as %s" % (" ".join(order), " ".join(heard)),
              heard == order and got["segmented_by"] == "voiced runs", got["verdict"])
    words = [{"text": "妈", "start": a, "end": b} for a, b in spans]
    got = tones.assess(path, "妈麻马骂", "zh-CN", pinyin=pin, words=words)
    check("whisper's timings, when they count out, place the syllables",
          got["segmented_by"] == "whisper timings"
          and [s["heard"] for s in got["syllables"]] == order)
    check("each syllable has its target, expected and heard tone and a confidence",
          all(set(("syllable", "target", "expect", "heard", "confidence", "start",
                   "end")) <= set(s) for s in got["syllables"])
          and got["syllables"][0]["syllable"] == "妈")
    check("every result says it is a prototype",
          got["prototype"] is True and "prototype" in got["verdict"])

    # Four syllables, two of them broken by a dropout: six runs, merged to four.
    samples = silence()
    for name in ("T1", "T4", "T2", "T1"):
        one = syllable(CONTOURS[name], 0.3)
        if name in ("T4", "T2"):
            cut = len(one) // 2
            one = one[:cut] + silence(0.06) + one[cut:]
        samples += one + silence()
    path = os.path.join(box, "broken.wav")
    wav(path, samples)
    got = tones.assess(path, "妈骂麻妈", "zh-CN", pinyin="ma1 ma4 ma2 ma1")
    check("six voiced runs for four syllables are merged to four (%d runs)"
          % got["voiced_runs"],
          got["voiced_runs"] == 6 and len(got["syllables"]) == 4
          and [s["heard"] for s in got["syllables"]] == ["T1", "T4", "T2", "T1"],
          [s["heard"] for s in got["syllables"]])

    path = os.path.join(box, "quiet.wav")
    wav(path, silence(1.0))
    got = tones.assess(path, "你好", "zh-CN", pinyin="ni3 hao3")
    check("silence is unknown, never a tone, and never wrong",
          [s["heard"] for s in got["syllables"]] == ["unknown", "unknown"]
          and "tone off" not in got["verdict"], got["verdict"])

    aims = tones.targets("ni3 hao3")
    check("pinyin: the written tone, and third-tone sandhi in what is expected",
          [(a["syllable"], a["target"], a["expect"]) for a in aims]
          == [("ni", "T3", "T2"), ("hao", "T3", "T3")])
    aims = tones.targets("nǐ hǎo ma")
    check("tone marks read as tones, an untoned syllable as neutral",
          [a["target"] for a in aims] == ["T3", "T3", "neutral"]
          and aims[0]["syllable"] == "ni")
    check("不 before a fourth tone is expected second",
          [a["expect"] for a in tones.targets("bu4 shi4")] == ["T2", "T4"])
    samples, _spans = phrase(["T2", "T3"])
    path = os.path.join(box, "nihao.wav")
    wav(path, samples)
    got = tones.assess(path, "你好", "zh-CN", pinyin="ni3 hao3")
    check("so ni3 hao3 said as T2 T3 is every tone right",
          [s["heard"] for s in got["syllables"]] == ["T2", "T3"]
          and got["verdict"].startswith("every tone right"), got["verdict"])
    samples, _spans = phrase(["T4", "T3"])
    wav(path, samples)
    got = tones.assess(path, "你好", "zh-CN", pinyin="ni3 hao3")
    check("and said as T4 T3 names the syllable off",
          "你 (heard T4, wanted T2)" in got["verdict"] and got["score"] == 50,
          got["verdict"])

    same = tones.contour(path)
    other_path = os.path.join(box, "other.wav")
    wav(other_path, phrase(["T1", "T1"])[0])
    near, far = tones.dtw(same, same), tones.dtw(same, tones.contour(other_path))
    check("DTW against the reference: the same contour is ~0, another is not",
          near is not None and near < 0.05 and far > 1.0, (near, far))
    got = tones.assess(path, "你好", "zh-CN", pinyin="ni3 hao3", reference=other_path)
    check("and the result carries the distance",
          got["contour"] and got["contour"]["dtw"] > 1.0)

    diff = tones.word_diff("我是学生", "我是老师生", "zh-CN")
    check("the word diff marks what was said wrong, missing or extra",
          [(d["op"], d["target"], d["heard"]) for d in diff]
          == [("equal", "我", "我"), ("equal", "是", "是"), ("wrong", "学", "老"),
              ("extra", "", "师"), ("equal", "生", "生")], diff)
    got = tones.assess(take_wav, "Bonjour madame", "fr-FR", heard="bonjour monsieur")
    check("another language gets the word diff and no tones",
          got["syllables"] == [] and "monsieur" in got["verdict"]
          and got["tones"].startswith("only Mandarin"))

    # =======================================================================
    # 4. THE SUBJECT'S SPEECH, AND WHAT A TURN IS TOLD
    # =======================================================================
    os.makedirs(os.path.join(atlas, "courses", "Mandarin"))
    os.makedirs(os.path.join(atlas, "courses", "Algebra"))
    os.makedirs(os.path.join(atlas, "board"))
    with open(os.path.join(atlas, "courses", "Mandarin", "tutorboard.json"), "w") as fh:
        json.dump({"name": "Mandarin", "speech": {"lang": "zh_CN", "voice": "Tingting"}}, fh)
    with open(os.path.join(atlas, ".gitignore"), "w") as fh:
        fh.write("/sessions/\n")
    subprocess.run(["git", "init", "-q", atlas], check=True)
    said = config.read_config(os.path.join(atlas, "courses", "Mandarin"))["speech"]
    check("read_config keeps a subject's speech, with its defaults",
          said == {"lang": "zh-CN", "native": "en-US", "voice": "Tingting", "auto": True},
          said)
    check("and drops one that names no language",
          config.clean_speech({"voice": "x"}) is None
          and config.read_config(os.path.join(atlas, "courses", "Algebra"))["speech"] is None)

    sid = sessions.new("drill", base=atlas)["id"]
    sessions.bind(sid, "courses/Mandarin", base=atlas)
    math_sid = sessions.new("algebra", base=atlas)["id"]
    sessions.bind(math_sid, "courses/Algebra", base=atlas)
    where = sessions.path(sid, atlas)
    math_where = sessions.path(math_sid, atlas)
    repo = course_repo.Repo(course_repo.stored_root(where), session=where, create=False)
    math_repo = course_repo.Repo(course_repo.stored_root(math_where), session=math_where,
                                 create=False)
    check("SPEECH_SENSE is in a turn of a subject with speech",
          sense.SPEECH_SENSE in sense.session_sense(repo))
    check("and not in one without it, until the session holds a heard take",
          sense.SPEECH_SENSE not in sense.session_sense(math_repo))
    os.makedirs(os.path.join(math_where, "speech"))
    with open(os.path.join(math_where, "speech", "t0001-r1.heard.json"), "w") as fh:
        fh.write("{}")
    check("then it is",
          sense.SPEECH_SENSE in sense.session_sense(math_repo))
    check("SPEECH_SENSE names `board hear`, and that is a command",
          "board hear" in sense.SPEECH_SENSE)

    # =======================================================================
    # 5. CARDS: a `say` fence
    # =======================================================================
    jobs = []
    body = ("Say this:\n\n```say zh-CN pinyin=\"ni3 hao3\"\n你好\n```\n\n"
            "```python\nprint(1)\n```\n")
    out = cards.extract_tikz(body, jobs, repo)
    name = synth.sha("zh-CN", "你好", "ni3 hao3", "Tingting")
    check("a say fence becomes a placeholder with the phrase after it",
          ("@@SAY:%s:pending:zh-CN:ni3%%20hao3@@ 你好\n" % name) in out
          and "```python" in out, out)
    check("and one job for the compiler thread, in the subject's voice",
          len(jobs) == 1 and jobs[0][0] == name and jobs[0][1] == "say"
          and json.loads(jobs[0][2])["voice"] == "Tingting"
          and json.loads(jobs[0][2])["live"] == repo.live, jobs)
    out = cards.extract_tikz("```say zh-CN\n谢谢 (thank you)\n```\n", [], repo)
    check("a phrase without pinyin keeps its own parentheses as words",
          "zh-CN@@ 谢谢 (thank you)\n" in out, out)
    os.makedirs(paths.SPEECH, exist_ok=True)
    with open(os.path.join(paths.SPEECH, name + ".m4a"), "wb") as fh:
        fh.write(b"cached")
    jobs = []
    out = cards.extract_tikz(body, jobs, repo)
    check("a cached phrase is ready and queues nothing",
          ("@@SAY:%s:ready:zh-CN:" % name) in out and not jobs)
    write_config({"order": {"tts": ["local"], "stt": ["local"], "assess": ["local"]},
                  "recipes": {"local": LOCAL}})
    synth.make(paths.SPEECH, "f" * 32, synth.job("en-US", "hello")[1])
    check("the compiler's say job makes the phrase through the TTS chain",
          open(os.path.join(paths.SPEECH, "f" * 32 + ".m4a"), "rb").read() == b"fake m4a")
    synth.make(paths.SPEECH, "e" * 32, synth.job("ga-IE", "Dia duit")[1])
    check("and one nobody can make leaves .err saying why",
          synth.status("e" * 32) == "error"
          and "espeak" in open(os.path.join(paths.SPEECH, "e" * 32 + ".err")).read())

    spoken = speaking.speakable(
        "# Groups\n\nA group $G$ is **closed**: see $$ab \\in G$$ and \\(x\\).\n\n"
        "```python\nx = 1\n```\n\n```say zh-CN\n你好\n```\n\nUse `foo` [here](http://x).")
    check("a card read aloud skips math, code and say phrases",
          "$" not in spoken and "x = 1" not in spoken and "你好" not in spoken
          and "foo" not in spoken and "Groups" in spoken and "closed" in spoken
          and "here" in spoken and "http" not in spoken, spoken)

    # =======================================================================
    # 6. THE ROUTE, end to end, STT stubbed by the fake whisper-cli
    # =======================================================================
    from tutorboard.server import app
    httpd = app.make_server(atlas, 0, start=False)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    PORT = httpd.server_port
    says = os.path.join(box, "whisper-says.json")
    samples, spans = phrase(["T2", "T3"])
    with open(says, "w") as fh:
        json.dump({"transcription": [
            {"text": "你", "offsets": {"from": int(spans[0][0] * 1000),
                                      "to": int(spans[0][1] * 1000)}},
            {"text": "好", "offsets": {"from": int(spans[1][0] * 1000),
                                      "to": int(spans[1][1] * 1000)}}]}, fh)
    os.environ["WHISPER_SAYS"] = says
    wav(take_wav, samples)
    with open(take_wav, "rb") as fh:
        TAKE = fh.read()

    def post_take(sid, audio_bytes, fields, filename="take.wav", ctype="audio/wav"):
        body, content = speech.multipart_body(
            sorted(fields.items()), [("audio", filename, ctype, audio_bytes)])
        conn = http.client.HTTPConnection("127.0.0.1", PORT, timeout=120)
        conn.request("POST", "/s/%s/speech/say" % sid, body=body,
                     headers={"Content-Type": content})
        r = conn.getresponse()
        raw = r.read()
        conn.close()
        try:
            return r.status, json.loads(raw.decode("utf-8"))
        except ValueError:
            return r.status, {"raw": raw[:200]}

    def get(path):
        conn = http.client.HTTPConnection("127.0.0.1", PORT, timeout=60)
        conn.request("GET", path)
        r = conn.getresponse()
        raw = r.read()
        conn.close()
        return r.status, raw

    def post_json(path, payload):
        conn = http.client.HTTPConnection("127.0.0.1", PORT, timeout=60)
        conn.request("POST", path, body=json.dumps(payload),
                     headers={"Content-Type": "application/json"})
        r = conn.getresponse()
        raw = r.read()
        conn.close()
        return r.status, json.loads(raw.decode("utf-8"))

    with open(os.path.join(repo.cards, "0003-ask.md"), "w") as fh:
        fh.write("---\nkind: question\n---\nSay 你好 back to me. $x^2$\n")
    status, got = post_take(sid, TAKE, {"lang": "zh-CN", "ref": "你好",
                                        "pinyin": "ni3 hao3", "answers": "0003"})
    rec = got.get("heard") or {}
    check("POST /s/<id>/speech/say hears the take: 200, the words, by local",
          status == 200 and got.get("ok") and rec.get("heard") == "你好"
          and rec.get("stt_by") == "local" and rec.get("assess_by") == "local",
          (status, got))
    base = rec.get("base") or ""
    folder = os.path.join(where, "speech")
    check("a take is named by when it arrived, not by a turn id taken before "
          "it was heard", base.startswith("take-") and got.get("turn") not in base,
          base)
    check("the take as sent, its 16 kHz WAV and its heard record are under the "
          "session's speech/",
          sorted(os.listdir(folder)) == sorted([base + ".orig.wav", base + ".wav",
                                                base + ".heard.json"])
          and rec.get("audio") == base + ".orig.wav"
          and open(os.path.join(folder, base + ".orig.wav"), "rb").read() == TAKE,
          os.listdir(folder))
    heard = json.load(open(os.path.join(folder, base + ".heard.json")))
    check("the heard record judges each syllable against the pinyin",
          [s["heard"] for s in heard["assess"]["syllables"]] == ["T2", "T3"]
          and heard["assess"]["segmented_by"] == "whisper timings"
          and heard["assess"]["prototype"] is True, heard.get("assess"))
    turns_rec = [json.loads(l) for l in open(os.path.join(where, "turns.jsonl"))]
    t = turns_rec[-1]
    check("a turn record of kind speech, answering the card, with its tones",
          t["kind"] == "speech" and t["answers"] == "0003" and t["text"] == "你好"
          and t["target"] == "你好" and len(t["tones"]) == 2 and not t["read"], t)
    msgs = inbox.unread(repo)
    m = msgs[-1]
    check("and a waking [speech] line: heard, target, verdict",
          m["text"].startswith("[speech] heard: '你好'. Target: '你好'. every tone right")
          and inbox.wakes(m), m.get("text"))
    shown = inbox.render([m], repo)
    check("whose file: is the heard record, and the tutor never gets the audio",
          ("file: %s" % os.path.join(folder, base + ".heard.json")) in shown
          and ".wav" not in shown and ".m4a" not in shown, shown)
    size = os.path.getsize(repo.messages_path)
    raw_last = open(repo.messages_path, "rb").read().splitlines()[-1]
    _text, taken = inbox.take(repo)
    check("the [speech] line is written ASCII, so a turn marks it read in "
          "place and never rewrites the inbox",
          all(b < 128 for b in raw_last) and any(t.get("kind") == "speech" for t in taken)
          and os.path.getsize(repo.messages_path) == size,
          (raw_last[:80], size, os.path.getsize(repo.messages_path)))
    costs = [json.loads(l) for l in open(os.path.join(where, "cost.jsonl"))]
    check("the session's cost.jsonl has the STT and the assessment",
          [c["speech"] for c in costs] == ["stt", "assess"], costs)
    status, raw = get("/s/%s/speech/last.json" % sid)
    check("GET /speech/last.json gives the newest heard record back",
          status == 200 and json.loads(raw)["heard"]["base"] == base)

    for ext, tool, argv in ((".m4a", "afconvert", ["afconvert", take_wav, "-o", "{out}",
                                                   "-f", "m4af", "-d", "aac"]),
                            (".webm", "ffmpeg", ["ffmpeg", "-nostdin", "-loglevel",
                                                 "error", "-y", "-i", take_wav,
                                                 "-c:a", "libopus", "{out}"])):
        if not shutil.which(tool):
            skip("a %s take" % ext, "%s is not installed here" % tool)
            continue
        made = os.path.join(box, "take" + ext)
        subprocess.run([a.replace("{out}", made) for a in argv], check=True)
        with open(made, "rb") as fh:
            data = fh.read()
        status, got = post_take(sid, data, {"lang": "zh-CN", "ref": "你好",
                                            "pinyin": "ni3 hao3"},
                                filename="take" + ext,
                                ctype="audio/mp4" if ext == ".m4a"
                                else "audio/webm;codecs=opus")
        b2 = (got.get("heard") or {}).get("base") or ""
        check("a %s take is converted by %s to 16 kHz mono and heard" % (ext, tool),
              status == 200 and got["heard"]["heard"] == "你好"
              and audio.wav_shape(os.path.join(folder, b2 + ".wav"))[:3] == (R, 1, 16)
              and os.path.isfile(os.path.join(folder, b2 + ext)), got)

    # Two takes heard at once, and a typed answer landing while they are
    # heard: three turns, three ids, and neither take's files overwritten.
    from tutorboard.lesson import turns as lesson_turns
    os.environ["WHISPER_SLEEP"] = "1.5"
    answers = {}

    def one_take(k):
        answers[k] = post_take(sid, TAKE, {"lang": "zh-CN", "ref": "你好",
                                           "pinyin": "ni3 hao3"})
    racing = [threading.Thread(target=one_take, args=(k,)) for k in (0, 1)]
    for th in racing:
        th.start()
    time.sleep(0.6)
    typed = lesson_turns.next_turn_id(repo)
    lesson_turns.write_turn(repo, {"id": typed, "rev": 1, "kind": "text",
                                   "from": "student", "text": "typed meanwhile",
                                   "t": time.time(), "read": False})
    for th in racing:
        th.join()
    os.environ["WHISPER_SLEEP"] = "0"
    ids = [typed] + [answers[k][1].get("turn") for k in (0, 1)]
    bases = [answers[k][1].get("heard", {}).get("base") for k in (0, 1)]
    check("two takes heard at once and a typed answer meanwhile get three turn ids",
          all(answers[k][0] == 200 for k in (0, 1)) and len(set(ids)) == 3, ids)
    check("and each take keeps its own recording and heard record",
          len(set(bases)) == 2 and all(
              os.path.isfile(os.path.join(folder, b + ".heard.json")) for b in bases),
          bases)

    status, got = post_take(sid, TAKE, {"ref": "你好", "pinyin": "ni3 hao3"})
    check("with no lang, the subject's speech.lang is used",
          status == 200 and got["heard"]["lang"] == "zh-CN", got)
    status, got = post_take(math_sid, TAKE, {"ref": "你好"})
    check("and a subject without one is asked to say which",
          status == 400 and "language" in got.get("error", ""), got)
    status, got = post_take(sid, b"", {"lang": "zh-CN"})
    check("an empty take is refused", status == 400, got)
    status, got = post_take(sid, b"not audio at all", {"lang": "zh-CN"},
                            filename="take.m4a", ctype="audio/mp4")
    check("audio nothing can read is 502, in words",
          status == 502 and "not heard" in got.get("error", ""), got)

    ended = sessions.new("ended", base=atlas)["id"]
    sessions.end(ended, base=atlas)
    status, got = post_take(ended, TAKE, {"lang": "zh-CN"})
    check("an ended session refuses a take (ENDED_REFUSES)",
          status == 409 and "/speech/say" in handler.ENDED_REFUSES)

    phrase_name = name
    status, raw = get("/speech/%s.m4a" % phrase_name)
    check("GET /speech/<sha>.m4a serves a cached phrase, unprefixed",
          status == 200 and raw == b"cached")
    status, raw = get("/s/%s/speech/%s.m4a" % (sid, phrase_name))
    check("and under a session", status == 200 and raw == b"cached")
    bad = [get(p)[0] for p in ("/speech/%s.M4A" % phrase_name,
                               "/speech/../config.json",
                               "/speech/%s.m4a" % phrase_name[:20],
                               "/speech/%s.m4a" % ("0" * 32),
                               "/speech/last.json")]
    check("only a strict sha name is served: %s" % bad, all(b == 404 for b in bad))

    with open(os.path.join(repo.cards, "0004-lesson.md"), "w") as fh:
        fh.write("---\nkind: lesson\n---\nA tone **rises** when $f' > 0$.\n\n"
                 "```python\nx = 1\n```\n")
    open(os.path.join(box, "say-voices.log"), "w").close()
    status, got = post_json("/s/%s/speech/card" % sid, {"card": "0004"})
    check("POST /speech/card speaks a card's prose in the native language",
          status == 200 and got["lang"] == "en-US" and got["url"]
          == "/speech/%s.m4a" % got["sha"]
          and get(got["url"])[1] == b"fake m4a", got)
    check("in a speaker's voice, never a novelty one",
          open(os.path.join(box, "say-voices.log")).read().split() == ["Samantha"])
    status, got = post_json("/s/%s/speech/card" % sid, {"card": "../x"})
    check("and refuses a card id that is not one", status == 400)
    httpd.shutdown()

    # =======================================================================
    # 7. `board hear`, the audit, the multipart fields
    # =======================================================================
    loader = importlib.machinery.SourceFileLoader("boardcli", os.path.join(ROOT, "bin", "board"))
    spec = importlib.util.spec_from_loader("boardcli", loader)
    board = importlib.util.module_from_spec(spec)
    loader.exec_module(board)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = board.main(["hear", os.path.join(folder, base + ".heard.json")])
    check("`board hear <file>` prints what was heard and each syllable's tone",
          code == 0 and "heard:   你好" in out.getvalue()
          and "你 T2->T2" in out.getvalue() and "prototype" in out.getvalue(),
          out.getvalue())
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = board.main(["hear", take_wav, "--lang", "zh-CN", "--ref", "你好",
                           "--pinyin", "ni3 hao3", "--json"])
    said = json.loads(out.getvalue()) if code == 0 else {}
    check("and an audio file is heard first, in a scratch copy",
          code == 0 and said.get("heard") == "你好"
          and not os.path.exists(os.path.splitext(take_wav)[0] + ".heard.json"))
    check("board hear is a command, documented in `board help`",
          "hear" in board.COMMANDS and "board hear <file>" in (board.__doc__ or ""))

    for rel in ("sessions/x/speech/t0001-r1.webm", "courses/M/take.ogg",
                "courses/M/take.m4a", "courses/M/take.wav"):
        check("the audit refuses audio: %s" % rel,
              any("audio" in p for p in audit.problems(rel)))

    fields = {}
    body, ctype = speech.multipart_body([("ref", "你好"), ("lang", "zh-CN")],
                                        [("audio", "a.wav", "audio/wav", b"RIFFxx")])
    folder2 = tempfile.mkdtemp(dir=box)
    types = []
    got = multipart.save_parts(io.BytesIO(body), len(body),
                               ctype.split("boundary=")[1].encode(), folder2,
                               lambda i, f: os.path.join(folder2, "x" + f),
                               fields=fields, types=types)
    check("the board's multipart reader keeps plain fields when asked",
          fields == {"ref": "你好", "lang": "zh-CN"} and types == ["audio/wav"]
          and open(got[0][1], "rb").read() == b"RIFFxx")

    # =======================================================================
    # 8. SETUP
    # =======================================================================
    brew = open(os.path.join(ATLAS_ROOT, "Brewfile")).read()
    check("the Brewfile has whisper-cpp, ffmpeg and espeak-ng",
          all('brew "%s"' % b in brew for b in ("whisper-cpp", "ffmpeg", "espeak-ng")))
    script = os.path.join(ATLAS_ROOT, "scripts", "speech-model.sh")
    text = open(script).read()
    import re
    pin = re.search(r'SHA256="\$\{SPEECH_MODEL_SHA256:-([0-9a-f]+)\}"', text)
    check("speech-model.sh pins one model by SHA-256",
          pin and len(pin.group(1)) == 64 and "ggml-small-q5_1.bin" in text)
    check("setup-mac.sh runs it",
          "scripts/speech-model.sh" in open(os.path.join(ATLAS_ROOT, "scripts",
                                                         "setup-mac.sh")).read())
    home = os.path.join(box, "home")
    os.makedirs(home)
    calls = os.path.join(box, "fetch.log")
    fetch = os.path.join(bin_dir, "fake-fetch")
    with open(fetch, "w") as fh:
        fh.write("#!/bin/sh\necho \"$1\" >> %r\nprintf 'model bytes' > \"$2\"\n" % calls)
    os.chmod(fetch, 0o755)
    import hashlib
    good_sum = hashlib.sha256(b"model bytes").hexdigest()
    env = dict(os.environ, HOME=home, SPEECH_MODEL_FETCH=fetch,
               SPEECH_MODEL_SHA256=good_sum, SPEECH_MODEL_URL="https://example.invalid/m")
    env.pop("TUTORBOARD_MODELS", None)
    first = subprocess.run(["bash", script], env=env, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, universal_newlines=True)
    model = os.path.join(home, ".local", "share", "tutor-board", "models",
                         "ggml-small-q5_1.bin")
    check("a first run downloads the model into ~/.local/share/tutor-board/models/",
          first.returncode == 0 and open(model, "rb").read() == b"model bytes",
          first.stdout)
    second = subprocess.run(["bash", script], env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, universal_newlines=True)
    check("and a second run changes nothing and fetches nothing",
          second.returncode == 0 and "unchanged" in second.stdout
          and len(open(calls).read().split()) == 1, second.stdout)
    os.remove(model)
    env["SPEECH_MODEL_SHA256"] = "0" * 64
    bad = subprocess.run(["bash", script], env=env, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, universal_newlines=True)
    check("a download whose checksum is wrong is deleted, not kept",
          bad.returncode == 1 and not os.path.exists(model)
          and not os.path.exists(model + ".part") and "SHA-256" in bad.stdout,
          bad.stdout)

    # =======================================================================
    # 9. DOCTOR, and the real binaries when they are here
    # =======================================================================
    from tutorboard.speech import witness
    lines = []
    ok = witness.report(dry=True, cfg=speech.load({"recipes": {"local": LOCAL}}),
                        out=lines.append)
    joined = "\n".join(lines)
    check("doctor --dry names the chains and the local TTS, STT and assessment",
          ok and "speech tts" in joined and "local tts:" in joined
          and "local stt:" in joined and "local assess:" in joined, joined)
    lines = []
    with open(says, "w") as fh:
        json.dump({"transcription": [{"text": " Wrong", "offsets": {}}]}, fh)
    ok = witness.report(dry=False, cfg=speech.load(
        {"order": {"tts": ["local"], "stt": ["local"]}, "recipes": {"local": LOCAL}}),
        out=lines.append)
    check("and spent, a word that does not come back fails the witness",
          not ok and "FAIL speech" in lines[-1], lines[-1:])

    real = speech.load({})
    paths.MODELS = os.path.join(os.path.expanduser("~"), ".local", "share",
                                "tutor-board", "models")
    if (shutil.which("whisper-cli") and speech.model_path(real["recipes"]["local"])
            and shutil.which("say") and CONVERTS):
        ok, line = witness.witness(speech.load({"order": {
            "tts": ["local"], "stt": ["local"]}}))
        check("the real say and whisper-cli: one word spoken and heard back", ok, line)
    else:
        print()
        print("SKIPPED THE REAL-BINARY WITNESS: this Mac lacks %s, so `say` speaking "
              "a word and whisper-cli hearing it back was NOT exercised here."
              % ", ".join(n for n, have in (
                  ("whisper-cli", shutil.which("whisper-cli")),
                  ("a whisper model in ~/.local/share/tutor-board/models",
                   speech.model_path(real["recipes"]["local"])),
                  ("say", shutil.which("say")),
                  ("afconvert or ffmpeg", CONVERTS)) if not have))
        print()
finally:
    shutil.rmtree(box, ignore_errors=True)

if fails:
    print("\n%d failed: %s" % (len(fails), "; ".join(fails)))
    sys.exit(1)
print("\nevery tutor speaks, listens and judges pronunciation")
