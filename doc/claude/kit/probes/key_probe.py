# Key probe: does KLayout (on this display server) see clean press/release events for
# modifier-only chords? Decides whether "tap Ctrl+Shift to talk" can work.
#
#   klayout -e -rm doc/claude/kit/probes/key_probe.py
#
# Logs every key press/release KLayout receives (while its window has focus), next to
# the X server's live modifier state, and prints "TAP Ctrl+Shift" when the chord is
# tapped: both pressed, both released, no other key in between, within TAP_MAX_S.
# Ctrl+Shift+<key> shortcuts must NOT print TAP.

import time
import pya

TAP_MAX_S = 0.6
NAMES = {pya.Qt.Key_Control.to_i(): "Ctrl", pya.Qt.Key_Shift.to_i(): "Shift",
         pya.Qt.Key_Alt.to_i(): "Alt", pya.Qt.Key_Meta.to_i(): "Meta",
         pya.Qt.Key_Super_L.to_i(): "Super_L", pya.Qt.Key_Super_R.to_i(): "Super_R"}
CHORD = {"Ctrl", "Shift"}


def _get(x):
  # KLayout's Qt bindings expose some getters as properties (ev.key), some as methods
  return x() if callable(x) else x


def _live_mods():
  # asks the X server, unlike QGuiApplication.keyboardModifiers() (Qt's cached copy)
  try:
    m = pya.QGuiApplication.queryKeyboardModifiers().to_i()
  except Exception as e:
    return "? (%s)" % e
  return "+".join(n for bit, n in ((0x04000000, "Ctrl"), (0x02000000, "Shift"),
                                   (0x08000000, "Alt"), (0x10000000, "Meta")) if m & bit) or "-"


class KeyProbe(pya.QObject):

  def __init__(self):
    pya.QObject.__init__(self)
    self.down = set()           # chord keys currently down
    self.seen = set()           # chord keys pressed since the chord started
    self.other = False          # a non-chord key was pressed during the chord
    self.t0 = 0.0
    self.last = None            # app filters see one event once per widget it propagates to

  def eventFilter(self, obj, ev):
    t = ev.type()
    if t == pya.QEvent.KeyPress or t == pya.QEvent.KeyRelease:
      press = (t == pya.QEvent.KeyPress)
      if not _get(ev.isAutoRepeat):
        sig = (press, _get(ev.key), _get(ev.timestamp))
        if sig != self.last:
          self.last = sig
          self._key(press, sig[1])
    return pya.QObject.eventFilter(self, obj, ev)

  def _key(self, press, key):
    name = NAMES.get(key, "key 0x%x" % key)
    now = time.time()
    if press:
      if name in CHORD:
        if not self.down:
          self.t0, self.seen, self.other = now, set(), False
        self.down.add(name)
        self.seen.add(name)
      elif self.down:
        self.other = True
    print("key_probe: %-7s %-10s live mods: %s" % ("press" if press else "release", name, _live_mods()),
          flush=True)
    if not press and name in self.down:
      self.down.discard(name)
      if not self.down:
        dt = now - self.t0
        if self.seen == CHORD and not self.other and dt <= TAP_MAX_S:
          print("key_probe: >>> TAP Ctrl+Shift (%.0f ms) - would start listening" % (dt * 1000), flush=True)
        elif self.seen == CHORD:
          why = "another key pressed" if self.other else "held %.0f ms" % (dt * 1000)
          print("key_probe:     (Ctrl+Shift not a tap: %s)" % why, flush=True)


_key_probe = KeyProbe()
pya.QApplication.instance().installEventFilter(_key_probe)
print("key_probe: installed - click into the KLayout window, then tap Ctrl+Shift", flush=True)
