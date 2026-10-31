# Layout XL commands: short phrases that name an action, typed or (later) spoken.
#
#   run drc / launch lvs
#   flip horizontal / flip vertical
#   metal 2 / switch to met2 / layer poly
#   start wire min width / route on metal 3 width 0.5
#   up to metal 4 using 2x2 vias / via down / go up
#   fit / undo / redo / save
#
# parse(text) -> (name, args) or (None, reason) is pure Python (no KLayout), so the
# grammar can be tested on its own. execute(name, args) does the work in the GUI and
# returns a one-line result for the status bar.

import os
import re

# canonical layer names -> (layer, datatype) in gf180mcuD
LAYERS = {
  "COMP": (22, 0), "POLY": (30, 0), "CONT": (33, 0),
  "MET1": (34, 0), "VIA1": (35, 0), "MET2": (36, 0), "VIA2": (38, 0),
  "MET3": (42, 0), "VIA3": (40, 0), "MET4": (46, 0), "VIA4": (41, 0), "MET5": (81, 0),
}
METALS = ["MET1", "MET2", "MET3", "MET4", "MET5"]
# min wire width (um): M1.1, M2..M4.1, MT.1 (Metal5 is the 11K top metal in option D),
# PL.1_LV (3.3V poly interconnect; 5V/6V areas need 0.2)
MIN_WIDTH = {"MET1": 0.23, "MET2": 0.28, "MET3": 0.28, "MET4": 0.28, "MET5": 0.44, "POLY": 0.18}

NUMBER_WORDS = {"zero": "0", "one": "1", "two": "2", "three": "3", "four": "4",
                "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
                "ten": "10", "point": "."}

# --- parsing -----------------------------------------------------------------

def normalize(text):
  t = text.lower().replace("-", " ")
  t = re.sub(r"[^a-z0-9. ]", " ", t)
  t = " ".join(NUMBER_WORDS.get(w, w) for w in t.split())
  t = re.sub(r"(\d) \. (\d)", r"\1.\2", t)          # "0 . 5" -> "0.5"
  t = re.sub(r"\b\. (\d)", r".\1", t)
  t = re.sub(r"(\d) ?(?:by|x) ?(\d)", r"\1x\2", t)   # "2 by 2" -> "2x2"
  t = re.sub(r"\.(?!\d)", " ", t)                    # sentence-final dots
  return " ".join(t.split())


_LAYER_RE = (r"(?:(?:metal|met|m) ?(?P<m>[1-5])|(?P<v>via|v) ?(?P<vn>[1-4])"
             r"|(?P<poly>poly)|(?P<comp>comp|active|diffusion)|(?P<cont>contact|cont))")


def _layer(m):
  if m is None:
    return None
  if m.group("m"):
    return "MET" + m.group("m")
  if m.group("vn"):
    return "VIA" + m.group("vn")
  if m.group("poly"):
    return "POLY"
  if m.group("comp"):
    return "COMP"
  if m.group("cont"):
    return "CONT"
  return None


def parse(text):
  t = normalize(text)
  if not t:
    return None, "nothing heard"

  if re.search(r"\b(run|launch|start)\b.*\bdrc\b|^drc$", t):
    return "run_drc", {}
  if re.search(r"\b(run|launch|start)\b.*\blvs\b|^lvs$", t):
    return "run_lvs", {}

  m = re.search(r"\b(flip|mirror)\b.*\b(horizontal|horizontally|x)\b", t)
  if m:
    return "flip", {"axis": "h"}
  m = re.search(r"\b(flip|mirror)\b.*\b(vertical|vertically|y)\b", t)
  if m:
    return "flip", {"axis": "v"}

  # via moves before wire/layer: "move up to metal 4 using 2x2 vias", "via down", "go up"
  m = re.search(r"\b(?:move |go |via |vias )?(?P<dir>up|down)\b(?: to " + _LAYER_RE + r")?", t)
  if m and re.search(r"\b(up|down)\b", t) and not re.search(r"\b(zoom|pan|scroll)\b", t):
    args = {"dir": 1 if m.group("dir") == "up" else -1, "target": _layer(m)}
    a = re.search(r"\b(\d+)x(\d+)\b", t)
    if a:
      args["array"] = (int(a.group(1)), int(a.group(2)))
    return "via", args

  if re.search(r"\b(wire|route|path)\b", t):
    args = {}
    lm = re.search(r"\b" + _LAYER_RE + r"\b", t)
    if lm:
      args["layer"] = _layer(lm)
    w = re.search(r"\b(?:width|with) (\d+(?:\.\d+)?)\b", t)    # "with": a common mishearing
    if w:
      args["width"] = float(w.group(1))
    elif re.search(r"\b(min|minimum)\b", t):
      args["width"] = "min"
    return "wire", args

  m = re.search(r"^(?:switch |change |go |select )?(?:to )?(?:layer )?" + _LAYER_RE + r"$", t)
  if m:
    return "layer", {"layer": _layer(m)}

  if re.search(r"\b(zoom )?fit\b|\bzoom (all|out all)\b", t):
    return "fit", {}
  if re.search(r"^undo\b", t):
    return "undo", {}
  if re.search(r"^redo\b", t):
    return "redo", {}
  if re.search(r"^save\b", t):
    return "save", {}

  return None, "not a command: '%s'" % t


