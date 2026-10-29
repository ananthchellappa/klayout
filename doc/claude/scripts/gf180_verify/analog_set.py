# The devices a first analog block needs, with realistic parameters for gf180mcuD (MIM option B).
import pya
ly = pya.Layout(); ly.dbu = 0.001
top = ly.create_cell("TOP")
specs = [
    ("nfet_bt",   "nfet",      {"w": 2.0, "l": 0.5, "nf": 1, "volt": "3.3V", "bulk": "Bulk Tie"}),
    ("pfet_bt",   "pfet",      {"w": 4.0, "l": 0.5, "nf": 1, "volt": "3.3V", "bulk": "Bulk Tie"}),
    ("nfet_gr",   "nfet",      {"w": 2.0, "l": 0.5, "nf": 4, "volt": "3.3V", "bulk": "Guard Ring"}),
    ("pfet_gr",   "pfet",      {"w": 4.0, "l": 0.5, "nf": 4, "volt": "3.3V", "bulk": "Guard Ring"}),
    ("mimb_m5",   "cap_mim",   {"mim_option": "MIM-B", "metal_level": "M5", "w": 10.0, "l": 10.0}),
    ("ppolyf_u",  "ppolyf_u_resistor", {"w": 1.0, "l": 10.0}),
    ("hires",     "ppolyf_u_high_Rs_resistor", {"w": 1.0, "l": 10.0}),
    # deep-nwell diodes at their (patched) default = minimum size
    ("dio_pw2dw", "diode_pw2dw", {"volt": "3.3V"}),
    ("dio_dw2ps", "diode_dw2ps", {"volt": "3.3V"}),
]
x = 0.0
for tag, name, p in specs:
    c = ly.create_cell(name, "gf180mcu_klayoutapi", p)
    c.name = tag                                   # so drc_by_device.py reports by tag
    top.insert(pya.DCellInstArray(c.cell_index(), pya.DTrans(round(x - c.dbbox().left, 3), round(-c.dbbox().bottom, 3))))
    x += round(c.dbbox().width() + 20, 0)
    print(f"{tag:10s} {name:28s} {c.dbbox().width():.2f}x{c.dbbox().height():.2f} um")
ly.write(out)
