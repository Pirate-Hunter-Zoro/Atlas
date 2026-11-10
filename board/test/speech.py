#!/usr/bin/env python3
"""Speech: every tutor speaks and listens.

    python3 test/speech.py

Nothing here needs a network, a key or a speech binary. A local http.server
stands in for Azure; a script stands in for whisper-cli and another for
`say`; every WAV is synthesised at run time with the standard library.

  - THE TABLE: azure and local, in that order for `tts` and `stt`; the
    config's `speech` block is laid over it; `chain` passes over a recipe
    that is unkeyed, missing its command, limited, stood down or without the
    language, and always ends with local. There is no pronunciation grade.
  - THE HOSTED RECIPES, against the stand-in: Azure's SSML and its
    short-audio STT. A refusal passes the job on to this Mac; a 429 marks the
    recipe limited and an unreachable host stands it down. Each job writes one
    cost line.
  - THE SUBJECT: `speech.lang` is the default language, and `SPEECH_SENSE`
    tells a turn that the session speaks and listens.
  - THE ROUTE, end to end with STT stubbed: a take saved under the session's
    speech/, heard, a turn record and a waking `[speech]` line whose `file:`
    is the heard record and never the audio; an ended session 409; phrases
    served by a strict sha name; a card read without its math.
  - THE CARDS: a `say` fence becomes a placeholder and a job for the cache.
  - SETUP: the model download is checksummed and a second run fetches nothing.
  - THE REAL BINARIES, when this Mac has them: one word spoken and heard back.
    Absent, that witness is SKIPPED, loudly.
"""

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
from tutorboard.speech import audio, synth                    # noqa: E402

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
def tone(dur=0.4, freq=220.0, amp=0.5):
    """A steady voiced tone: enough for a converter and a fake whisper."""
    n = int(dur * R)
    return [amp * math.sin(2 * math.pi * freq * i / R) for i in range(n)]


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
    check("the table holds azure and local",
          set(D["recipes"]) == {"azure", "local"})
    check("two jobs, tts and stt, and no pronunciation grade",
          speech.KINDS == ("tts", "stt") and not hasattr(speech, "_azure_assess"))
    check("and tries them in that order for every kind",
          all(D["order"][k] == ["azure", "local"] for k in speech.KINDS))
    az = D["recipes"]["azure"]
    check("azure takes AZURE_SPEECH_KEY and AZURE_SPEECH_REGION",
          az["needs_key"] == "AZURE_SPEECH_KEY"
          and az["region_key"] == "AZURE_SPEECH_REGION")
    check("azure has no assessment endpoint or price",
          "assess" not in az and "assess_per_minute" not in az.get("prices", {}))
    check("and no OpenAI recipe or driver is left",
          not any(n.startswith("_openai") for n in dir(speech))
          and not any(v == "openai" for v, _k in speech.DRIVERS))
    lo = D["recipes"]["local"]
    check("local is say (espeak-ng after it) and whisper-cli",
          lo["tts"]["cmd"] == ["say"] and lo["tts"]["fallback_cmd"] == ["espeak-ng"]
          and lo["stt"]["cmd"] == ["whisper-cli"]
          and "assess" not in lo and not lo.get("needs_key"))

    cfg = speech.load({"order": {"tts": ["spare", "azure"]},
                       "recipes": {"azure": {"voices": {"zh-CN": "zh-CN-YunxiNeural"}},
                                   "spare": {"via": "azure", "needs_key": "X",
                                             "tts": {"endpoint": "http://x"}}}})
    check("the config's speech block is laid over the table: order per kind",
          cfg["order"]["tts"] == ["spare", "azure"]
          and cfg["order"]["stt"] == ["azure", "local"])
    check("a recipe merges one level deeper, keeping what it does not name",
          cfg["recipes"]["azure"]["voices"]["zh-CN"] == "zh-CN-YunxiNeural"
          and cfg["recipes"]["azure"]["voices"]["ja-JP"] == "ja-JP-NanamiNeural"
          and cfg["recipes"]["azure"]["needs_key"] == "AZURE_SPEECH_KEY"
          and cfg["recipes"]["azure"]["tts"]["format"] == "riff-24khz-16bit-mono-pcm")
    check("a new recipe is added and null removes one",
          "spare" in cfg["recipes"]
          and "azure" not in speech.load({"recipes": {"azure": None}})["recipes"])
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
              and speech.unavailable({"recipes": {"local": kept}}, "local", "tts",
                                     "zh-CN") is None, kept)
    check("the defaults themselves are never changed by a load",
          "azure" in speech.DEFAULT_SPEECH["recipes"])
    try:
        speech.run("assess", "zh-CN", {"wav": "/nowhere.wav"}, cfg=cfg)
        raised = False
    except ValueError as exc:
        raised = "tts" in str(exc) and "stt" in str(exc)
    check("and asking for a pronunciation grade is refused", raised)

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
    check("unkeyed, azure is passed over and local is the chain",
          speech.chain("tts", "zh-CN", cfg) == ["local"]
          and speech.chain("stt", "zh-CN", cfg) == ["local"])
    why = dict(speech.explain("stt", "zh-CN", cfg))
    check("and azure is named with the key it lacks",
          "AZURE_SPEECH_KEY" in why["azure"])
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
          "azure:" in said and "local:" in said, said)
    check("Irish has no local voice without espeak-ng, and says so",
          "espeak-ng" in (dict(speech.explain("tts", "ga-IE", cfg))["local"] or ""))

    write_keys(AZURE_SPEECH_KEY="az-key", AZURE_SPEECH_REGION="westeurope")
    full = speech.load({"recipes": {"local": LOCAL}})
    check("keyed, the chain is azure, then this Mac",
          speech.chain("tts", "zh-CN", full) == ["azure", "local"]
          and speech.chain("stt", "zh-CN", full) == ["azure", "local"])
    check("and no Azure voice for Swahili",
          "azure" not in speech.chain("tts", "sw-KE", full))
    swapped = speech.load({"order": {"tts": ["local", "azure"]},
                           "recipes": {"local": LOCAL}})
    check("local is last whatever order the config gives",
          speech.chain("tts", "zh-CN", swapped) == ["azure", "local"])
    only = speech.load({"order": {"stt": ["local"]}, "recipes": {"local": LOCAL}})
    check("and a recipe the order does not name is not tried",
          speech.chain("stt", "zh-CN", only) == ["local"])
    speech.mark_limited("azure", time.time() + 600, "429")
    check("a limited recipe is passed over",
          speech.chain("stt", "zh-CN", full) == ["local"]
          and "allowance" in dict(speech.explain("stt", "zh-CN", full))["azure"])
    clear_marks()
    speech.mark_dark("azure", "no route", time.time() + 600)
    check("so is a stood-down one",
          speech.chain("stt", "zh-CN", full) == ["local"]
          and "stood down" in dict(speech.explain("stt", "zh-CN", full))["azure"])
    clear_marks()
    from tutorboard import limits
    check("and speech's marks never read as the tutor's allowance",
          not limits.limit_record())

    # =======================================================================
    # 2. THE HOSTED RECIPES, against a stand-in
    # =======================================================================
    seen = []
    behave = {"azure_tts": 200, "azure_stt": 200, "azure_stream": False}
    reply_wav = os.path.join(box, "reply.wav")
    wav(reply_wav, tone(0.4))
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
                if status == 200 and behave["azure_stream"]:
                    # A streamed WAV: RIFF and data sizes 0xFFFFFFFF.
                    at = REPLY.index(b"data") + 4
                    streamed = (REPLY[:4] + b"\xff\xff\xff\xff" + REPLY[8:at]
                                + b"\xff\xff\xff\xff" + REPLY[at + 4:])
                    return self.answer(200, streamed, "audio/wav")
                return self.answer(status, REPLY if status == 200 else b"no", "audio/wav")
            if self.path.startswith("/azure/stt"):
                if behave["azure_stt"] != 200:
                    return self.answer(behave["azure_stt"], b"slow down", "text/plain")
                got = {"RecognitionStatus": "Success", "DisplayText": "你好。",
                       "NBest": [{"Display": "你好。", "Words": [
                           {"Word": "你好", "Offset": 1200000,
                            "Duration": 6000000}]}]}
                return self.answer(200, json.dumps(got).encode("utf-8"),
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
                        "stt": {"endpoint": base + "/azure/stt/{region}"}},
              "local": LOCAL}
    live = os.path.join(box, "live")
    os.makedirs(live)
    take_wav = os.path.join(box, "take.wav")
    wav(take_wav, tone())
    with open(take_wav, "rb") as fh:
        TAKE = fh.read()

    cfg = speech.load({"recipes": HOSTED})
    if CONVERTS:
        dest = os.path.join(box, "zh.m4a")
        got, by = speech.run("tts", "zh-CN", {"text": "你好", "dest": dest},
                             live=live, cfg=cfg)
        req = seen[-1]
        check("azure speaks first: SSML to the regional endpoint with the key",
              by == "azure" and req["path"].endswith("/westeurope")
              and req["headers"].get("Ocp-Apim-Subscription-Key") == "az-key"
              and req["headers"].get("Content-Type") == "application/ssml+xml"
              and req["headers"].get("X-Microsoft-OutputFormat")
              == "riff-24khz-16bit-mono-pcm", req["headers"])
        ssml = req["body"].decode("utf-8")
        check("in the language's voice, with no phoneme override",
              "zh-CN-XiaoxiaoNeural" in ssml and "xml:lang='zh-CN'" in ssml
              and "phoneme" not in ssml, ssml)
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
        check("azure refusing, this Mac speaks",
              by == "local" and open(dest, "rb").read() == b"fake m4a")
        check("and the refusal alone marks nothing",
              speech.chain("tts", "zh-CN", cfg)[0] == "azure")
        behave["azure_tts"] = 200
        behave["azure_stream"] = True
        got, by = speech.run("tts", "zh-CN", {"text": "你好", "dest": dest},
                             live=live, cfg=cfg)
        behave["azure_stream"] = False
        cost = [json.loads(l) for l in open(os.path.join(live, "cost.jsonl"))][-1]
        check("a streamed WAV declaring 0xFFFFFFFF bytes is sized from what came: "
              "0.4 s, not a day of audio",
              by == "azure" and abs(cost["seconds"] - 0.4) < 0.01
              and cost["usd"] < 0.001
              and abs(audio.seconds(reply_wav) - 0.4) < 0.01, cost)
        check("and still lands as an m4a",
              os.path.getsize(dest) > 0 and open(dest, "rb").read(12)[4:8] == b"ftyp")
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
          and req["body"] == TAKE
          and "Pronunciation-Assessment" not in req["headers"])
    check("and its words come back with their timings",
          got["text"] == "你好。" and got["words"][0]["text"] == "你好"
          and abs(got["words"][0]["start"] - 0.12) < 1e-6
          and abs(got["words"][0]["end"] - 0.72) < 1e-6, got)

    heard_says = os.path.join(box, "whisper-heard.json")
    with open(heard_says, "w") as fh:
        json.dump({"transcription": [{"text": "你好",
                                      "offsets": {"from": 0, "to": 600}}]}, fh)
    os.environ["WHISPER_SAYS"] = heard_says
    behave["azure_stt"] = 429
    got, by = speech.run("stt", "zh-CN", {"wav": take_wav}, live=live, cfg=cfg)
    check("a 429 passes the job on, to this Mac's whisper-cli",
          by == "local" and got["text"] == "你好", got)
    check("and marks azure limited, so the next job does not ask it",
          speech.chain("stt", "zh-CN", cfg) == ["local"])
    behave["azure_stt"] = 200
    clear_marks()
    unreach = speech.load({"recipes": dict(HOSTED, azure={
        "stt": {"endpoint": dead + "/stt/{region}"}})})
    got, by = speech.run("stt", "zh-CN", {"wav": take_wav}, live=live, cfg=unreach)
    check("an unreachable host is stood down and this Mac answers",
          by == "local" and speech.chain("stt", "zh-CN", unreach)[0] == "local")
    clear_marks()

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
    got, by = speech.run("stt", "zh-CN", {"wav": take_wav}, live=live,
                         cfg=speech.load({"order": {"stt": ["local"]},
                                          "recipes": {"local": LOCAL}}))
    check("a character whisper cut in two is joined whole, never U+FFFD",
          by == "local" and got["text"] == "你，好" and "\ufffd" not in got["text"], got)
    check("with the first half's start and the second's end, and punctuation "
          "no word",
          [(w["text"], w["start"], w["end"]) for w in got["words"]]
          == [("你", 0.1, 0.3), ("好", 0.33, 0.6)], got["words"])
    os.environ.pop("WHISPER_SAYS", None)
    costs = [json.loads(l) for l in open(os.path.join(live, "cost.jsonl"))]
    check("every job that answered wrote exactly one cost line",
          len(costs) == (7 if CONVERTS else 5)
          and all(c["requests"] == 1 and c["tokens"] == 0 for c in costs), costs)
    body, ctype = speech.multipart_body([("a", "1")], [("f", "x.wav", "audio/wav", b"RIFF")])
    check("the hand-built multipart ends with its closing boundary",
          body.endswith(("--%s--\r\n" % ctype.split("boundary=")[1]).encode()))

    from tutorboard.agents import usage
    out = io.StringIO()
    with open(os.path.join(live, "cost.jsonl"), "a") as fh:
        fh.write(json.dumps({"turn": 1, "agent": "deepseek", "tokens": 1000,
                             "requests": 2, "usd": 0.5}) + "\n")
    with contextlib.redirect_stdout(out):
        usage.cost_report({}, {"dir": "live", "root": live})
    check("`board cost` counts a speech job apart from the turns",
          "1 turn(s)" in out.getvalue() and "speech:" in out.getvalue(), out.getvalue())
    got, by = speech.run("stt", "zh-CN", {"wav": take_wav}, cfg=cfg)
    alone = usage.read_jsonl(os.path.join(os.environ["BOARD_STATE_DIR"],
                                          "speech-cost.jsonl"))
    check("a job with no session costs in the state directory's speech-cost.jsonl",
          len(alone) == 1 and alone[0]["agent"] == "speech:%s" % by, alone)
    only_speech = os.path.join(box, "only-speech")
    os.makedirs(only_speech)
    with open(os.path.join(only_speech, "cost.jsonl"), "w") as fh:
        fh.write(json.dumps(alone[0]) + "\n")
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        usage.cost_all({}, [{"dir": "live", "root": live},
                            {"dir": "only-speech", "root": only_speech}])
    said = out.getvalue()
    check("bare `board cost` shows speech apart from the turns: each place's, "
          "and the jobs no session paid for",
          "speech, apart from the turns" in said and "no session" in said
          and "only-speech" in said and "1 turn(s)" in said
          and "speech in total: %d job(s)" % (len(costs) + 2) in said, said)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        usage.cost_all({}, [{"dir": "only-speech", "root": only_speech}],
                       sessionless=False)
    check("and a place that only spoke still shows, with no sessionless line "
          "when one subject is asked for",
          "no turn has reported" in out.getvalue() and "only-speech" in out.getvalue()
          and "no session" not in out.getvalue(), out.getvalue())

    # =======================================================================
    # 3. THE SUBJECT'S SPEECH, AND WHAT A TURN IS TOLD
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
          said == {"lang": "zh-CN", "native": "en-US", "voice": "Tingting"}, said)
    check("and drops one that names no language",
          config.clean_speech({"voice": "x"}) is None
          and config.read_config(os.path.join(atlas, "courses", "Algebra"))["speech"] is None)

    sid = sessions.new("take", base=atlas)["id"]
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
    check("SPEECH_SENSE never grades a voice, and says so",
          "never grade a voice" in sense.SPEECH_SENSE.lower()
          and "tone" not in sense.SPEECH_SENSE.lower())
    check("and names `board hear`, which is a command",
          "board hear" in sense.SPEECH_SENSE)

    # =======================================================================
    # 4. CARDS: a `say` fence
    # =======================================================================
    jobs = []
    body = ("Say this:\n\n```say zh-CN\n你好\n```\n\n"
            "```python\nprint(1)\n```\n")
    out = cards.extract_tikz(body, jobs, repo)
    name = synth.sha("zh-CN", "你好", "Tingting")
    check("a say fence becomes a placeholder with the phrase after it",
          ("@@SAY:%s:pending:zh-CN@@ 你好\n" % name) in out
          and "```python" in out, out)
    check("and one job for the compiler thread, in the subject's voice",
          len(jobs) == 1 and jobs[0][0] == name and jobs[0][1] == "say"
          and json.loads(jobs[0][2])["voice"] == "Tingting"
          and json.loads(jobs[0][2])["live"] == repo.live, jobs)
    check("no pinyin rides in the marker or the job",
          "pinyin" not in out and "pinyin" not in jobs[0][2])
    out = cards.extract_tikz("```say zh-CN\n谢谢 (thank you)\n```\n", [], repo)
    check("a phrase keeps its own parentheses as words",
          "zh-CN@@ 谢谢 (thank you)\n" in out, out)
    os.makedirs(paths.SPEECH, exist_ok=True)
    with open(os.path.join(paths.SPEECH, name + ".m4a"), "wb") as fh:
        fh.write(b"cached")
    jobs = []
    out = cards.extract_tikz(body, jobs, repo)
    check("a cached phrase is ready and queues nothing",
          ("@@SAY:%s:ready:zh-CN@@" % name) in out and not jobs)
    write_config({"order": {"tts": ["local"], "stt": ["local"]},
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
    # 5. THE ROUTE, end to end, STT stubbed by the fake whisper-cli
    # =======================================================================
    from tutorboard.server import app
    httpd = app.make_server(atlas, 0, start=False)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    PORT = httpd.server_port
    says = os.path.join(box, "whisper-says.json")
    with open(says, "w") as fh:
        json.dump({"transcription": [
            {"text": "你", "offsets": {"from": 0, "to": 300}},
            {"text": "好", "offsets": {"from": 330, "to": 600}}]}, fh)
    os.environ["WHISPER_SAYS"] = says
    wav(take_wav, tone())
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
    status, got = post_take(sid, TAKE, {"lang": "zh-CN", "answers": "0003"})
    rec = got.get("heard") or {}
    check("POST /s/<id>/speech/say hears the take: 200, the words, by local",
          status == 200 and got.get("ok") and rec.get("heard") == "你好"
          and rec.get("stt_by") == "local" and "assess" not in rec,
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
    check("the heard record has the words and no grade",
          heard["heard"] == "你好" and "assess" not in heard
          and "verdict" not in heard and "pinyin" not in heard, heard)
    turns_rec = [json.loads(l) for l in open(os.path.join(where, "turns.jsonl"))]
    t = turns_rec[-1]
    check("a turn record of kind speech, answering the card",
          t["kind"] == "speech" and t["answers"] == "0003" and t["text"] == "你好"
          and not t["read"] and "tones" not in t and "target" not in t, t)
    msgs = inbox.unread(repo)
    m = msgs[-1]
    check("and a waking [speech] line: what was heard",
          m["text"].startswith("[speech] heard: '你好'.") and inbox.wakes(m),
          m.get("text"))
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
    check("the session's cost.jsonl has the STT alone",
          [c["speech"] for c in costs] == ["stt"], costs)
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
        status, got = post_take(sid, data, {"lang": "zh-CN"},
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
        answers[k] = post_take(sid, TAKE, {"lang": "zh-CN"})
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

    status, got = post_take(sid, TAKE, {})
    check("with no lang, the subject's speech.lang is used",
          status == 200 and got["heard"]["lang"] == "zh-CN", got)
    status, got = post_take(math_sid, TAKE, {})
    check("and a subject without one is asked to say which",
          status == 400 and "language" in got.get("error", ""), got)
    status, got = post_take(sid, b"", {"lang": "zh-CN"})
    check("an empty take is refused", status == 400, got)
    status, got = post_take(sid, b"not audio at all", {"lang": "zh-CN"},
                            filename="take.m4a", ctype="audio/mp4")
    check("audio nothing can read is 502, in words",
          status == 502 and "not heard" in got.get("error", ""), got)
    left = sorted(os.listdir(folder))
    check("and leaves the recording, but no 16 kHz WAV or half-written temp",
          got.get("audio") in left and not any(
              f.startswith(".wav16k-") or f == got["audio"].rsplit(".", 1)[0] + ".wav"
              for f in left), left)

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

    # A conversion is bounded by time: stand-ins for afinfo, afconvert and
    # ffmpeg, alone on the PATH.
    fakes = os.path.join(box, "fakes")
    os.makedirs(fakes)
    conv_log = os.path.join(box, "conv.log")
    small = os.path.join(box, "small.wav")
    wav(small, tone(0.4))

    def fake(name, body):
        path = os.path.join(fakes, name)
        with open(path, "w") as fh:
            fh.write("#!/bin/sh\necho %s \"$@\" >> %s\n%s\n" % (name, conv_log, body))
        os.chmod(path, 0o755)

    def fresh(*names):
        for f in os.listdir(fakes):
            os.remove(os.path.join(fakes, f))
        open(conv_log, "w").close()
        for name, body in names:
            fake(name, body)

    LAST = "for a; do last=$a; done"
    long_src = os.path.join(box, "long.m4a")
    with open(long_src, "wb") as fh:
        fh.write(b"m4a")
    out_dir = os.path.join(box, "conv")
    os.makedirs(out_dir)
    dst = os.path.join(out_dir, "take.wav")
    keep_path, keep_timeout = os.environ["PATH"], audio.TIMEOUT
    os.environ["PATH"] = fakes + ":/bin"
    try:
        fresh(("afinfo", "echo 'estimated duration: 3600.0 sec'"),
              ("afconvert", "exit 1"),
              ("ffmpeg", "%s; cp %s \"$last\"" % (LAST, small)))
        audio.to_wav16k(long_src, dst)
        calls = open(conv_log).read()
        check("an hour-long take afconvert would read whole goes through ffmpeg, "
              "stopped at the limit and a margin",
              "afconvert" not in calls and "-t %d" % (audio.MAX_SECONDS + audio.MARGIN)
              in calls and audio.wav_shape(dst), calls)
        os.remove(dst)
        fresh(("afinfo", "echo 'estimated duration: 3600.0 sec'"),
              ("afconvert", "exit 1"))
        try:
            audio.to_wav16k(long_src, dst)
            refused = ""
        except audio.Unconvertible as exc:
            refused = str(exc)
        check("and without ffmpeg it is refused in words, nothing written",
              "3600 s long" in refused and os.listdir(out_dir) == [], refused)
        fresh(("afinfo", "echo 'estimated duration: 3.0 sec'"),
              ("afconvert", "cp %s \"$3\"" % small))
        audio.to_wav16k(long_src, dst)
        check("a short take still goes through afconvert",
              "afconvert" in open(conv_log).read() and audio.wav_shape(dst))
        os.remove(dst)
        fresh(("afinfo", "echo 'estimated duration: 3.0 sec'"),
              ("afconvert", "echo half > \"$3\"; exit 1"))
        try:
            audio.to_wav16k(long_src, dst)
        except audio.Unconvertible:
            pass
        check("a conversion that fails leaves no partial WAV", os.listdir(out_dir) == [],
              os.listdir(out_dir))
        audio.TIMEOUT = 1
        fresh(("afinfo", "echo 'estimated duration: 3.0 sec'"),
              ("afconvert", "echo half > \"$3\"; exec sleep 5"))
        try:
            audio.to_wav16k(long_src, dst)
            timed = ""
        except audio.Unconvertible as exc:
            timed = str(exc)
        check("nor one that times out", "took more than" in timed
              and os.listdir(out_dir) == [], (timed, os.listdir(out_dir)))
    finally:
        os.environ["PATH"], audio.TIMEOUT = keep_path, keep_timeout

    from tutorboard.speech import hear
    deaf_live = os.path.join(box, "deaf")
    os.makedirs(os.path.join(deaf_live, "speech"))
    deaf_take = os.path.join(deaf_live, "speech", "t1.m4a")
    shutil.copyfile(small, deaf_take)
    keep_run = speech.run

    def deaf(*a, **k):
        raise speech.Refused("nobody could do stt")
    speech.run = deaf
    try:
        hear.take(deaf_live, deaf_take, "zh-CN")
        raised = False
    except speech.Refused:
        raised = True
    finally:
        speech.run = keep_run
    check("a take nobody could hear leaves its recording and no 16 kHz WAV",
          raised and sorted(os.listdir(os.path.join(deaf_live, "speech"))) == ["t1.m4a"],
          os.listdir(os.path.join(deaf_live, "speech")))

    # =======================================================================
    # 6. `board hear`, the audit, the multipart fields
    # =======================================================================
    loader = importlib.machinery.SourceFileLoader("boardcli", os.path.join(ROOT, "bin", "board"))
    spec = importlib.util.spec_from_loader("boardcli", loader)
    board = importlib.util.module_from_spec(spec)
    loader.exec_module(board)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = board.main(["hear", os.path.join(folder, base + ".heard.json")])
    check("`board hear <file>` prints what was heard and the words",
          code == 0 and "heard:   你好" in out.getvalue()
          and "words:" in out.getvalue() and "prototype" not in out.getvalue(),
          out.getvalue())
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = board.main(["hear", take_wav, "--lang", "zh-CN", "--json"])
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
    body, ctype = speech.multipart_body([("lang", "zh-CN")],
                                        [("audio", "a.wav", "audio/wav", b"RIFFxx")])
    folder2 = tempfile.mkdtemp(dir=box)
    types = []
    got = multipart.save_parts(io.BytesIO(body), len(body),
                               ctype.split("boundary=")[1].encode(), folder2,
                               lambda i, f: os.path.join(folder2, "x" + f),
                               fields=fields, types=types)
    check("the board's multipart reader keeps plain fields when asked",
          fields == {"lang": "zh-CN"} and types == ["audio/wav"]
          and open(got[0][1], "rb").read() == b"RIFFxx")

    # =======================================================================
    # 7. SETUP
    # =======================================================================
    brew = open(os.path.join(ATLAS_ROOT, "Brewfile")).read()
    check("the Brewfile has whisper.cpp, ffmpeg and espeak-ng",
          all('brew "%s"' % b in brew for b in ("whisper.cpp", "ffmpeg", "espeak-ng")))
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
    # 8. DOCTOR, and the real binaries when they are here
    # =======================================================================
    from tutorboard.speech import witness
    lines = []
    ok = witness.report(dry=True, cfg=speech.load({"recipes": {"local": LOCAL}}),
                        out=lines.append)
    joined = "\n".join(lines)
    check("doctor --dry names the chains and the local TTS and STT, and no grade",
          ok and "speech tts" in joined and "local tts:" in joined
          and "local stt:" in joined and "local assess:" not in joined, joined)
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
print("\nevery tutor speaks and listens")
