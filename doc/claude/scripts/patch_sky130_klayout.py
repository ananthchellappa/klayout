"""Patch open_pdks' sky130A KLayout files for KLayout 0.30 + gdsfactory 9 / kfactory 3.

Ported from IIC-OSIC-TOOLS (_build/images/open_pdks/scripts/install_ciel.sh).
Idempotent: each patch is skipped if already applied, and fails loudly if its
target pattern is missing (i.e. upstream changed and the patch needs review).

usage: python3 patch_sky130_klayout.py <PDK_ROOT>/sky130A/libs.tech/klayout
"""

import pathlib
import re
import sys

MARK = "# patched-by: patch_sky130_klayout.py"


def patch_lyt(lyt: pathlib.Path) -> None:
    # open_pdks ships the generic "sky130" tech name, a sky130.lyp reference and the
    # build machine's absolute base path
    s = lyt.read_text()
    if not re.search(r">sky130<|sky130\.lyp|<base-path>", s):
        print(f"skip  {lyt.name}: already clean")
        return
    s = s.replace(">sky130<", ">sky130A<").replace("sky130.lyp", "sky130A.lyp")
    s = re.sub(r"\s*<base-path>.*?</base-path>", "\n <base-path/>", s)
    s = re.sub(r"<original-base-path>.*?</original-base-path>",
               "<original-base-path>$PDK_ROOT/$PDK/libs.tech/klayout</original-base-path>", s)
    lyt.write_text(s)
    print(f"patch {lyt.name}")


def patch_boolean_ops(cells: pathlib.Path) -> None:
    # gdsfactory >= 8 dropped the "A-B" boolean operation string
    n = 0
    for f in cells.rglob("*.py"):
        s = f.read_text()
        t = re.sub(r'operation= *"A-B"', 'operation="-"', s)
        if t != s:
            f.write_text(t)
            n += 1
    print(f"patch boolean ops in {n} file(s)")


def patch_pdk_py(pdk: pathlib.Path) -> None:
    # pdk.py uses kfactory 0.x internals; kfactory >= 1 also locks cached cells
    s = pdk.read_text()
    if MARK in s:
        print("skip  pdk.py: already patched")
        return
    old1 = "  kf.kcell._get_default_kcl().clear()\n"
    new1 = ("  " + MARK + "\n"
            "  try:\n"
            "    kf.kcell._get_default_kcl().clear()\n"
            "  except AttributeError:\n"
            "    kf.kcl.clear()\n")
    old2 = "  source_cell = c._kdb_cell\n"
    new2 = ("  source_cell = getattr(c, \"kdb_cell\", None)\n"
            "  if source_cell is None:\n"
            "    source_cell = c._kdb_cell\n"
            "  for cell in source_cell.layout().each_cell():\n"
            "    if cell.locked:\n"
            "      cell.locked = False\n")
    for old in (old1, old2):
        if old not in s:
            sys.exit(f"pdk.py: pattern not found, review patch: {old.strip()!r}")
    pdk.write_text(s.replace(old1, new1).replace(old2, new2))
    print("patch pdk.py")


SHIM = '''
''' + MARK + '''
def _gf9_compat():
    from typing import Optional
    import gdsfactory as gf

    def _add_array(self, component, columns=2, rows=2, spacing=(100, 100), alias: Optional[str] = None):
        return self.add_ref(component=component, name=alias, columns=columns, rows=rows,
                            column_pitch=spacing[0], row_pitch=spacing[1])

    # gdsfactory 9 removed Component.add_array
    if not hasattr(gf.Component, "add_array"):
        gf.Component.add_array = _add_array
    # gdsfactory >= 9.29 no longer auto-activates the generic PDK used for layer lookup
    try:
        gf.get_active_pdk()
    except Exception:
        gf.gpdk.PDK.activate()


_gf9_compat()
'''


def patch_init(init: pathlib.Path) -> None:
    s = init.read_text()
    if MARK in s:
        print("skip  cells/__init__.py: already patched")
        return
    init.write_text(s + SHIM)
    print("patch cells/__init__.py")


def main() -> None:
    root = pathlib.Path(sys.argv[1])
    cells = root / "python" / "cells"
    patch_lyt(root / "tech" / "sky130A.lyt")
    if cells.is_dir():
        patch_boolean_ops(cells)
        patch_pdk_py(cells / "pdk.py")
        patch_init(cells / "__init__.py")
    else:
        print(f"warn  no PCell dir at {cells}")


if __name__ == "__main__":
    main()
