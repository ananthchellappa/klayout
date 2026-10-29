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
- **One harmless startup warning:** the gdsfactory PCell library (`gf180mcu`) fails to load.

## Verification (`doc/claude/scripts/gf180_verify/run.sh`, all passing 2026-10-29)

| Check | Result |
|---|---|
| All 31 PCells at defaults | 28 produce geometry. **Broken upstream:** `diode_pw2dw` and `diode_dw2ps` exhaust memory in `Cell.flatten` (this took WSL down at 12 GB); `efuse` raises TypeError. All three are skipped. |
| DRC, single nfet with bulk tie | Clean, apart from 6 whole-die density rules that a test cell can't meet |
| LVS, single nfet vs Xschem-format netlist | **Netlists match** |
| DRC per device, analog set: nfet/pfet with bulk tie, nf=4 with guard ring, MIM-B 10×10 on M5, `ppolyf_u`, high-R poly | **All clean** |
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
