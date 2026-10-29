# Generate one gf180mcu_klayoutapi PCell (-rd name=...) at defaults and report its shape count.
import pya, sys
ly = pya.Layout(); ly.dbu = 0.001
c = ly.create_cell(name, "gf180mcu_klayoutapi", {})
n = 0
for li in ly.layer_indexes():
    it = c.begin_shapes_rec(li)
    while not it.at_end():
        n += 1; it.next()
print(f"{'OK ' if n else 'ERR'}  {name:16s} shapes={n:5d} size={c.dbbox().width():.2f}x{c.dbbox().height():.2f} um", flush=True)
