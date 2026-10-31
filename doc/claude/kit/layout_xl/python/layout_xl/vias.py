# gf180mcuD via PCells for KLayout's wire (path) tool.
#
# Registers the library "gf180mcu_vias" with one PCell that declares Via1..Via4 as via
# types (PCellDeclaration#via_types). With it, pressing "O" (or Edit > via up/down) while
# drawing a path drops a via and continues the wire on the next metal.
#
# Rules (gf180mcu DRC deck, rule_decks/via.rb and metal.rb, option D = 5LM):
#   V*.1   via size 0.26 x 0.26            V*.2a  via space 0.26
#   V*.2b  space 0.36 inside 4x4+ arrays   V*.3b/4a metal overlap >= 0.01
#   V*.3c/4b end-of-line overlap 0.06 when the metal is < 0.34 wide
#   M1.1 0.23, M2..M4.1 0.28 min width
#   Metal5 is the top metal in option D (11K), so MT.1 (width 0.44) and MT.4 (area 0.5625)
#   apply to it instead of M5.1.
# We use 0.06 enclosure on all sides, so the metal pads are >= 0.38 and the
# end-of-line rule never applies. Via4's top pad is at least 0.76 square, so even an
# isolated via meets the top-metal area rule.
#
# The array size comes from the wire width unless set: ARRAY = (nx, ny) overrides it
# for every via placed afterwards (the "with 2x2 vias" voice/typed command sets it).

import math
import pya

LIB_NAME = "gf180mcu_vias"

VIA_SIZE = 0.26
VIA_SPACE = 0.26
VIA_SPACE_BIG = 0.36      # V*.2b: arrays of 4x4 or more
ENCLOSURE = 0.06
GRID = 0.005

# (name, description, bottom, cut, top, min top pad) as (layer, datatype)
STACK = [
  ("V1", "Via1 (Metal1-Metal2)", (34, 0), (35, 0), (36, 0), 0.0),
  ("V2", "Via2 (Metal2-Metal3)", (36, 0), (38, 0), (42, 0), 0.0),
  ("V3", "Via3 (Metal3-Metal4)", (42, 0), (40, 0), (46, 0), 0.0),
  ("V4", "Via4 (Metal4-Metal5)", (46, 0), (41, 0), (81, 0), 0.76),
]
TOP_PAD = {name: pad for name, _, _, _, _, pad in STACK}

ARRAY = (0, 0)            # (nx, ny); 0 = derive from the wire width


def set_array(nx, ny):
  global ARRAY
  ARRAY = (max(0, int(nx)), max(0, int(ny)))


def _snap_up(v):
  return math.ceil(v / GRID - 1e-9) * GRID


class ViaPCell(pya.PCellDeclarationHelper):

  def __init__(self):
    super(ViaPCell, self).__init__()
    # the five parameters every via PCell must have (see PCellDeclaration#via_types)
    self.param("via", self.TypeString, "Via type", default="V1")
    self.param("w_bottom", self.TypeDouble, "Bottom width", default=0.0)
    self.param("h_bottom", self.TypeDouble, "Bottom height", default=0.0)
    self.param("w_top", self.TypeDouble, "Top width", default=0.0)
    self.param("h_top", self.TypeDouble, "Top height", default=0.0)
    self.param("nx", self.TypeInt, "Columns (0 = auto)", default=0)
    self.param("ny", self.TypeInt, "Rows (0 = auto)", default=0)

    self.types = []
    pad = VIA_SIZE + 2 * ENCLOSURE
    for name, desc, bottom, cut, top, _ in STACK:
      vt = pya.ViaType(name, desc)
      vt.bottom = pya.LayerInfo(*bottom)
      vt.cut = pya.LayerInfo(*cut)
      vt.top = pya.LayerInfo(*top)
      vt.wbmin = vt.hbmin = vt.wtmin = vt.htmin = pad
      vt.bottom_grid = vt.top_grid = GRID
      self.types.append(vt)

  def via_types(self):
    return self.types

  def display_text_impl(self):
    nx, ny = self._array()
    return "%s %dx%d" % (self.via, nx, ny)

  def coerce_parameters_impl(self):
    pass

  def can_create_from_shape_impl(self):
    return False

  def _fit(self, a, b):
    # how many cuts fit across the narrower of the two requested metal widths
    dims = [d for d in (a, b) if d > 1e-9]
    if not dims:
      return 1
    room = min(dims) - 2 * ENCLOSURE
    return max(1, int(math.floor((room + VIA_SPACE) / (VIA_SIZE + VIA_SPACE) + 1e-9)))

  def _array(self):
    nx = self.nx or ARRAY[0] or self._fit(self.w_bottom, self.w_top)
    ny = self.ny or ARRAY[1] or self._fit(self.h_bottom, self.h_top)
    return nx, ny

  def produce_impl(self):
    vt = next((t for t in self.types if t.name == self.via), None)
    if vt is None:
      return
    nx, ny = self._array()
    space = VIA_SPACE_BIG if (nx >= 4 and ny >= 4) else VIA_SPACE
    pitch = VIA_SIZE + space
    wcut = nx * VIA_SIZE + (nx - 1) * space
    hcut = ny * VIA_SIZE + (ny - 1) * space
    top_pad = TOP_PAD[vt.name]
    for layer, w, h, pad in ((vt.bottom, self.w_bottom, self.h_bottom, 0.0),
                             (vt.top, self.w_top, self.h_top, top_pad)):
      pw = _snap_up(max(w, wcut + 2 * ENCLOSURE, pad)) / 2
      ph = _snap_up(max(h, hcut + 2 * ENCLOSURE, pad)) / 2
      self.cell.shapes(self.layout.layer(layer)).insert(pya.DBox(-pw, -ph, pw, ph))
    cut = self.cell.shapes(self.layout.layer(vt.cut))
    for ix in range(nx):
      for iy in range(ny):
        x = (ix - 0.5 * (nx - 1)) * pitch
        y = (iy - 0.5 * (ny - 1)) * pitch
        cut.insert(pya.DBox(-VIA_SIZE / 2, -VIA_SIZE / 2, VIA_SIZE / 2, VIA_SIZE / 2).moved(x, y))


class ViaLib(pya.Library):

  def __init__(self):
    self.description = "gf180mcuD vias for the wire tool (Layout XL kit)"
    self.layout().register_pcell("Via", ViaPCell())
    # Not tied to a technology on purpose: a GDS opened without the gf180mcu technology
    # selected still gets vias (they are matched by layer number).
    self.register(LIB_NAME)


def register():
  if pya.Library.library_by_name(LIB_NAME) is None:
    ViaLib()
