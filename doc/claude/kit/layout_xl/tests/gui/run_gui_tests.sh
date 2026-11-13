#!/bin/bash
# Runs the Layout XL GUI tests in hidden-window KLayout (-z -e, offscreen), with an
# isolated KLAYOUT_HOME that holds only the layout_xl package, under a memory cap.
#   doc/claude/kit/layout_xl/tests/gui/run_gui_tests.sh
# Needs: the gf180mcuD PDK (~/pdk/gf180mcuD.env), voice/setup.sh run, and the
# read-aloud recordings from listen.py --test (LAYOUT_XL_VOICE_TEST=<stamp>).
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
KIT=$(cd "$HERE/../../.." && pwd)
REPO=$(cd "$KIT/../../.." && pwd)
KL=${KLAYOUT_REAL:-$REPO/bin-release/klayout}
DATA=${LAYOUT_XL_DATA:-$HOME/.local/share/layout-xl}
REC=$DATA/voice-test/${LAYOUT_XL_VOICE_TEST:-20261103-105938}
source ~/pdk/gf180mcuD.env
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/home/salt"
ln -s "$KIT/layout_xl" "$TMP/home/salt/layout_xl"

run() {   # name, then env assignments
  local t=$1; shift
  echo "=== $t"
  local out
  out=$(cd "$HERE" && env KLAYOUT_HOME="$TMP/home" QT_QPA_PLATFORM=offscreen "$@" \
    systemd-run --user --scope -q -p MemoryMax=4G timeout 120 "$KL" -z -e -r "$HERE/$t" 2>&1 | grep -v '^##')
  echo "$out"
  # pass only on the test's own verdict: a script error or a hang never prints it
  grep -q '^RESULT: PASS' <<<"$out"
}

fail=0
run test_palette.py LAYOUT_XL_DATA=/nonexistent || fail=1
run test_voice_missing.py LAYOUT_XL_DATA=/nonexistent || fail=1
run test_voice.py LAYOUT_XL_VOICE_WAV="$REC-04.wav:$REC-07.wav:$KIT/layout_xl/voice_helper/rec01.wav:$REC-12.wav" || fail=1
echo; [ $fail = 0 ] && echo "ALL GUI TESTS PASSED" || echo "SOME GUI TESTS FAILED"
exit $fail
