# Command palette (Ctrl+Shift+P): one searchable list of
#   - the Layout XL commands, each with the phrase that says it ("up to metal 4 ..."),
#   - every KLayout menu action, read from the menu tree (so it stays complete),
#   - features that need something installed, greyed, with what to install.
# Typing a whole command ("up to metal 4 using 2x2 vias") offers it as the first row,
# parsed by the same grammar as voice. Enter runs the selected row.

import importlib.util
import os

import pya

from layout_xl import commands, voice

RECENT_MAX = 5


def _get(x):
  # KLayout's Qt bindings expose some getters as properties, some as methods
  return x() if callable(x) else x

_recent = []              # the last rows run, newest first (typed commands included)


# --- what each feature needs ----------------------------------------------------
# Each check returns None when the feature can be used, else what the user should do.

def _need_pdk_macro(kind):
  def check():
    return None if commands._pdk_macro(kind) else \
      "needs the gf180mcu PDK on KLAYOUT_PATH: run doc/claude/kit/install.sh, then source ~/pdk/gf180mcuD.env"
  return check


def _need_lvs_netlist():
  hint = _need_pdk_macro("lvs")()
  if hint:
    return hint
  cv = pya.CellView.active()
  if cv.is_valid() and cv.filename():
    base = os.path.splitext(cv.filename())[0]
    if not any(os.path.isfile(base + ext) for ext in (".cdl", ".spice", ".cir")):
      return "needs the schematic netlist next to the layout: %s.cdl (or .spice)" % os.path.basename(base)
  return None


def _need_voice():
  ok, missing = voice.installed()
  return None if ok else "needs the recogniser: run doc/claude/kit/voice/setup.sh (offline, 40 MB)"


def _need_gdsfactory():
  return None if importlib.util.find_spec("gdsfactory") else \
    "needs gdsfactory~=7.9.4 in KLayout's Python, then a restart (see doc/claude/gf180_pdk.md)"


# --- rows -------------------------------------------------------------------------

class Row(object):

  def __init__(self, title, detail, run, shortcut="", need=None, enabled=True):
    self.title = title
    self.detail = detail          # the phrase to say, or the menu path
    self.run = run                # callable returning a status-bar message (or None)
    self.shortcut = shortcut
    self.need = need              # callable -> None or install hint
    self.enabled = enabled
    self.hint = None

  def text(self):
    s = self.title
    if self.detail:
      s += "   — " + self.detail
    if self.shortcut:
      s += "   [" + self.shortcut + "]"
    if self.hint:
      s += "   (" + self.hint + ")"
    elif not self.enabled:
      s += "   (not available now)"
    return s

  def haystack(self):
    return (self.title + " " + self.detail).lower()


def _cmd(name, **args):
  return lambda: commands.execute(name, args)


def _layout_xl_rows():
  rows = [
    Row("Run DRC", "say: run drc", _cmd("run_drc"), need=_need_pdk_macro("drc")),
    Row("Run LVS", "say: launch lvs", _cmd("run_lvs"), need=_need_lvs_netlist),
    Row("Flip horizontally", "say: flip", _cmd("flip", axis="h")),
    Row("Flip vertically", "say: flip vertical", _cmd("flip", axis="v")),
    Row("Wire at min width", "say: start wire min width", _cmd("wire", width="min")),
    Row("Via up", "say: via up / up to metal 4 using 2x2 vias", _cmd("via", dir=1)),
    Row("Via down", "say: via down", _cmd("via", dir=-1)),
    Row("Voice command", "tap Ctrl+Shift, then say a command", lambda: voice.install().tap(), need=_need_voice),
    Row("Via stack PCell (via_dev)", "gf180mcu library",
        lambda: "place it from the Libraries panel: gf180mcu › via_dev", need=_need_gdsfactory),
  ]
  for name in commands.LAYERS:
    say = name.lower().replace("met", "metal ").replace("via", "via ")
    rows.append(Row("Layer " + name, "say: " + say, _cmd("layer", layer=name)))
  return rows


def _strip(title):
  return title.replace("&&", "\0").replace("&", "").replace("\0", "&").rstrip(".").strip()


def _menu_rows(menu):
  rows = []

  def walk(path, crumbs):
    for c in menu.items(path):
      if menu.is_separator(c):
        continue
      a = menu.action(c)
      if a is None or not a.is_effective_visible():
        continue
      title = _strip(a.title)
      if menu.is_menu(c):
        walk(c, crumbs + [title] if title else crumbs)
      elif title:
        rows.append(Row(title, " › ".join(crumbs), (lambda a=a: a.trigger()),
                        shortcut=a.effective_shortcut(), enabled=a.is_effective_enabled()))

  for top in menu.items(""):
    if not top.split(".")[-1].startswith("@"):     # @toolbar, context menus: duplicates
      a = menu.action(top)
      if a is not None and a.is_effective_visible():
        # KLayout's own top-level menus report an empty title: name them from the path
        title = _strip(a.title) or top.replace("_menu", "").replace("_group", "").replace("_", " ").title()
        walk(top, [title])
  return rows


