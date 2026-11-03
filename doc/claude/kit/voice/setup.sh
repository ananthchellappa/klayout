#!/bin/bash
# Voice spike setup: a Python venv with Vosk + sounddevice, and the small English Vosk
# model (40 MB, Apache 2.0), both under ~/.local/share/layout-xl (outside the repo).
set -euo pipefail
BASE=${LAYOUT_XL_DATA:-$HOME/.local/share/layout-xl}
MODEL=vosk-model-small-en-us-0.15
mkdir -p "$BASE"
[ -x "$BASE/voice-venv/bin/python" ] || python3 -m venv "$BASE/voice-venv"
"$BASE/voice-venv/bin/pip" -q install vosk sounddevice
if [ ! -d "$BASE/$MODEL" ]; then
  tmp=$(mktemp -d)
  curl -fsSL -o "$tmp/m.zip" "https://alphacephei.com/vosk/models/$MODEL.zip"
  "$BASE/voice-venv/bin/python" -I -c "import sys, zipfile; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])" "$tmp/m.zip" "$BASE"
  rm -rf "$tmp"
fi
echo "ready. Test with:"
echo "  $BASE/voice-venv/bin/python $(cd "$(dirname "$0")" && pwd)/listen.py --model $BASE/$MODEL --test"
