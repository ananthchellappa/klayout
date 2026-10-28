import pya
ly = pya.Layout(); ly.dbu = 0.001
top = ly.create_cell("TOP")
c = ly.create_cell("nfet", "skywater130", {"w": 1.0, "l": 0.15, "nf": 1, "gate_con_pos": "top", "bulk": "bulk tie"})
top.insert(pya.CellInstArray(c.cell_index(), pya.Trans()))
ly.write(out)
