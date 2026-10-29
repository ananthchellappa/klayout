#!/bin/bash
# Acceptance checks for the gf180mcuD install (doc/claude/scripts/install_gf180.sh).
#   source ~/pdk/gf180mcuD.env && doc/claude/scripts/gf180_verify/run.sh [outdir]
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
KLAYOUT=${KLAYOUT:-$HOME/dev/klayout/bin-release/klayout}
# Hard caps: a broken PCell once ate 12 GB, and KLayout ignores SIGTERM while in Python.
# RAM is capped with a cgroup (ulimit -v breaks the multi-threaded DRC, which reserves
# lots of address space it never touches).
KL () {
  systemd-run --user --scope -q -p MemoryMax=${KL_MEM:-6G} -p MemorySwapMax=0 \
    timeout -s KILL ${KL_TIMEOUT:-900} "$KLAYOUT" "$@"
}
OUT=${1:-$HOME/tmp/gf180-verify}
KT=$PDK_ROOT/$PDK/libs.tech/klayout
mkdir -p "$OUT"
export QT_QPA_PLATFORM=offscreen
count_items () { python3 -I -c 'import sys,re; print(len(re.findall(r"<item>",open(sys.argv[1]).read())))' "$1"; }

echo "== 1. every PCell at defaults"
KL -zz -rd out="$OUT/pcells.gds" -r "$HERE/pcells.py" 2>&1 | grep -v '^## ' | tee "$OUT/pcells.log"

echo "== 2. DRC: single nfet, then the whole device gallery"
KL -zz -rd nf=1 -rd out="$OUT/nfet1.gds" -r "$HERE/nfet1.py"
KL -b -r "$KT/drc/gf180mcu.drc" -rd input="$OUT/nfet1.gds" -rd report="$OUT/nfet1_drc.lyrdb" \
    -rd run_mode=deep > "$OUT/drc_nfet1.log" 2>&1 || { tail -20 "$OUT/drc_nfet1.log"; exit 1; }
echo "nfet1 DRC violations: $(count_items "$OUT/nfet1_drc.lyrdb")"
KL -b -r "$KT/drc/gf180mcu.drc" -rd input="$OUT/pcells.gds" -rd report="$OUT/pcells_drc.lyrdb" \
    -rd run_mode=deep > "$OUT/drc_pcells.log" 2>&1 || { tail -20 "$OUT/drc_pcells.log"; exit 1; }
echo "gallery DRC violations: $(count_items "$OUT/pcells_drc.lyrdb")"

echo "== 3. LVS: nfet1 vs Xschem-style netlist"
KL -b -r "$KT/lvs/gf180mcu.lvs" -rd input="$OUT/nfet1.gds" -rd schematic="$HERE/nfet1.spice" \
    -rd schematic_translate=true -rd report="$OUT/nfet1.lvsdb" -rd target_netlist="$OUT/nfet1_extracted.cir" \
    > "$OUT/lvs.log" 2>&1 || true
grep -q 'Netlists match' "$OUT/lvs.log" && echo "LVS match" || { echo "LVS MISMATCH"; exit 1; }
echo "-- extracted:"; grep -vE '^\s*\*|^\s*$' "$OUT/nfet1_extracted.cir" 2>/dev/null || echo "(none)"

echo "== 4. 2-finger nfet extraction (to check W total vs per finger)"
KL -zz -rd nf=2 -rd out="$OUT/nfet2.gds" -r "$HERE/nfet1.py"
KL -b -r "$KT/lvs/gf180mcu.lvs" -rd input="$OUT/nfet2.gds" -rd schematic="$HERE/nfet1.spice" \
    -rd schematic_translate=true -rd report="$OUT/nfet2.lvsdb" -rd target_netlist="$OUT/nfet2_extracted.cir" \
    > "$OUT/lvs2.log" 2>&1 || true
grep -E '^M|^X' "$OUT/nfet2_extracted.cir" 2>/dev/null || echo "(none)"
echo "== 5. analog device set (bulk ties, guard rings, MIM-B on M5, poly resistors): DRC per device + extraction"
KL -zz -rd out="$OUT/analog.gds" -r "$HERE/analog_set.py" 2>&1 | grep -v '^## '
KL -b -r "$KT/drc/gf180mcu.drc" -rd input="$OUT/analog.gds" -rd report="$OUT/analog_drc.lyrdb" \
    -rd run_mode=deep > "$OUT/drc_analog.log" 2>&1 || { tail -20 "$OUT/drc_analog.log"; exit 1; }
KL -zz -rd gds="$OUT/analog.gds" -rd rdb="$OUT/analog_drc.lyrdb" -r "$HERE/drc_by_device.py" 2>&1 | grep -v '^## '
KL -b -r "$KT/lvs/gf180mcu.lvs" -rd input="$OUT/analog.gds" -rd schematic="$HERE/nfet1.spice" \
    -rd schematic_translate=true -rd report="$OUT/analog.lvsdb" -rd target_netlist="$OUT/analog_extracted.cir" \
    > "$OUT/lvs_analog.log" 2>&1 || true
grep -E '^[MRC]' "$OUT/analog_extracted.cir"
echo "done: $OUT"
