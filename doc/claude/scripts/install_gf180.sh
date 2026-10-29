#!/bin/bash
# Install the gf180mcuD PDK for KLayout: only the KLayout parts, about 5 MB.
#
# Fetches the KLayout tech files, PCells, DRC and LVS decks from the two
# GlobalFoundries repos (sparse git checkouts at pinned commits) and arranges
# them the way open_pdks does (libs.tech/klayout/{tech,pymacros,macros,drc,lvs}).
# Uses the gf180mcu_klayoutapi PCell library, which needs no gdsfactory and no venv.
# Skips ciel on purpose: its gf180mcu "common" package is a 318 MB download.
#
#   doc/claude/scripts/install_gf180.sh             # installs into ~/pdk
#   PDK_ROOT=/elsewhere doc/claude/scripts/install_gf180.sh
#
# Afterwards:  source ~/pdk/gf180mcuD.env && klayout -e

set -euo pipefail

PDK_ROOT=${PDK_ROOT:-$HOME/pdk}
PDK=gf180mcuD
PR_COMMIT=${PR_COMMIT:-5e4be8726e2ae8be099c4131f697a353d6457874}   # 2026-10-19
PV_COMMIT=${PV_COMMIT:-a561909c667ce1e8485313f5d280a7014f524e49}   # 2026-10-17
PR_URL=https://github.com/fossi-foundation/globalfoundries-pdk-libs-gf180mcu_fd_pr.git
PV_URL=https://github.com/fossi-foundation/globalfoundries-pdk-libs-gf180mcu_fd_pv.git
KLAYOUT_BIN=${KLAYOUT_BIN:-$(cd "$(dirname "$0")/../../.." && pwd)/bin-release}

SRC=$PDK_ROOT/src/gf180mcu
DEST=$PDK_ROOT/$PDK/libs.tech/klayout

# sparse_fetch <url> <commit> <dir> <sparse patterns...>
sparse_fetch () {
  local url=$1 commit=$2 dir=$3; shift 3
  if [ ! -d "$dir/.git" ]; then
    git clone -q --filter=blob:none --no-checkout "$url" "$dir"
  fi
  git -C "$dir" sparse-checkout set --no-cone "$@"
  git -C "$dir" fetch -q --depth 1 origin "$commit"
  git -C "$dir" checkout -q "$commit"
}

echo "[INFO] fetching gf180mcu_fd_pr @ ${PR_COMMIT:0:10}"
sparse_fetch "$PR_URL" "$PR_COMMIT" "$SRC/pr" \
  '/tech/klayout/' '/cells/klayout/' '/rules/klayout/' '/LICENSE' \
  '!/cells/klayout/pymacros/testing/'
echo "[INFO] fetching gf180mcu_fd_pv @ ${PV_COMMIT:0:10}"
sparse_fetch "$PV_URL" "$PV_COMMIT" "$SRC/pv" \
  '/klayout/' '/LICENSE' '!/klayout/*/testing/'

echo "[INFO] assembling $DEST"
rm -rf "$DEST"
mkdir -p "$DEST"/{tech,pymacros,macros,drc,lvs,scripts}
cp -a "$SRC/pr/tech/klayout/."            "$DEST/tech/"
cp -a "$SRC/pr/cells/klayout/pymacros/."  "$DEST/pymacros/"
cp -a "$SRC/pr/cells/klayout/scripts/."   "$DEST/scripts/"
cp -a "$SRC/pr/rules/klayout/macros/."    "$DEST/macros/"
cp -a "$SRC/pv/klayout/drc/."             "$DEST/drc/"
cp -a "$SRC/pv/klayout/lvs/."             "$DEST/lvs/"
cp "$SRC/pr/LICENSE" "$DEST/LICENSE"
# pymacros/cells is the gdsfactory PCell library ("gf180mcu"). Without gdsfactory
# it fails to load and KLayout logs one warning; gf180mcu_klayoutapi covers the devices.
printf '%s\n%s\n' "gf180mcu_fd_pr $PR_COMMIT" "gf180mcu_fd_pv $PV_COMMIT" > "$DEST/VERSIONS"

cat > "$PDK_ROOT/$PDK.env" <<EOF
# source this before starting KLayout for gf180mcuD work
export PDK_ROOT=$PDK_ROOT
export PDK=$PDK
export GF_PDK_OPTION=D
export KLAYOUT_PATH=\$PDK_ROOT/\$PDK/libs.tech/klayout
# the PDK's DRC/LVS menu entries run "klayout -b" from PATH
export PATH=$KLAYOUT_BIN:\$PATH
EOF

du -sh "$DEST"
echo "[INFO] done. Use:  source $PDK_ROOT/$PDK.env && klayout -e"
