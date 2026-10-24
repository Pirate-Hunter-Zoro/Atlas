#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# speech-model.sh -- the one whisper model the board's local listener loads.
#
#     bash scripts/speech-model.sh
#
# Downloads ggml-small-q5_1.bin into ~/.local/share/tutor-board/models/
# (TUTORBOARD_MODELS moves it) and checks it against the pinned SHA-256. A
# model already there with the right checksum is left alone, so a second run
# changes nothing and fetches nothing. A download that does not match is
# deleted, never kept. The checksum is Hugging Face's own (the file's LFS oid);
# a model rename is the three lines below.
#
# For tests, SPEECH_MODEL_FETCH names the downloader, run as
# `<fetch> <url> <output file>`; SPEECH_MODEL_URL and SPEECH_MODEL_SHA256
# replace the pins.
# ---------------------------------------------------------------------------
set -uo pipefail

NAME="ggml-small-q5_1.bin"
URL="${SPEECH_MODEL_URL:-https://huggingface.co/ggerganov/whisper.cpp/resolve/main/$NAME}"
SHA256="${SPEECH_MODEL_SHA256:-ae85e4a935d7a567bd102fe55afc16bb595bdb618e11b2fc7591bc08120411bb}"

DIR="${TUTORBOARD_MODELS:-$HOME/.local/share/tutor-board/models}"
DEST="$DIR/$NAME"

sum_of() { shasum -a 256 "$1" 2>/dev/null | cut -d' ' -f1; }

fetch() {
  if [ -n "${SPEECH_MODEL_FETCH:-}" ]; then
    "$SPEECH_MODEL_FETCH" "$1" "$2"
  else
    curl -fsSL --retry 2 -o "$2" "$1"
  fi
}

if [ -f "$DEST" ] && [ "$(sum_of "$DEST")" = "$SHA256" ]; then
  echo "ok    whisper model $NAME unchanged"
  exit 0
fi

mkdir -p "$DIR" || { echo "----  could not make $DIR"; exit 1; }
PART="$DEST.part"
rm -f "$PART"
if ! fetch "$URL" "$PART"; then
  rm -f "$PART"
  echo "----  the whisper model did not download from $URL; rerun when online"
  exit 1
fi
GOT="$(sum_of "$PART")"
if [ "$GOT" != "$SHA256" ]; then
  rm -f "$PART"
  echo "----  the whisper model's SHA-256 is $GOT, not the pinned $SHA256; deleted"
  exit 1
fi
mv -f "$PART" "$DEST"
echo "ok    whisper model $NAME downloaded and checked"
