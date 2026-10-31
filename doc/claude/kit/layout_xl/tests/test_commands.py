# Grammar tests for layout_xl.commands.parse (plain Python, no KLayout):
#   python3 -I doc/claude/kit/layout_xl/tests/test_commands.py
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "python"))
from layout_xl.commands import parse

CASES = [
  ("run DRC", ("run_drc", {})),
  ("launch drc", ("run_drc", {})),
  ("Launch LVS.", ("run_lvs", {})),
  ("flip vertical", ("flip", {"axis": "v"})),
  ("flip horizontally", ("flip", {"axis": "h"})),
  ("mirror vertically", ("flip", {"axis": "v"})),
  ("switch to MET2", ("layer", {"layer": "MET2"})),
  ("metal two", ("layer", {"layer": "MET2"})),
  ("Metal 3.", ("layer", {"layer": "MET3"})),
  ("layer poly", ("layer", {"layer": "POLY"})),
  ("m1", ("layer", {"layer": "MET1"})),
  ("start wire route min width", ("wire", {"width": "min"})),
  ("start wire minimum width", ("wire", {"width": "min"})),
  ("route on metal 3 width 0.5", ("wire", {"layer": "MET3", "width": 0.5})),
  ("start a wire on metal two with zero point five", ("wire", {"layer": "MET2", "width": 0.5})),
  ("wire", ("wire", {})),
  ("move up to MET4 using 2x2 vias", ("via", {"dir": 1, "target": "MET4", "array": (2, 2)})),
  ("move up to metal four using two by two vias", ("via", {"dir": 1, "target": "MET4", "array": (2, 2)})),
  ("go down to metal 1", ("via", {"dir": -1, "target": "MET1"})),
  ("via up", ("via", {"dir": 1, "target": None})),
  ("go down", ("via", {"dir": -1, "target": None})),
  ("up with 3 by 2 vias", ("via", {"dir": 1, "target": None, "array": (3, 2)})),
  ("zoom fit", ("fit", {})),
  ("fit", ("fit", {})),
  ("undo", ("undo", {})),
  ("save", ("save", {})),
  ("box on metal 2 from here to there", (None, None)),
  ("", (None, None)),
]

fails = 0
for text, want in CASES:
  got = parse(text)
  ok = got == want if want[0] else got[0] is None
  fails += not ok
  print("%s %-50r -> %r" % ("ok  " if ok else "FAIL", text, got))
print("%d/%d passed" % (len(CASES) - fails, len(CASES)))
sys.exit(1 if fails else 0)
