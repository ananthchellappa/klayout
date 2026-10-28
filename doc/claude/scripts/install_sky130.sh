#!/bin/bash
# Install the sky130A PDK for KLayout (and Xschem) the way IIC-OSIC-TOOLS does:
# ciel at a pinned open_pdks commit + KLayout tech/PCell patches + a dedicated venv.
# See doc/claude/sky130_pdk_plan.md for the reasoning and verification.
#
#   doc/claude/scripts/install_sky130.sh            # installs into ~/pdk
#   PDK_ROOT=/elsewhere doc/claude/scripts/install_sky130.sh
#
# Afterwards:  source ~/pdk/sky130A.env && klayout -e

set -euo pipefail

PDK_ROOT=${PDK_ROOT:-$HOME/pdk}
OPEN_PDKS_COMMIT=${OPEN_PDKS_COMMIT:-1689ac3f2dc763876eaf967227c7dfe831b031ae}
LIBS=${LIBS:-sky130_fd_pr}               # add sky130_fd_sc_hd for digital/mixed-signal
VENV=$PDK_ROOT/.venv
HERE=$(cd "$(dirname "$0")" && pwd)

mkdir -p "$PDK_ROOT"

echo "[INFO] venv with ciel + pinned gdsfactory/kfactory: $VENV"
[ -x "$VENV/bin/python" ] || python3 -m venv "$VENV"
TMPDIR=$PDK_ROOT "$VENV/bin/pip" install --no-cache-dir --upgrade \
    ciel gdsfactory==9.51.0 kfactory==3.0.4

echo "[INFO] ciel enable sky130 $OPEN_PDKS_COMMIT ($LIBS)"
lib_args=()
for l in $LIBS; do lib_args+=(-l "$l"); done
"$VENV/bin/ciel" enable --pdk-root "$PDK_ROOT" --pdk-family sky130 "${lib_args[@]}" "$OPEN_PDKS_COMMIT"

echo "[INFO] removing sky130B"
rm -rf "$PDK_ROOT"/ciel/sky130/versions/*/sky130B "$PDK_ROOT/sky130B"
[ -d "$PDK_ROOT/sky130A" ] || { echo "[ERROR] $PDK_ROOT/sky130A missing after ciel enable"; exit 1; }

echo "[INFO] patching KLayout tech + PCells"
python3 -I "$HERE/patch_sky130_klayout.py" "$PDK_ROOT/sky130A/libs.tech/klayout"

SITE=$(ls -d "$VENV"/lib/python3*/site-packages)
cat > "$PDK_ROOT/sky130A.env" <<EOF
# source this before starting KLayout for sky130 work
export PDK_ROOT=$PDK_ROOT
export PDK=sky130A
export KLAYOUT_PATH=\$PDK_ROOT/\$PDK/libs.tech/klayout
# KLayout's embedded Python ignores PYTHONPATH; it reads KLAYOUT_PYTHONPATH
export KLAYOUT_PYTHONPATH=$SITE
EOF

echo "[INFO] done. Use:  source $PDK_ROOT/sky130A.env && klayout -e"
