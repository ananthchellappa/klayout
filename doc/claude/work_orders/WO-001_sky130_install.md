# WO-001: Install sky130A for KLayout (and verify it)

| | |
|---|---|
| Status | **Ready**: approved design, scripts written, not yet run |
| Written | 2026-10-27 |
| Background | `doc/claude/sky130_pdk_plan.md` (why this recipe; what was verified) |
| Effort | ~15 min wall clock, mostly downloads and pip |
| Touches | `~/pdk/` (new), `~/tmp/sky130-trial/` (delete). **No changes to the KLayout source tree** |

## Goal

Put a working, pinned sky130A PDK at `~/pdk` that our own KLayout build (`~/dev/klayout/bin-release/klayout`, 0.30.12) can use for layout, PCells, DRC and LVS. It must pass the acceptance checks below, and the throwaway trial setup must then be removed.

## Context the implementer needs

- The recipe is ported from IIC-OSIC-TOOLS: ciel at open_pdks commit `1689ac3f2dc763876eaf967227c7dfe831b031ae`, plus patches to the KLayout tech file and PCells. **Unpatched, every PCell silently produces an empty cell** (`AttributeError: module 'kfactory.kcell' has no attribute '_get_default_kcl'`).
- gdsfactory/kfactory live in a dedicated venv (`~/pdk/.venv`), pinned to **gdsfactory 9.51.0 / kfactory 3.0.4**. Those are the versions that were tested; don't upgrade them as part of this work order.
- KLayout's embedded Python **ignores `PYTHONPATH`**. The venv is exposed through `KLAYOUT_PYTHONPATH`, which the generated env file sets.
- The PCell library is named **`skywater130`**.
- `/tmp` is a 7.7 GB RAM disk shared with other sessions. The installer sets `TMPDIR=$PDK_ROOT` for pip. Don't put large things in `/tmp`, and don't delete other sessions' files there.
- Don't add anything to `~/.bashrc`. The env file is sourced explicitly.

## Files (already in the repo)

| File | Role |
|---|---|
| `doc/claude/scripts/install_sky130.sh` | Creates the venv, runs `ciel enable` (sky130_fd_pr only), deletes sky130B, patches, writes `~/pdk/sky130A.env` |
| `doc/claude/scripts/patch_sky130_klayout.py` | Idempotent patcher. Exits non-zero if an expected pattern is missing |
| `doc/claude/scripts/sky130_verify/run.sh` | Acceptance checks: PCells, DRC, LVS |
| `doc/claude/scripts/sky130_verify/{pcells.py,nfet1.py,nfet1.spice}` | Inputs for the checks |

`run.sh` was validated on 2026-10-27 against the trial copy. It passes on the patched PDK and fails (exit 1, `ERR` lines) on an unpatched one.

## Steps

1. **Preflight**
   - `df -h ~ /tmp`: about 1.5 GB free in `$HOME` is needed.
   - `ls ~/pdk`: stop and ask the user if it already exists and isn't from this work order.
   - `bin-release/klayout -v` should print `KLayout 0.30.12`.
2. **Install**: `doc/claude/scripts/install_sky130.sh`
   - Expect the patcher to print `patch sky130A.lyt`, `patch boolean ops in N file(s)`, `patch pdk.py` and `patch cells/__init__.py`.
   - If it reports `pattern not found`, the pinned commit's sources differ from what the patch expects. Stop and diff against `~/tmp/sky130-trial/raw/libs.tech/klayout/python/cells/pdk.py` (the release `ff08c23d` that was verified) **before** deleting the trial.
3. **Idempotency**: run `python3 -I doc/claude/scripts/patch_sky130_klayout.py ~/pdk/sky130A/libs.tech/klayout` again. Every line should say `skip`.
4. **Verify**: `source ~/pdk/sky130A.env && doc/claude/scripts/sky130_verify/run.sh ~/tmp/sky130-verify`
5. **GUI smoke test** (the user does this; it needs a display):
   - Run `source ~/pdk/sky130A.env && ~/dev/klayout/bin-release/klayout -e`.
   - Confirm `skywater130` appears in the Libraries panel.
   - Drag an `nfet` into a new layout; it should draw.
   - Check that the tech `sky130A` is selectable and the layers look right.
6. **Clean up**: once 4 passes, `rm -rf ~/tmp/sky130-trial ~/tmp/sky130-verify`. This is about 1 GB, mostly the trial venv.
7. **Record**:
   - Update `doc/claude/sky130_pdk_plan.md`: replace "Written, **not yet run**" with the install date, and note any deviations.
   - Update `doc/claude/TODO.md`: mark the sky130 PDK item done.
   - Set this work order's Status to Done, with the date and results.
   - Optionally update FAQ Q10 in `doc/claude/blog_klayout_faq.html`: the PCells work once patched.

## Acceptance criteria

- [ ] `~/pdk/sky130A/libs.tech/klayout/{tech,drc,lvs,pymacros,python}` exist; `~/pdk/sky130B` does not.
- [ ] `ciel ls --pdk-root ~/pdk --pdk-family sky130` (from the venv) shows `1689ac3f…` enabled.
- [ ] `run.sh` prints `ALL CHECKS PASSED` and exits 0:
  - 7 PCell instances, all `OK` with non-zero shape counts;
  - 0 DRC violations with `feol/beol/offgrid=true`;
  - LVS `Congratulations! Netlists match.`
- [ ] Running the patcher a second time is a no-op.
- [ ] Nothing was added to `~/.bashrc`, and no system `pip` installs were made.
- [ ] `~/tmp/sky130-trial` has been removed.

## Out of scope (separate work orders later)

- **WO-002, Phase 0 inverter.** Draw an inverter with Xschem → LVS netlist (`lvs_netlist=1`), place `skywater130` PCells in KLayout, route, run `sky130.lvs` with `convert_subckts=true scale=true`, and open the `.lvsdb` in the netlist browser. Mapping rules: `w = W/nf`; pass `gate_con_pos` and `bulk` explicitly; multi-finger PCells don't strap their fingers.
- **WO-003, cross-probe macro** (see `doc/claude/code_analysis/crossprobe_layout_xl.md` P0). Both TCP endpoints must stay on loopback, because Xschem's server evaluates any Tcl it receives.
- **WO-004, Cadence-style init macro**: black background, Virtuoso keymap (`doc/claude/TODO.md`).
- Adding `sky130_fd_sc_hd`: rerun with `LIBS="sky130_fd_pr sky130_fd_sc_hd"`.
- Checking which open_pdks version `~/dev/xschem-claude/sky130A`'s symbols and models came from.
- Evaluating kpex.
