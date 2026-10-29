# One 3.3 V nfet, W=1 L=0.28, with a bulk tie: input for the DRC and LVS checks.
import pya
ly = pya.Layout(); ly.dbu = 0.001
top = ly.create_cell("TOP")
c = ly.create_cell("nfet", "gf180mcu_klayoutapi", {"w": 1.0, "l": 0.28, "nf": int(nf), "volt": "3.3V", "bulk": "Bulk Tie"})
top.insert(pya.CellInstArray(c.cell_index(), pya.Trans()))
ly.write(out)
