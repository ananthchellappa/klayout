<!--
DRAFT for review, not yet posted.
Target: https://github.com/fossi-foundation/globalfoundries-pdk-libs-gf180mcu_fd_pr/issues/new
Post with:  gh issue create -R fossi-foundation/globalfoundries-pdk-libs-gf180mcu_fd_pr \
              --title "<title below>" --body-file <this file, without this comment>
Related but different: #2 is about the gdsfactory library (pymacros/cells); this is the KLayout-API one.
-->

**Title:** `diode_pw2dw` / `diode_dw2ps` (klayout_api_cells) exhaust all memory at default size: negative contact count becomes 2^64-1

## Summary

Placing `diode_pw2dw` or `diode_dw2ps` from the `gf180mcu_klayoutapi` library at its default parameters makes KLayout allocate memory until the OS kills it. On a 16 GB machine (WSL2) it took the whole VM down.

The cause is a negative contact count. At the default size (w = 0.22, l = 0.36 µm), `number_spc_contacts()` in `cells/klayout/pymacros/klayout_api_cells/draw_diode.py` returns −1 for some contact rows. `pya.CellInstArray` takes the counts as unsigned, so −1 becomes 18446744073709551615. The `flatten` that follows tries to create that many contacts.

Tested at commit `5e4be8726e2ae8be099c4131f697a353d6457874` with KLayout 0.30.12 and Python 3.14.

## Reproduction

Under a memory cap, so the machine survives:

```sh
cat > repro.py <<'EOF'
import pya
ly = pya.Layout(); ly.dbu = 0.001
ly.create_cell("diode_pw2dw", "gf180mcu_klayoutapi", {})   # defaults
print("done")
EOF
systemd-run --user --scope -p MemoryMax=2G klayout -zz -r repro.py   # killed or std::bad_alloc in Cell.flatten; never prints "done"
```

The unsigned conversion on its own:

```python
a = pya.CellInstArray(0, pya.Trans(), pya.Vector(470, 0), pya.Vector(0, 470), -1, 1)
print(a.na, a.size())   # 18446744073709551615 18446744073709551615
```

## Arithmetic (diode_pw2dw, w = 0.22 µm, 3.3V)

The top contact row has length

`w − 2·lvpwell_pcmp_enc − 2·cmp_w − 2·cont_spc_tol = 0.22 − 0.24 − 0.72 − 0.22 = −0.96 µm`

Then `number_spc_contacts`:

- `spc_cont = −0.96 − 2·0.07 = −1.10`
- `num_cont = int((−1.10 + 0.25) / (0.22 + 0.25)) = int(−1.81) = −1`

## Measured limits

Measured by scanning sizes, with the count clamped at 0 so small sizes can be generated, and running the PDK's own DRC deck (`gf180mcu.drc`, deep mode):

| Cell | All contact rows present from (w × l, µm) | DRC clean |
|---|---|---|
| `diode_pw2dw` | 1.54 × 0.60 (3.3V), 1.62 × 0.68 (5/6V) | Not monotonic below 3 µm: e.g. w = 3, l = 1.28 is clean but l = 1.38–1.58 fails PP.2/PP.8b. CO.1/CO.2a fail at the smallest sizes. |
| `diode_dw2ps` | 2.54 × 1.60 (3.3V), 2.62 × 1.68 (5/6V) | l < 1.7 fails DN.1. l = 1.7–2.4 fails CO.1/CO.2a/DF.10/DF.3a/M1.2a/NP.2/NP.8b, depending on size. |

At 3 × 3 µm and every w, l in {3, 3.25, 3.5, 4, 4.45, 5, 6.3, 7, 10}, both voltages (324 cells), both diodes are DRC-clean apart from the whole-die density rules.

## Suggested fix

1. **Raise the defaults and minimums** (`diode_pw2dw_l/_w`, `diode_dw2ps_l/_w` in `diode.py`, which `coerce_parameters_impl` also uses as minimums) to 3 µm, or to whatever size the maintainers know is clean.
2. **Clamp contact counts at 0** in `number_spc_contacts` (`draw_diode.py`, `draw_res.py`, `draw_cap_mim.py`, `draw_cap_mos.py`). Also clamp the single-line `nx`/`ny`/`nxgr` counts in `draw_fet.py` and `draw_mos.py`, which use the same pattern. A too-small value typed into a form then gives a DRC error instead of a runaway allocation.

We apply exactly these two changes in our installer as a patch; the script is at https://github.com/ananthchellappa/klayout/blob/d86b04ed1/doc/claude/scripts/patch_gf180.py. Happy to open a PR.

Separately, KLayout itself silently accepts a negative Python int as an unsigned array count. That may be worth raising with KLayout.
