# Shared helpers for the hidden-window GUI tests (run through run_gui_tests.sh).
import os
import sys
import time

import pya

LAYOUT = os.environ.get("LAYOUT_XL_TEST_GDS", os.path.expanduser("~/tmp/gf180-verify/nfet1.gds"))
failures = []


def spin(s):
  # run the Qt event loop for s seconds (timers, the voice helper's output)
  t = time.time()
  while time.time() - t < s:
    pya.QCoreApplication.processEvents()
    time.sleep(0.02)


def check(what, got, want):
  ok = got == want
  print("%s %s: %r" % ("ok  " if ok else "FAIL", what, got) + ("" if ok else " (wanted %r)" % (want,)))
  if not ok:
    failures.append(what)


def done():
  print("RESULT: %s" % ("PASS" if not failures else "FAIL (%s)" % ", ".join(failures)))
  # exit explicitly so a failure shows in the exit code; os._exit skips Python's
  # buffered output, so flush first
  sys.stdout.flush()
  sys.stderr.flush()
  os._exit(1 if failures else 0)


def key(kind, k):
  mw = pya.MainWindow.instance()
  pya.QApplication.sendEvent(mw, pya.QKeyEvent(kind, k, pya.Qt.KeyboardModifier.NoModifier))


def tap(hold=0.1, extra=None):
  C, S = pya.Qt.Key_Control.to_i(), pya.Qt.Key_Shift.to_i()
  KP, KR = pya.QEvent.KeyPress, pya.QEvent.KeyRelease
  key(KP, C)
  key(KP, S)
  if extra:
    key(KP, extra)
    key(KR, extra)
  time.sleep(hold)
  key(KR, C)
  key(KR, S)
