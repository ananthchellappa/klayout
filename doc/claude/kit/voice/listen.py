# Voice spike: microphone -> Vosk (vocabulary restricted to the command words) ->
# layout_xl.commands.parse. Nothing is sent to KLayout yet; it prints what it heard and
# which command that becomes.
#
#   listen.py --model DIR           say commands until Ctrl+C (Enter before each)
#   listen.py --model DIR --test    read the test phrases aloud, get a score at the end
#   listen.py --model DIR a.wav ..  decode recordings instead of the microphone
#
# Each utterance ends by itself when you stop talking (Vosk's endpointing). In --test
# mode the recordings are kept in ~/.local/share/layout-xl/voice-test/ (outside the
# repo) so changes to the vocabulary can be re-checked against them.

import argparse
import json
import os
import sys
import time
import wave

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "layout_xl", "python"))
from layout_xl import commands   # noqa: E402  (parse() needs no KLayout)

RATE = 16000
BLOCK = 1600                      # 0.1 s
MAX_S = 8.0
SAVE_DIR = os.path.expanduser("~/.local/share/layout-xl/voice-test")

# every word the command grammar uses; anything else comes out as [unk]
WORDS = """
run launch start check drc lvs
flip mirror horizontal horizontally vertical vertically
metal met via poly comp active contact
switch change go select to layer
wire route path min minimum width with on
zero one two three four five six seven eight nine ten point by x using
up down move
fit zoom all undo redo save
""".split()

TESTS = [
  ("run drc", ("run_drc", {})),
  ("launch lvs", ("run_lvs", {})),
  ("flip", ("flip", {"axis": "h"})),
  ("flip vertical", ("flip", {"axis": "v"})),
  ("metal two", ("layer", {"layer": "MET2"})),
  ("switch to metal three", ("layer", {"layer": "MET3"})),
  ("poly", ("layer", {"layer": "POLY"})),
  ("start wire min width", ("wire", {"width": "min"})),
  ("route on metal three width zero point five", ("wire", {"layer": "MET3", "width": 0.5})),
  ("up to metal four using two by two vias", ("via", {"dir": 1, "target": "MET4", "array": (2, 2)})),
  ("via down", ("via", {"dir": -1, "target": None})),
  ("go up", ("via", {"dir": 1, "target": None})),
  ("fit", ("fit", {})),
  ("undo", ("undo", {})),
  ("save", ("save", {})),
]


def recognizer(model):
  from vosk import KaldiRecognizer
  rec = KaldiRecognizer(model, RATE, json.dumps(WORDS + ["[unk]"]))
  rec.SetWords(True)
  return rec


def _result(rec, final):
  r = json.loads(rec.FinalResult() if final else rec.Result())
  words = r.get("result", [])
  conf = min((w["conf"] for w in words), default=0.0)
  return r.get("text", ""), conf


def from_wav(model, path):
  rec = recognizer(model)
  w = wave.open(path)
  while True:
    d = w.readframes(4000)
    if not d:
      break
    rec.AcceptWaveform(d)
  return _result(rec, True)


def from_mic(model, save=None):
  import sounddevice as sd
  rec = recognizer(model)
  frames = []
  with sd.RawInputStream(samplerate=RATE, channels=1, dtype="int16", blocksize=BLOCK) as stream:
    t0 = time.time()
    while time.time() - t0 < MAX_S:
      data, _ = stream.read(BLOCK)
      data = bytes(data)
      frames.append(data)
      if rec.AcceptWaveform(data):
        text, conf = _result(rec, False)
        if text and text != "[unk]":
          break
    else:
      text, conf = _result(rec, True)
  if save:
    with wave.open(save, "wb") as w:
      w.setnchannels(1)
      w.setsampwidth(2)
      w.setframerate(RATE)
      w.writeframes(b"".join(frames))
  return text, conf


def show(text, conf):
  # [unk] = a word outside the command vocabulary: something other than a command was
  # said ("place nfet ..." comes out as "[unk] fit ..."), so don't act on the rest
  if "[unk]" in text.split():
    name, args = None, "not understood (words outside the command vocabulary)"
  else:
    name, args = commands.parse(text)
  print("  heard: %-45r conf %.2f -> %s %s" % (text, conf, name or "-", args))
  return name, args


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("--model", required=True)
  ap.add_argument("--test", action="store_true")
  ap.add_argument("wavs", nargs="*")
  a = ap.parse_args()

  from vosk import Model, SetLogLevel
  SetLogLevel(-1)
  model = Model(a.model)

  if a.wavs:
    for p in a.wavs:
      print(p)
      show(*from_wav(model, p))
    return

  if a.test:
    os.makedirs(SAVE_DIR, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    good = 0
    for i, (phrase, want) in enumerate(TESTS):
      input("\n[%d/%d] press Enter, then say: \"%s\"" % (i + 1, len(TESTS), phrase))
      got = show(*from_mic(model, os.path.join(SAVE_DIR, "%s-%02d.wav" % (stamp, i))))
      ok = got == want
      good += ok
      print("  " + ("ok" if ok else "WRONG, wanted %s %s" % want))
    print("\n%d/%d right. Recordings: %s/%s-*.wav" % (good, len(TESTS), SAVE_DIR, stamp))
    return

  print("Ctrl+C to stop.")
  while True:
    input("\npress Enter and say a command")
    show(*from_mic(model))


if __name__ == "__main__":
  try:
    main()
  except KeyboardInterrupt:
    print()