def all_rows():
  mw = pya.MainWindow.instance()
  rows = _layout_xl_rows() + _menu_rows(mw.menu())
  for r in rows:
    if r.need:
      try:
        r.hint = r.need()
      except Exception as e:
        r.hint = "check failed: %s" % e
  return rows


def search(rows, query):
  # every word of the query must appear; title-prefix matches first, then recent rows
  q = query.lower().split()
  titles = [r.title for r in _recent]
  if not q:
    return list(_recent) + [r for r in rows if r.title not in titles]
  hits = [r for r in rows if all(w in r.haystack() for w in q)]
  joined = " ".join(q)

  def rank(r):
    t = r.title.lower()
    return (0 if t.startswith(joined) else 1 if any(w.startswith(q[0]) for w in t.split()) else 2,
            0 if r.title in titles else 1)
  return sorted(hits, key=rank)


def typed_row(query):
  # a whole command typed into the search box, e.g. "up to metal 4 using 2x2 vias"
  if len(query.split()) < 2:
    return None
  name, args = commands.parse(query)
  if name is None:
    return None
  desc = ", ".join("%s %s" % (k, v) for k, v in sorted(args.items()) if v is not None)
  return Row("Do: " + query.strip(), (name + (" (" + desc + ")" if desc else "")),
             _cmd(name, **args))


# --- dialog -----------------------------------------------------------------------

class Palette(pya.QDialog):

  def __init__(self, parent):
    pya.QDialog.__init__(self, parent)
    self.windowTitle = "Layout XL commands"
    self.resize(720, 440)
    self.rows = all_rows()
    self.shown = []
    self.chosen = None
    box = pya.QVBoxLayout(self)
    self.edit = pya.QLineEdit(self)
    self.edit.placeholderText = "search, or type a command: up to metal 4 using 2x2 vias"
    self.list = pya.QListWidget(self)
    self.info = pya.QLabel(self)
    self.info.wordWrap = True
    box.addWidget(self.edit)
    box.addWidget(self.list)
    box.addWidget(self.info)
    self.edit.textChanged(self._refilter)
    self.edit.returnPressed(self._enter)
    self.list.itemActivated(lambda item: self._enter())
    self.list.currentRowChanged(self._show_info)
    self.edit.installEventFilter(self)
    self._refilter("")

  def eventFilter(self, obj, ev):
    # arrow keys in the search box move the selection, so the hands stay on the keys
    if ev.type() == pya.QEvent.KeyPress:
      key = _get(ev.key)
      step = {pya.Qt.Key_Down.to_i(): 1, pya.Qt.Key_Up.to_i(): -1,
              pya.Qt.Key_PageDown.to_i(): 10, pya.Qt.Key_PageUp.to_i(): -10}.get(key)
      if step and self.shown:
        row = max(0, min(len(self.shown) - 1, _get(self.list.currentRow) + step))
        self.list.setCurrentRow(row)
        return True
    return pya.QDialog.eventFilter(self, obj, ev)

  def _refilter(self, text):
    self.shown = search(self.rows, text)
    typed = typed_row(text)
    if typed:
      self.shown.insert(0, typed)
    self.list.clear()
    grey = pya.QBrush(pya.QColor(140, 140, 140))
    for i, r in enumerate(self.shown[:300]):
      self.list.addItem(r.text())      # QListWidgetItem(text, list) doesn't add it here
      if r.hint or not r.enabled:
        self.list.item(i).setForeground(grey)
    if self.shown:
      self.list.setCurrentRow(0)
    else:
      self.info.text = "nothing matches" if len(text.split()) < 2 else commands.parse(text)[1]

  def _show_info(self, i):
    if 0 <= i < len(self.shown):
      r = self.shown[i]
      self.info.text = r.hint or ("" if r.enabled else "not available now (needs a selection, a layout, ...)")

  def _enter(self):
    i = _get(self.list.currentRow)
    if not (0 <= i < len(self.shown)):
      return
    r = self.shown[i]
    if r.hint:
      self.info.text = r.hint     # stay open: the user reads what to install
      return
    self.chosen = r
    self.accept()


def run_row(r):
  _recent[:] = [x for x in _recent if x.title != r.title]
  _recent.insert(0, r)
  del _recent[RECENT_MAX:]
  try:
    msg = r.run()
  except Exception as e:
    msg = "%s failed: %s" % (r.title, e)
  return msg


def show():
  mw = pya.MainWindow.instance()
  dlg = Palette(mw)
  dlg.exec_()
  # run after the dialog has closed, so focus is back in the layout view (via up/down
  # in the middle of a wire needs that)
  if dlg.chosen is not None:
    r = dlg.chosen
    msg = run_row(r)
    if msg:
      mw.message("Layout XL: " + msg, 8000)
      print("layout_xl: %s -> %s" % (r.title, msg))
  dlg._destroy()
