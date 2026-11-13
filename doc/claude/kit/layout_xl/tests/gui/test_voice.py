# Voice end to end with simulated Ctrl+Shift taps; the helper decodes recordings
# (LAYOUT_XL_VOICE_WAV, set by run_gui_tests.sh) instead of the microphone.
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # KLayout ignores PYTHONPATH
import pya
from common import spin, check, done, tap, LAYOUT
from layout_xl import voice, commands

mw = pya.MainWindow.instance()
mw.load_layout(LAYOUT, 1)
view = mw.current_view()
v = voice.install()
spin(3)
check("helper ready", v.ready, True)

tap(); spin(2)                                       # "metal two"
check("tap 1 -> layer", commands._current_layer_name(view), "MET2")
tap(extra=pya.Qt.Key_A.to_i()); spin(1)              # Ctrl+Shift+A: not a tap
check("Ctrl+Shift+A not a tap", v.listening, False)
tap(hold=1.5); spin(1)                               # held: not a tap
check("held 1.5 s not a tap", v.listening, False)
tap(); spin(2)                                       # "start wire min width"
check("tap 2 -> wire width", mw.get_config("edit-path-width"), "0.28")
mw.set_config("edit-path-width", "0.5")
tap(); spin(2)                                       # "place nfet ..." -> rejected
check("tap 3 rejected, nothing changed", mw.get_config("edit-path-width"), "0.5")

v.proc.kill(); spin(1)                               # helper dies -> next tap restarts it
check("helper death noticed", v.proc, None)
tap(); spin(4)                                       # new helper: recordings start over
check("restarted after kill", v.proc is not None and v.proc.poll() is None, True)
v.stop()
done()
