# Command palette: search, install hints, keyboard, typed commands, running rows.
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # KLayout ignores PYTHONPATH
import pya
from common import spin, check, done, LAYOUT
from layout_xl import palette, commands

mw = pya.MainWindow.instance()
mw.load_layout(LAYOUT, 1)
view = mw.current_view()
check("menu shortcut", mw.menu().action("layout_xl_menu.palette").effective_shortcut(), "Ctrl+Shift+P")

dlg = palette.Palette(mw)
check("rows found (> 200)", len(dlg.rows) > 200, True)
check("list widget filled", palette._get(dlg.list.count) > 200, True)


def titles(q, n=3):
  dlg.edit.text = q
  return [r.title for r in dlg.shown[:n]]

check("flip", titles("flip", 2), ["Flip horizontally", "Flip vertically"])
check("menu breadcrumb", [r.detail for r in dlg.shown if r.title == "Flip Horizontally"][:1], ["Edit › Layout"])
check("drc first", titles("drc", 1), ["Run DRC"])
check("typed command row", titles("up to metal 4 using 2x2 vias", 1), ["Do: up to metal 4 using 2x2 vias"])
check("words for numbers", titles("metal two", 1), ["Do: metal two"])
dlg.edit.text = "xyzzy"
check("no match", (len(dlg.shown), dlg.info.text), (0, "nothing matches"))
dlg.edit.text = "box on metal 2 from here"
check("not a command explained", dlg.info.text.startswith("not a command"), True)

dlg.edit.text = "lvs"
lvs = [r for r in dlg.shown if r.title == "Run LVS"][0]
check("LVS hint names the netlist", "nfet1.cdl" in (lvs.hint or ""), True)
dlg.edit.text = "via stack"
dlg._enter()
check("Enter on greyed row keeps it open", (dlg.chosen, "gdsfactory" in dlg.info.text), (None, True))

dlg.edit.text = "flip"
pya.QApplication.sendEvent(dlg.edit, pya.QKeyEvent(pya.QEvent.KeyPress, pya.Qt.Key_Down.to_i(),
                                                   pya.Qt.KeyboardModifier.NoModifier))
check("Down arrow moves selection", palette._get(dlg.list.currentRow), 1)

for q, layer in (("metal two", "MET2"), ("layer met3", "MET3")):
  dlg.edit.text = q
  dlg._enter()
  palette.run_row(dlg.chosen)
  check("ran %r" % q, commands._current_layer_name(view), layer)
dlg.edit.text = ""
check("recent first", [r.title for r in dlg.shown[:2]], ["Do: layer met3", "Do: metal two"])

# the real modal dialog, driven by a timer
inst = []
orig = palette.Palette.__init__
def init(self, parent):
  orig(self, parent)
  inst.append(self)
palette.Palette.__init__ = init
def drive():
  inst[-1].edit.text = "metal 4"
  inst[-1]._enter()
t = pya.QTimer()
t.singleShot = True
t.interval = 300
t.timeout(drive)
t.start()
palette.show()
check("modal dialog runs the row", commands._current_layer_name(view), "MET4")
done()
