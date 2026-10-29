# Attribute DRC markers in a gallery report (-rd gds=... -rd rdb=...) to the PCell instance they fall in.
import pya, collections
ly = pya.Layout(); ly.read(gds)
boxes = [(inst.cell.name.split("$")[0], inst.dbbox()) for inst in ly.top_cell().each_inst()]
names = {n for n, _ in boxes}
db = pya.ReportDatabase(""); db.load(rdb)
per = collections.defaultdict(collections.Counter)
for item in db.each_item():
    cat = db.category_by_id(item.category_id())
    if "coverage over the entire die" in cat.description:
        continue                                   # whole-die density rules: meaningless for a gallery
    # deep-mode DRC reports markers in the coordinate frame of the cell they were found in,
    # so attribute by the marker's cell, not by position
    cell = db.cell_by_id(item.cell_id()).name().split("$")[0]
    per[cell if cell in names else f"({cell})"][cat.name()] += 1
for name in sorted(names) + sorted(k for k in per if k.startswith("(")):
    c = per.get(name, collections.Counter())
    print(f"{'CLEAN' if not c else 'DIRTY'}  {name:26s} {sum(c.values()):4d}  " + ", ".join(f"{k}x{n}" for k, n in c.most_common(6)))
