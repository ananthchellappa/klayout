# gf180mcuD for KLayout: install and verification

Decided 2026-10-29: gf180mcuD is the working PDK for now. sky130A (`sky130_pdk_plan.md`, WO-001) stays as the fallback.

## Why gf180mcuD

- **Small:** the KLayout parts are about 2 MB (7 MB including git data). ciel isn't used, because its gf180mcu `common` package is a 318 MB download.
- **No gdsfactory:** the PDK ships a second PCell library, `gf180mcu_klayoutapi`, written directly against the KLayout API. sky130's PCells need gdsfactory, a 0.8 GB venv and patches. Unpatched, they silently produce empty cells.
- **Built for our flow:** the LVS deck has an Xschem netlist translation (`-rd schematic_translate=true`, plus `lvs/gf180_xschem_klayout_spice_convert.py`).
- **Maintained:** both upstream repos had commits in October 2026.
- **Xschem side** already exists in `~/dev/xschem-claude/gf180mcuD`.

## Install

```sh
doc/claude/scripts/install_gf180.sh          # into ~/pdk; PDK_ROOT=... to change
source ~/pdk/gf180mcuD.env && klayout -e
```

- **Pinned sources:** sparse checkouts in `~/pdk/src/gf180mcu/{pr,pv}` of `fossi-foundation/globalfoundries-pdk-libs-gf180mcu_fd_pr` @ `5e4be872` and `..._fd_pv` @ `a561909c`.
- **Assembled tree:** `~/pdk/gf180mcuD/libs.tech/klayout/{tech,pymacros,macros,drc,lvs}`, in the open_pdks layout.
- **The env file** sets:
  - `GF_PDK_OPTION=D`;
  - `KLAYOUT_PATH`;
  - `PATH` to include `bin-release`, because the PDK's DRC/LVS menu entries run `klayout -b` from PATH.
- **Our fixes to the PDK** are applied by `doc/claude/scripts/patch_gf180.py` to the assembled tree; the pinned sources stay untouched.
- **The gdsfactory PCell library (`gf180mcu`) is skipped.** The installer patches the PDK's `pymacros/gf180mcu.lym` so that, without gdsfactory, it skips that library and prints a notice at every start instead of an error-like warning. See "The gdsfactory library" below.

## The deep n-well diode memory blow-up (fixed by our patch)

- **Cause:** at their defaults (w = 0.22, l = 0.36 µm), `diode_pw2dw` and `diode_dw2ps` compute contact rows of negative length. `number_spc_contacts()` then returns −1, `pya.CellInstArray` takes the count as unsigned (−1 → 2⁶⁴ − 1), and `Cell.flatten` tries to make that many contacts. This took WSL down at 12 GB.
- **Not only the diodes:** the same `int(...)` count is used in `draw_res.py`, `draw_cap_mim.py`, `draw_cap_mos.py`, `draw_fet.py` and `draw_mos.py`. Their defaults are fine, but a too-small value typed into a form could trigger it.
- **Our patch:**
  1. clamps all 26 counts at 0, so a too-small device draws without contacts and DRC flags it;
  2. raises the two diodes' defaults and form minimums to 3 × 3 µm.
- **Why 3 × 3:** every contact row exists from 1.62 × 0.68 (`pw2dw`) and 2.62 × 1.68 (`dw2ps`), but below 3 µm DRC is clean only at some sizes, and not monotonically. From 3 to 10 µm, all 324 sizes tested (9 × 9 w/l values, both voltages, both diodes) are DRC-clean.
- **Upstream:** reported as [fd_pr #51](https://github.com/fossi-foundation/globalfoundries-pdk-libs-gf180mcu_fd_pr/issues/51) (text in `doc/claude/upstream/`). Once fixed upstream, bump `PR_COMMIT` and drop the matching parts of `patch_gf180.py`; its checks fail loudly when the upstream text changes.
- **Safety net:** the kit's `klayout` launcher (`doc/claude/kit/bin/klayout`) runs the GUI under a 10 GiB cgroup cap (`KLAYOUT_MEM` to change), so any future runaway kills KLayout, not WSL. Jobs that KLayout starts, such as the DRC/LVS menu runs, share that cap.

## The gdsfactory library

The PDK ships two device PCell libraries. Compared by registered PCell names (pinned `fd_pr` commit):

| | `gf180mcu_klayoutapi` (used) | `gf180mcu` (gdsfactory, skipped) |
|---|---|---|
| PCells | 31 | 29 |
| Only here | `efuse`, `nfet_10v0_asym`, `pfet_10v0_asym` | `via_dev` (via stack) |

So skipping it gives up only `via_dev`. That matters for the via rows/columns bindkeys in WO-008.

**To get it back** (untested): install `gdsfactory~=7.9.4`, the version pinned in the PDK's `requirements.txt`, for the Python that KLayout embeds (3.14 in this build), then restart KLayout. The patched macro loads the library whenever `gdsfactory` is importable. Version 7.9 predates Python 3.14 and pulls in many dependencies, so it may not install cleanly. The alternative is to port `via_dev` to the KLayout API.

## Verification (`doc/claude/scripts/gf180_verify/run.sh`, all passing 2026-10-29)

| Check | Result |
|---|---|
| All 31 PCells at defaults | 30 produce geometry. `efuse` raises TypeError upstream and is skipped. `diode_pw2dw` and `diode_dw2ps` used to exhaust memory; our patch fixes them (see below). |
| DRC, single nfet with bulk tie | Clean, apart from 6 whole-die density rules that a test cell can't meet |
| LVS, single nfet vs Xschem-format netlist | **Netlists match** |
| DRC per device, analog set: nfet/pfet with bulk tie, nf=4 with guard ring, MIM-B 10×10 on M5, `ppolyf_u`, high-R poly, both deep n-well diodes at their (patched) 3×3 default | **All clean** |
| Extraction | nfet/pfet_03v3 with the drawn W/L; MIM 100 µm² → 0.2 pF `cap_mim_2f0fF`; `ppolyf_u`, `ppolyf_u_1k` |

Every KLayout call in the checks runs under a cgroup RAM cap (`systemd-run --user --scope -p MemoryMax=6G`) and `timeout -s KILL`. `ulimit -v` can't be used: it breaks the multi-threaded DRC.

## Quirks to design around

1. **MOS `w` is per finger.** nf=2, w=1 extracts as two devices of W=1. Xschem's `W` is the total (its symbol uses `W/nf`), so map PCell `w = W/nf`.
2. **Multi-finger MOS fingers aren't strapped.** nf=4 extracts as 4 transistors with separate gates and chained source/drain. To match one Xschem device with nf=4, the fingers must be wired, either by us or by a strapping option. This is the same as sky130.
3. **Resistor `l`/`w` are swapped:**
   - parameter `w` is labelled "Length" and is the physical length; `l` is labelled "Width";
   - the GUI form is right, but scripts pass length as `w`.
4. **MOS default `bulk = None`** has no tap and fails the tap-distance rules (DF.13/DF.14). Use `Bulk Tie` or `Guard Ring`.
5. **MIM defaults to option A**, which is wrong for gf180mcuD. Use `mim_option = MIM-B`, `metal_level = M5`, since the MIM sits under the top metal of the 5-metal stack.
6. **Defaults of the n+/p+ diffusion resistors and the diodes** have off-grid vertices and small-area violations. Check them before use.
