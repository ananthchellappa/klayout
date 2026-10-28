# sky130 in KLayout: what people use, what we verified, how we install

2026-10-27. Supersedes the earlier "research only" version of this file.

## What working KLayout + sky130 users actually run

The reference setup is **IIC-OSIC-TOOLS** (JKU's all-in-one Docker image, widely used for open-source analog design). Its PDK install script (`_build/images/open_pdks/scripts/install_ciel.sh`) does this:

1. `pip install ciel`, then `ciel enable <open_pdks commit> --pdk sky130`. The pinned commit is `1689ac3f2dc763876eaf967227c7dfe831b031ae`; a ciel release of it was published 2026-08-27.
2. It deletes `sky130B`.
3. It **patches the KLayout tech file**. open_pdks still ships the generic `sky130` tech name, a `sky130.lyp` reference, and the build machine's absolute `<base-path>`. Per their comment, this is still needed as of 2026-08-06.
4. It **patches the sky130 PCells** for current gdsfactory/kfactory:
   - `operation="A-B"` → `"-"`;
   - `pdk.py` uses removed kfactory 0.x internals (`_get_default_kcl`, `_kdb_cell`), and kfactory ≥1 locks cells that `scale_and_snap` must modify;
   - a shim for `Component.add_array`, which gdsfactory 9 removed;
   - generic-PDK activation, since gdsfactory ≥9.29 no longer auto-activates it.
5. It builds **KLayout v0.30.12**, the same version as our build, with gdsfactory installed system-wide.

So the sky130 PCells *are* usable, but only with these patches. Upstream open_pdks is broken out of the box with current gdsfactory, which is why naive installs fail. That explains the mixed reports online.

## What I verified on our build

The trial is in `~/tmp/sky130-trial` and can be deleted. It used the ciel `sky130-ff08c23d` common + fd_pr tarballs, IIC's patches re-implemented, a venv with gdsfactory 9.51.0 / kfactory 3.0.4, and our `bin-release/klayout` 0.30.12.

| Check | Result |
|---|---|
| PCell library loads | `skywater130` with 18 PCells: nfet, pfet, res_poly/diff/metal, mim_cap, cap_var, cap_vpp, diodes, BJTs, rf_*, vias_gen, guard_ring_gen |
| Instantiate from script | nfet, pfet, res_poly, mim_cap, vias_gen, guard_ring_gen all OK, ~0.01–0.04 s each |
| DRC (`drc/sky130A_mr.drc -rd feol=true -rd beol=true -rd offgrid=true`) | 256 rule categories ran, **0 violations** on nfets |
| LVS (`lvs/sky130.lvs`) vs a hand-written Xschem-style netlist | **Match**, with `-rd convert_subckts=true -rd scale=true` |

What we learned the hard way:

- **KLayout ignores `PYTHONPATH`.** Use **`KLAYOUT_PYTHONPATH`** (`src/pya/pya/pya.cc:208`) to point at the venv's site-packages.
- **The PCell library is named `skywater130`**, not "sky130".
- **PCell `w` is per-finger width; Xschem `W` is total width.** The symbol's AD/AS formulas use `W/nf`. So the mapping is `w = W/nf`, `l = L`, `nf = nf`.
- **Set the choice parameters explicitly** (`gate_con_pos`: top/bottom/alternating; `bulk`: None/"bulk tie"/"guard ring"). Through the script API they otherwise arrive as `None`, the same problem IIC reports for gf180.
- **Multi-finger PCells don't strap the fingers.** Each finger gets its own gate contact, and S/D/G must be routed, so an nf=4 device extracts as 4 devices until it's wired. This is fine for hand layout. Our generator (Phase 2) must add straps, or we'll eventually want our own PCell.
- **LVS switches for Xschem netlists:**
  - `convert_subckts=true`, because Xschem writes `XM1 … sky130_fd_pr__nfet_01v8`, which is a subckt call;
  - `scale=true`, because Xschem writes micrometres without units;
  - the substrate net is `sky130_gnd` (configurable with `-rd lvs_sub=`).
- **The default `drc/sky130A.lydrc` has FEOL checks off.** Use `sky130A_mr.drc` with explicit switches.
- **`~/.klayout` is always on the search path.** `KLAYOUT_PATH` only adds to it (`src/lay/lay/laySystemPaths.cc`), so personal init macros (background, key bindings) coexist with the PDK.

## Options considered

| Option | Verdict |
|---|---|
| IIC-OSIC-TOOLS Docker image | Proven, but a large image with its own KLayout. We're hacking our own KLayout build, so we'd fight two installs. **Reuse its recipe, not the image.** |
| KLayout Salt package "Efabless_sky130" | Same Mabrains PCells, unpatched, so it breaks with current gdsfactory. No DRC/LVS pinning. **No.** |
| Plain open_pdks / ciel without patches | PCells don't load with current gdsfactory. **No.** |
| **ciel at IIC's pinned commit + IIC patches + a dedicated venv** | Matches what's known to work, keeps the PDK reproducible and pinned, keeps system Python clean, and uses our KLayout. **Chosen.** |

## Decision: how we install

- **PDK_ROOT = `~/pdk`.** Treat it as read-only vendor data, like a Cadence PDK install.
- **open_pdks commit `1689ac3f`**, the one IIC-OSIC-TOOLS pins and has tested with KLayout 0.30.12.
- **Libraries: `sky130_fd_pr`** only (plus the common files), about 21 MB to download. Add `sky130_fd_sc_hd` (127 MB) later if we go mixed-signal.
- **A dedicated venv at `~/pdk/.venv`** with ciel and **pinned** gdsfactory 9.51.0 / kfactory 3.0.4, the versions verified above. It's exposed to KLayout through `KLAYOUT_PYTHONPATH`. No `--break-system-packages`.
- **Our own idempotent patch script**, carrying IIC's patches. It fails loudly if a pattern isn't found, so we notice when upstream fixes or changes something.
- **One env file**, `~/pdk/sky130A.env`, that sets `PDK_ROOT`, `PDK`, `KLAYOUT_PATH` and `KLAYOUT_PYTHONPATH`. It's sourced by our launch scripts, not by `~/.bashrc`, so it doesn't affect other projects.
- Script: `doc/claude/scripts/install_sky130.sh`. Written, **not yet run**.

Disk cost: about 105 MB for the PDK (sky130A only) and about 0.8 GB for the venv. The pip `klayout` wheel inside the venv is unused by the app, which loads its own `klayout` module first (verified).

## How this fits the one-library / lib-cell-view vision

The PDK stays vendor-pristine under `~/pdk`, as in Cadence: you never edit the PDK, you reference it. The "one library" lives in our workarea:

```
<workarea>/library.defs                     # shared registry (exists today for Xschem)
<workarea>/sky130_fd_pr/nfet_01v8/symbol/nfet_01v8.sym       # exists today
<workarea>/sky130_fd_pr/nfet_01v8/layout/pcell.json          # NEW: {"lib":"skywater130","pcell":"nfet",
                                                             #  "map":{"w":"@W/@nf","l":"@L","nf":"@nf"},
                                                             #  "fixed":{"gate_con_pos":"top","bulk":"bulk tie"}}
<workarea>/<userlib>/<cell>/{symbol,schematic,layout}/…     # user cells: layout/<cell>.oas
```

- The `pcell.json` files are the single place where the Xschem→PCell parameter mapping lives, including the `w = W/nf` rule and the explicit choice parameters learned above.
- The KLayout-side lib/cell/view loader (planned) reads `library.defs` and `pcell.json`, and is what the Phase 2 generator and the cross-probe use.
- If we later write our own PCells (to strap fingers, or drop gdsfactory), only `pcell.json` changes.

## Next steps (on approval)

1. Run `install_sky130.sh`, then re-run the trial checks (PCells load, DRC clean, LVS match) against `~/pdk`.
2. Delete `~/tmp/sky130-trial`.
3. Phase 0 inverter: Xschem LVS netlist → place PCells → route → `sky130.lvs` (with the switches above) → `.lvsdb` in the netlist browser.
4. Check which open_pdks version `xschem-claude/sky130A`'s symbols and models came from. If it differs from `1689ac3f`, decide whether to re-vendor the models from `~/pdk`.