# --- execution (inside KLayout) ----------------------------------------------

def execute(name, args):
  import pya
  mw = pya.MainWindow.instance()
  view = mw.current_view()
  if view is None and name not in ("run_drc", "run_lvs"):
    return "no layout open"
  return globals()["_do_" + name](mw, view, **args)


def _trigger(mw, path):
  menu = mw.menu()
  if not menu.is_valid(path):
    return False
  menu.action(path).trigger()
  return True


def _pdk_macro(kind):
  # the PDK's own "Run Klayout DRC/LVS" entries, run directly (same as its menu)
  import pya
  for base in os.environ.get("KLAYOUT_PATH", "").split(":"):
    path = os.path.join(base, "macros", "gf180mcu_%s.ly%s" % (kind, kind))
    if os.path.isfile(path):
      return pya.Macro(path)
  return None


def _run_pdk(mw, kind):
  import pya
  cv = pya.CellView.active()
  if not cv.is_valid() or not cv.filename():
    return "save the layout to a file first (the PDK %s reads it from disk)" % kind.upper()
  macro = _pdk_macro(kind)
  if macro is None:
    return "gf180mcu %s macro not found on KLAYOUT_PATH" % kind.upper()
  macro.run()          # runs to completion; results open in the marker browser
  return "%s finished (gf180mcu PDK): see the marker browser" % kind.upper()


def _do_run_drc(mw, view):
  return _run_pdk(mw, "drc")


def _do_run_lvs(mw, view):
  return _run_pdk(mw, "lvs")


def _do_flip(mw, view, axis):
  if not view.has_selection():
    return "select something to flip first"
  _trigger(mw, "edit_menu.selection_menu.sel_flip_x" if axis == "h" else "edit_menu.selection_menu.sel_flip_y")
  return "flipped " + ("horizontally" if axis == "h" else "vertically")


def _current_layer_name(view):
  import pya
  it = view.current_layer
  if it.at_end():
    return None
  node = it.current()
  for name, (l, d) in LAYERS.items():
    if node.source_layer == l and node.source_datatype == d:
      return name
  return None


def _set_layer(view, name):
  import pya
  l, d = LAYERS[name]
  it = view.begin_layers()
  while not it.at_end():
    node = it.current()
    if not node.has_children() and node.source_layer == l and node.source_datatype == d:
      view.current_layer = it
      return True
    it.next()
  # not in the layer list yet: add it, so it can be drawn on
  cv = view.active_cellview()
  if not cv.is_valid():
    return False
  cv.layout().layer(pya.LayerInfo(l, d))
  props = pya.LayerProperties()
  props.source = "%d/%d@%d" % (l, d, cv.index() + 1)
  view.insert_layer(view.end_layers(), props)
  return _set_layer(view, name) if _layer_present(view, l, d) else False


def _layer_present(view, l, d):
  it = view.begin_layers()
  while not it.at_end():
    n = it.current()
    if n.source_layer == l and n.source_datatype == d:
      return True
    it.next()
  return False


def _do_layer(mw, view, layer):
  if not _set_layer(view, layer):
    return "could not select %s" % layer
  return "layer %s %d/%d" % ((layer,) + LAYERS[layer])


def _do_wire(mw, view, layer=None, width=None):
  if not view.is_editable():
    return "the layout is read-only: start KLayout with -e to draw wires"
  if layer and not _set_layer(view, layer):
    return "could not select %s" % layer
  current = _current_layer_name(view)
  if width == "min":
    if current not in MIN_WIDTH:
      return "no min width known for %s: say a width" % (current or "this layer")
    width = MIN_WIDTH[current]
  if width is not None:
    mw.set_config("edit-path-width", "%g" % width)
  view.switch_mode("path")
  return "wire on %s, width %s um: click to start" % (current or "current layer", mw.get_config("edit-path-width"))


def _do_via(mw, view, dir, target=None, array=None):
  from layout_xl import vias
  current = _current_layer_name(view)
  steps = 1
  if target:
    if target not in METALS or current not in METALS:
      return "vias go between metals (now on %s)" % (current or "unknown layer")
    steps = METALS.index(target) - METALS.index(current)
    if steps == 0:
      return "already on %s" % target
    dir, steps = (1 if steps > 0 else -1), abs(steps)
  if array:
    vias.set_array(*array)
  path = "@secrets.via_up" if dir > 0 else "@secrets.via_down"
  for _ in range(steps):
    if not _trigger(mw, path):
      return "via command not available (draw a wire first, in edit mode)"
  nx, ny = vias.ARRAY
  size = ("%dx%d" % (nx, ny)) if nx and ny else "auto"
  return "via %s x%d (%s): now on %s" % ("up" if dir > 0 else "down", steps, size, _current_layer_name(view) or "?")


def _do_fit(mw, view):
  view.zoom_fit()
  return "fit"


def _do_undo(mw, view):
  _trigger(mw, "edit_menu.undo")
  return "undo"


def _do_redo(mw, view):
  _trigger(mw, "edit_menu.redo")
  return "redo"


def _do_save(mw, view):
  _trigger(mw, "file_menu.save")
  return "saved"
