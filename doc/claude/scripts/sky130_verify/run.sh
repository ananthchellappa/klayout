#!/bin/bash
# Acceptance checks for the sky130A install (see doc/claude/work_orders/WO-001_sky130_install.md).
#   source ~/pdk/sky130A.env && doc/claude/scripts/sky130_verify/run.sh [outdir]
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
KL=${KLAYOUT:-$HOME/dev/klayout/bin-release/klayout}
OUT=${1:-$HOME/tmp/sky130-verify}
KT=$PDK_ROOT/$PDK/libs.tech/klayout
mkdir -p "$OUT"
export QT_QPA_PLATFORM=offscreen

echo "== 1. PCells"
"$KL" -zz -rd out="$OUT/pcells.gds" -r "$HERE/pcells.py" | tee "$OUT/pcells.log"
! grep -q '^ERR' "$OUT/pcells.log"

echo "== 2. single-finger nfet + DRC (FEOL/BEOL/offgrid on)"
"$KL" -zz -rd out="$OUT/nfet1.gds" -r "$HERE/nfet1.py"
"$KL" -b -r "$KT/drc/sky130A_mr.drc" -rd input="$OUT/nfet1.gds" -rd report="$OUT/nfet1_drc.lyrdb" \
    -rd feol=true -rd beol=true -rd offgrid=true > "$OUT/drc.log" 2>&1
python3 -I -c 'import sys,re; s=open(sys.argv[1]).read(); n=len(re.findall(r"<item>",s)); print("DRC violations:",n); sys.exit(n!=0)' "$OUT/nfet1_drc.lyrdb"

echo "== 3. LVS vs Xschem-style netlist"
"$KL" -b -r "$KT/lvs/sky130.lvs" -rd input="$OUT/nfet1.gds" -rd schematic="$HERE/nfet1.spice" \
    -rd report="$OUT/nfet1.lvsdb" -rd convert_subckts=true -rd scale=true > "$OUT/lvs.log" 2>&1
grep -q 'Congratulations! Netlists match' "$OUT/lvs.log" && echo "LVS match"
echo "ALL CHECKS PASSED  ($OUT)"
