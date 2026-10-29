#!/bin/bash
# Layout-XL kit installer: gf180mcuD PDK for KLayout + the Cadence-style startup package.
#
#   doc/claude/kit/install.sh
#   source ~/pdk/gf180mcuD.env && klayout -e
#
# The startup package is linked (not copied) into ~/.klayout/salt, so pulling the repo
# updates it. Remove it with: rm ~/.klayout/salt/layout_xl
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
KLAYOUT_HOME=${KLAYOUT_HOME:-$HOME/.klayout}

"$HERE/../scripts/install_gf180.sh"

mkdir -p "$KLAYOUT_HOME/salt"
ln -sfn "$HERE/layout_xl" "$KLAYOUT_HOME/salt/layout_xl"
echo "[INFO] startup package linked: $KLAYOUT_HOME/salt/layout_xl -> $HERE/layout_xl"
echo "[INFO] done. Use:  source ${PDK_ROOT:-$HOME/pdk}/gf180mcuD.env && klayout -e"
