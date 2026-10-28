import sys, pya, time
print("python", sys.version.split()[0])
import klayout; print("klayout module from", klayout.__file__)
lib = pya.Library.library_by_name("skywater130")
print("libs:", list(pya.Library.library_names()))
if not lib:
    sys.exit("ERR no skywater130 library (check KLAYOUT_PATH/KLAYOUT_PYTHONPATH)")
names = [lib.layout().pcell_declaration(i).name() for i in lib.layout().pcell_ids()]
print("pcells:", names)
ly = pya.Layout(); top = ly.create_cell("TOP")
for name, params in [("nfet", {}), ("nfet", {"w": 2.0, "l": 0.5, "nf": 4}), ("pfet", {}), ("res_poly", {}), ("mim_cap", {}), ("vias_gen", {}), ("guard_ring_gen", {})]:
    t = time.time()
    try:
        c = ly.create_cell(name, "skywater130", params)
        bb = c.dbbox() if c else None
        nshapes = sum(c.shapes(li).size() for li in ly.layer_indexes()) if c else 0
        # a broken PCell yields an empty cell instead of raising
        tag = "OK " if nshapes else "ERR"
        print(f"{tag} {name:15s} {params} bbox={bb} shapes={nshapes} {time.time()-t:.2f}s")
        top.insert(pya.CellInstArray(c.cell_index(), pya.Trans()))
    except Exception as e:
        print(f"ERR {name:15s} {params}: {str(e)[:300]}")
decl = lib.layout().pcell_declaration("nfet")
print("nfet params:", [(p.name, p.default) for p in decl.get_parameters()][:14])
ly.write(out)
