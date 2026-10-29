#!/usr/bin/env python3
# Layout-XL kit fixes to the gf180mcuD KLayout files, applied by install_gf180.sh to the
# assembled tree (the pinned upstream sources are left untouched).
#
#   patch_gf180.py <libs.tech/klayout>
#
# 1. pymacros/gf180mcu.lym: without gdsfactory, skip the gdsfactory PCell library and say
#    what that means, instead of printing an error-like warning.
# 2. Contact counts: the PCells compute "how many contacts fit" with int(...), which goes
#    negative when a device is too small. KLayout takes CellInstArray counts as unsigned, so
#    -1 becomes 2**64-1 contacts and Cell.flatten exhausts memory (this OOM-killed WSL).
#    Clamp every such count at 0: a too-small device then draws without contacts and DRC
#    flags it.
# 3. diode_pw2dw / diode_dw2ps: defaults (also the minimums the form enforces) of
#    0.22 x 0.36 um are far too small for these deep n-well diodes and trigger 2.
#    Raise them to 3 x 3 um, the smallest size found to be DRC-clean throughout.
#
# Each patch checks that the upstream text it replaces is there, and fails loudly if not.

import re
import sys
from pathlib import Path

# (w, l) in um. Every contact row is present from 1.62 x 0.68 (pw2dw) and 2.62 x 1.68
# (dw2ps), but DRC only becomes reliably clean later, and not monotonically (pw2dw is clean
# at l=1.28 and dirty at 1.38-1.58). 3 x 3 and every w, l in 3..10 tested clean at both
# voltages (324 sizes). See doc/claude/gf180_pdk.md.
DIODE_MIN = {"diode_pw2dw": ("3", "3"), "diode_dw2ps": ("3", "3")}

GDSFACTORY_BLOCK = '''# Load the gdsfactory based PCells (patched by the Layout-XL kit, see patch_gf180.py)
import importlib.util
if importlib.util.find_spec("gdsfactory") is None:
    print("## gf180mcuD (Layout-XL kit): using the KLayout-API PCell library gf180mcu_klayoutapi.")
    print("##   Skipped: the gdsfactory PCell library 'gf180mcu' (gdsfactory is not installed).")
    print("##   Given up: via_dev, the via-stack PCell; it exists only in that library.")
    print("##     Every device (MOS, BJT, diodes, MIM/MOS caps, resistors) is in gf180mcu_klayoutapi.")
    print("##   To get it: install gdsfactory~=7.9.4 (the PDK's pinned version) for the Python")
    print("##     KLayout embeds, then restart. Untested here; see doc/claude/gf180_pdk.md.")
else:
    try:
        from cells import gf180mcu
        gf180mcu()
        print("## gf180mcu PDK Pcells loaded.")
    except Exception as e:
        print(f"## gf180mcu PDK gdsfactory based Pcells failed to load, got an exception: {e}.")
        print("## Please check that you have a relevant gdsfactory module version installed.")

'''

# single-line contact counts: num_cont = int(...), nx = int(...) + 1, ny = ..., nxgr = ...
COUNT_RE = re.compile(r"^(\s*(?:num_cont|nx|ny|nxgr)\s*=\s*)(int\(.*\)(?:\s*\+\s*1)?)\s*$", re.M)
EXPECTED_COUNTS = {"draw_cap_mim.py": 1, "draw_cap_mos.py": 1, "draw_res.py": 1,
                   "draw_diode.py": 1, "draw_fet.py": 11, "draw_mos.py": 11}


def patch_gdsfactory(lym):
  text = lym.read_text()
  start = text.index("# Load the gdsfactory based PCells")
  end = text.index("# Load the KLayout API based PCells")
  lym.write_text(text[:start] + GDSFACTORY_BLOCK + text[end:])


def patch_counts(cells):
  for name, expected in EXPECTED_COUNTS.items():
    path = cells / name
    text, n = COUNT_RE.subn(r"\1max(0, \2)", path.read_text())
    if n != expected:
      sys.exit(f"patch_gf180: {name}: expected {expected} contact counts, found {n}")
    path.write_text(text)


def patch_diode_minimums(cells):
  path = cells / "diode.py"
  text = path.read_text()
  for cell, (w, l) in DIODE_MIN.items():
    for dim, value in (("l", l), ("w", w)):
      text, n = re.subn(rf"^{cell}_{dim} = [0-9.]+$", f"{cell}_{dim} = {value}", text, flags=re.M)
      if n != 1:
        sys.exit(f"patch_gf180: diode.py: no '{cell}_{dim} = ...' line")
  path.write_text(text)


def main():
  root = Path(sys.argv[1])
  cells = root / "pymacros" / "klayout_api_cells"
  patch_gdsfactory(root / "pymacros" / "gf180mcu.lym")
  patch_counts(cells)
  patch_diode_minimums(cells)
  print("[INFO] patched: gdsfactory notice, contact counts clamped, diode minimum sizes")


main()
