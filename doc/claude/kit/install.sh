#!/bin/bash
# Layout-XL kit installer: gf180mcuD PDK for KLayout, the Cadence-style startup package,
# and a "klayout" command that runs this repo's build under a RAM cap.
#
#   doc/claude/kit/install.sh
#   source ~/pdk/gf180mcuD.env && klayout -e
#
# Everything is linked (not copied), so pulling the repo updates it. Remove with:
#   rm ~/.klayout/salt/layout_xl ~/.local/bin/klayout
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
KLAYOUT_HOME=${KLAYOUT_HOME:-$HOME/.klayout}

# the PDK env puts the capped launcher (not the raw binary) on PATH
KLAYOUT_BIN="$HERE/bin" "$HERE/../scripts/install_gf180.sh"

mkdir -p "$KLAYOUT_HOME/salt"
ln -sfn "$HERE/layout_xl" "$KLAYOUT_HOME/salt/layout_xl"
echo "[INFO] startup package linked: $KLAYOUT_HOME/salt/layout_xl -> $HERE/layout_xl"

mkdir -p "$HOME/.local/bin"
ln -sfn "$HERE/bin/klayout" "$HOME/.local/bin/klayout"
echo "[INFO] capped launcher linked: $HOME/.local/bin/klayout -> $HERE/bin/klayout"
echo "[INFO] done. Use:  source ${PDK_ROOT:-$HOME/pdk}/gf180mcuD.env && klayout -e"
