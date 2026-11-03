# Voice commands inside KLayout: tap Ctrl+Shift, say a command, stop talking.
#
# The recogniser runs in a helper process (kit/voice/server.py, its own venv, installed
# by kit/voice/setup.sh). KLayout only detects the tap, asks the helper to listen, polls
# its output on a timer and hands the text to layout_xl.commands. If the helper is not
# installed, dies or the microphone fails, voice says so in the status bar and the rest
# of KLayout carries on.

import json
import os
import subprocess
import time

import pya

from layout_xl import commands

DATA = os.environ.get("LAYOUT_XL_DATA", os.path.expanduser("~/.local/share/layout-xl"))
PYTHON = os.path.join(DATA, "voice-venv", "bin", "python")
MODEL = os.path.join(DATA, "vosk-model-small-en-us-0.15")
LOG = os.path.join(DATA, "voice-helper.log")
# commands.py lives in kit/layout_xl/python/layout_xl/ (reached through the salt symlink)
KIT = os.path.normpath(os.path.join(os.path.dirname(os.path.realpath(commands.__file__)), "..", "..", ".."))
SERVER = os.path.join(KIT, "voice", "server.py")

TAP_MAX_S = 1.0          # measured taps: 480-580 ms
CHORD = {pya.Qt.Key_Control.to_i(), pya.Qt.Key_Shift.to_i()}
POLL_MS = 50


def _get(x):
  # KLayout's Qt bindings expose some getters as properties, some as methods
  return x() if callable(x) else x


def installed():
  missing = [p for p in (PYTHON, MODEL, SERVER) if not os.path.exists(p)]
  return not missing, missing


class TapFilter(pya.QObject):
  # Calls on_tap() when Ctrl and Shift are pressed and released together with no other
  # key in between, within TAP_MAX_S. Ctrl+Shift+<key> shortcuts are not taps. Never
  # consumes an event.

  def __init__(self, on_tap):
    pya.QObject.__init__(self)
    self.on_tap = on_tap
    self.down, self.seen, self.other, self.t0 = set(), set(), False, 0.0
    self.last = None      # an application filter sees an event once per widget it reaches

  def eventFilter(self, obj, ev):
    t = ev.type()
    if (t == pya.QEvent.KeyPress or t == pya.QEvent.KeyRelease) and not _get(ev.isAutoRepeat):
      press = (t == pya.QEvent.KeyPress)
      sig = (press, _get(ev.key), _get(ev.timestamp))
      if sig != self.last:
        self.last = sig
        self._key(press, sig[1])
    return pya.QObject.eventFilter(self, obj, ev)

  def _key(self, press, key):
    if press:
      if key in CHORD:
        if not self.down:
          self.t0, self.seen, self.other = time.time(), set(), False
        self.down.add(key)
        self.seen.add(key)
      elif self.down:
        self.other = True
    elif key in self.down:
      self.down.discard(key)
      if not self.down and self.seen == CHORD and not self.other and time.time() - self.t0 <= TAP_MAX_S:
        try:
          self.on_tap()
        except Exception as e:
          print("layout_xl voice: %s" % e)


class Voice(object):

  def __init__(self):
    self.proc = None
    self.buf = b""
    self.ready = False
    self.listening = False
    self.want_listen = False
    self.timer = pya.QTimer()
    self.timer.interval = POLL_MS
    self.timer.timeout(self._poll)

  # --- status bar ---

  def _msg(self, text, ms=8000):
    print("layout_xl voice: " + text)
    mw = pya.MainWindow.instance()
    if mw is not None:
      mw.message("Voice: " + text, ms)

  # --- helper process ---

  def start(self):
    ok, missing = installed()
    if not ok:
      return "not installed (missing %s): run doc/claude/kit/voice/setup.sh" % ", ".join(missing)
    if self.proc is not None and self.proc.poll() is None:
      return None
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)     # KLayout's embedded Python must not leak into the venv
    log = open(LOG, "ab")
    self.proc = subprocess.Popen([PYTHON, "-I", SERVER, MODEL], stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE, stderr=log, env=env, close_fds=True)
    log.close()
    os.set_blocking(self.proc.stdout.fileno(), False)
    self.buf, self.ready, self.listening = b"", False, False
    self.timer.start()
    return None

  def stop(self):
    self.timer.stop()
    if self.proc is not None and self.proc.poll() is None:
      self.proc.stdin.close()       # the helper exits on EOF
      try:
        self.proc.wait(2)
      except subprocess.TimeoutExpired:
        self.proc.kill()
    self.proc = None

  def tap(self):
    if self.listening:
      return self._msg("still listening...")
    err = self.start()
    if err:
      return self._msg(err, 15000)
    if self.ready:
      self._send("listen")
    else:
      self.want_listen = True
      self._msg("starting the recogniser...")

  def _send(self, line):
    try:
      self.proc.stdin.write((line + "\n").encode())
      self.proc.stdin.flush()
    except (BrokenPipeError, OSError) as e:
      self._msg("helper gone (%s), see %s" % (e, LOG))
      self.proc = None

  def _poll(self):
    if self.proc is None:
      self.timer.stop()
      return
    try:
      chunk = os.read(self.proc.stdout.fileno(), 65536)
    except BlockingIOError:
      chunk = None
    if chunk:
      self.buf += chunk
      while b"\n" in self.buf:
        line, self.buf = self.buf.split(b"\n", 1)
        try:
          self._handle(json.loads(line.decode()))
        except Exception as e:
          self._msg("bad helper output %r: %s" % (line[:80], e))
    elif self.proc.poll() is not None:     # EOF and exited
      self.timer.stop()
      code = self.proc.returncode
      self.proc, self.ready, self.listening = None, False, False
      self._msg("helper stopped (exit %s), see %s; tap again to restart" % (code, LOG), 15000)

  def _handle(self, m):
    if "error" in m:
      self.listening = False
      self._msg(m["error"], 15000)
    elif m.get("ready"):
      self.ready = True
      if self.want_listen:
        self.want_listen = False
        self._send("listen")
    elif m.get("listening"):
      self.listening = True
      self._msg("listening... say a command", 10000)
    elif "text" in m:
      self.listening = False
      self._msg(self.dispatch(m["text"]))

  def dispatch(self, text):
    if not text.strip():
      return "nothing heard"
    name, args = commands.parse_heard(text)
    if name is None:
      return "heard '%s': %s" % (text, args)
    try:
      return "'%s' -> %s" % (text, commands.execute(name, args))
    except Exception as e:
      return "'%s' -> %s failed: %s" % (text, name, e)


_voice = None
_filter = None


def install():
  # idempotent; returns the Voice instance
  global _voice, _filter
  if _voice is None:
    _voice = Voice()
    _filter = TapFilter(_voice.tap)
    pya.QApplication.instance().installEventFilter(_filter)
    if installed()[0]:
      _voice.start()          # load the model now, so the first tap is quick
  return _voice
