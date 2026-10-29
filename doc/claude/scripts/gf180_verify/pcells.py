# Generate every gf180mcu_klayoutapi PCell at its default parameters; print ERR for any that fails or is empty.
import pya
lib = pya.Library.library_by_name("gf180mcu_klayoutapi")
if lib is None:
    raise RuntimeError("gf180mcu_klayoutapi not registered: is KLAYOUT_PATH set (source ~/pdk/gf180mcuD.env)?")
ly = pya.Layout(); ly.dbu = 0.001
top = ly.create_cell("TOP")
# Broken upstream at the pinned commit: the deep-nwell diodes exhaust memory in Cell.flatten
# (that took WSL down at 12 GB); efuse raises TypeError (draw_efuse missing device_name).
SKIP = {"diode_pw2dw", "diode_dw2ps", "efuse"}
x = 0.0
for name in lib.layout().pcell_names():
    if name in SKIP:
        print(f"SKIP {name:16s} known broken upstream"); continue
    try:
        c = ly.create_cell(name, "gf180mcu_klayoutapi", {})
    except Exception as e:
        print(f"ERR  {name:16s} {e}"); continue
    n = 0; layers = set()
    for li in ly.layer_indexes():
        it = c.begin_shapes_rec(li)
        while not it.at_end():
            n += 1; layers.add(li); it.next()
    print(f"{'OK ' if n else 'ERR'}  {name:16s} shapes={n:5d} layers={len(layers):2d} size={c.dbbox().width():.2f}x{c.dbbox().height():.2f} um")
    top.insert(pya.DCellInstArray(c.cell_index(), pya.DTrans(x - c.dbbox().left, -c.dbbox().bottom)))
    x += c.dbbox().width() + 20
ly.write(out)
