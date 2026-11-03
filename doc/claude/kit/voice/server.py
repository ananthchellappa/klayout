# Voice helper process for KLayout (started by layout_xl_voice.lym, one per KLayout).
# Runs in its own venv so Vosk, PortAudio and the model stay out of KLayout's process:
# if anything here crashes, KLayout only loses voice.
#
# Line protocol, JSON out:
#   -> {"ready": true} | {"error": "..."}          once, after loading the model
#   stdin "listen"  -> {"listening": true}, then {"text": "...", "conf": 0.9}
#                                               or {"error": "..."}
#   stdin EOF (KLayout exited) -> the helper exits
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def say(**kw):
  sys.stdout.write(json.dumps(kw) + "\n")
  sys.stdout.flush()


def main():
  try:
    from vosk import Model, SetLogLevel
    import listen
    SetLogLevel(-1)
    model = Model(sys.argv[1])
  except Exception as e:
    say(error="voice helper could not start: %s" % e)
    return 1
  say(ready=True)
  for line in sys.stdin:
    if line.strip() != "listen":
      continue
    say(listening=True)
    try:
      # LAYOUT_XL_VOICE_WAV=a.wav[:b.wav...]: decode recordings in turn instead of the
      # microphone (for testing the KLayout side without speaking)
      wavs = [w for w in os.environ.get("LAYOUT_XL_VOICE_WAV", "").split(":") if w]
      if wavs:
        n = getattr(main, "n", 0)
        main.n = n + 1
        text, conf = listen.from_wav(model, wavs[n % len(wavs)])
      else:
        text, conf = listen.from_mic(model)
      say(text=text, conf=conf)
    except Exception as e:
      say(error="microphone: %s" % e)
  return 0


if __name__ == "__main__":
  sys.exit(main())
