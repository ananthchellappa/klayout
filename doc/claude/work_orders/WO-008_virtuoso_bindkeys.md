# WO-008: Virtuoso "Layout" bindkeys in KLayout

| | |
|---|---|
| Status | **Plan**. `f` (Zoom Fit) and Ctrl+F (hierarchy toggle) are done, in the kit startup file |
| Written | 2026-10-29 |
| Source | `bindkeys.il` in github.com/ananthchellappa/SKILL, plus the `.il` files it loads |
| Scope | 46 distinct "Layout" / "Virtuoso XL" bindings: 28 in `bindkeys.il`, 17 in loaded files, 1 Virtuoso XL. Schematic, ViVA and other-app bindings are out of scope. |
| Lives in | `doc/claude/kit/layout_xl/` (the startup package), no KLayout source changes |

## Design

- **One table, like `bindkeys.il`.** `layout_xl/bindkeys.py` maps a key to a command name. Users edit that table, not the code.
- **Every command is a menu action** in a new **Layout XL** menu, with the table key as its default shortcut. So every binding:
  - shows in File → Setup → Customize Menu;
  - can be rebound there;
  - follows the startup file's rule: applied only while still at the default.
- **Layer names go through an alias map per PDK,** so the SKILL names keep working. For gf180mcuD:
  - MET1–MET4 → Metal1–Metal4 (34/0, 36/0, 42/0, 46/0)
  - POLY → Poly2 (30/0)
  - PACT → COMP (22/0) + Pplus
  - TEXT → the `*_Label` layers
  - Vias → Contact and Via1–Via5

  This is the same alias file the voice plan uses (WO-007 §4.3).
- **The Layout XL menu runs commands by triggering its actions**, not through `MainWindow.call_menu`. Tested 2026-10-29: `call_menu` doesn't fire actions created from Python.

## Key conflicts to resolve

| Key | KLayout today | Resolution |
|---|---|---|
| Alt+V, Alt+T, Alt+H | Menu mnemonics: &View, &Tools, &Help | Drop the `&` from those menu titles in the startup file. Verify that Qt then delivers the shortcut (Step 0). |
| 0 | Display → Box Only (`max_hier_0`) | Taken by "unmark all nets"; Ctrl+F already covers Box Only |
| Ctrl+G | Display → Goto Position | Taken by toggle group; move Goto Position to Ctrl+Shift+G |
| F2 | Zoom Fit | Already moved to `f` |

8, 9, Ctrl+H, Ctrl+U, Ctrl+L, Ctrl+M, Ctrl+2 and Ctrl+Shift+B are free in KLayout's defaults (checked against `klayoutrc`).

## The bindings

Effort: **S** = built in or under an hour; **M** = a macro of a few hours; **L** = depends on other work.

### Phase 1: built in or small macros

| Key | Virtuoso function | KLayout plan | Effort |
|---|---|---|---|
| Ctrl+H | `_leRotateOrFlip("MY")`: flip horizontally | Built in: Edit → Selection → Flip Horizontally (`sel_flip_x`); bind it. Confirm the axis matches MY. | S |
| Ctrl+U | `_leRotateOrFlip("MX")`: flip vertically | Built in: `sel_flip_y` | S |
| Alt+1 … Alt+4 | toggle MET1…MET4 drawing visibility | Macro: find the aliased layer's `LayerPropertiesNode` in the current view and flip `visible` | S |
| Alt+P / Alt+A / Alt+T | toggle POLY / PACT / TEXT | Same macro, alias list | S |
| Alt+V | toggle Vias objects | Same macro over the via layer group | S |
| Alt+0 | toggle all layers visible | If any layer is visible, hide all; else show all | S |
| Ctrl+Shift+1/2/3 | save LSW settings to slot 1/2/3 | Save the layer properties (`view.save_layer_props`) to `~/.klayout/layout_xl/lsw<n>.lyp` | S |
| Ctrl+Alt+1/2/3 | load LSW slot 1/2/3 | `view.load_layer_props` from the slot | S |
| Ctrl+L | load `display.drf_pwrplot` from cwd | Load `pwrplot.lyp` from cwd (KLayout's equivalent of a display resource file) | S |
| Ctrl+Shift+B | load `display.drf_blink` | Load `blink.lyp` (KLayout layer properties support blinking). Ship sample `.lyp` files. | S |
| Ctrl+Alt+H | `selSimilar`: select all instances of the selected instance's master; with nothing selected, use the Library Manager selection | Macro: select all instances of the same cell in the current cell (`ObjectInstPath` list). With nothing selected, use the cell selected in the Cells panel. | M |
| Ctrl+Alt+X | `lxHiSwap`: swap two objects | Macro: swap the positions of two selected instances, as one undo step | S |
| Ctrl+Alt+V / Ctrl+Alt+Shift+H | `CCSAbutAlignInstances`: abut and align selected instances vertically / horizontally | Built in: Edit → Selection → **Distribute**, with Space = 0 and alignment. The macro calls it with preset values and no dialog. | M |
| Ctrl+G | `toggle_group`: ungroup if a group is selected, else group | Macro: one selected instance → Flatten Instances one level; otherwise Make Cell. KLayout has no figure groups, so a cell is the closest equivalent. | M |
| Ctrl+2 | `_leChangeEditMode("a")`: make the cellview editable | KLayout sets editable mode per session (`-e`). Macro: if the view is read-only, set `edit-mode` and reopen the layout. Warn about unsaved changes. | M |

### Phase 2: needs more design

| Key | Virtuoso function | KLayout plan | Effort |
|---|---|---|---|
| 9 / 8 / 0 | mark net / unmark net / unmark all | `pya.NetTracer` from the cursor point, using the tech's connectivity (the gf180 `.lyt` defines 6 connections), drawn as `pya.Marker`s in a highlight colour. Keep a per-view list of marked nets for unmark. | M |
| Alt+9 | toggle visibility of all Objects | KLayout has no Objects palette. Map it to: instance boxes (`inst-visible`), texts (`text-visible`), rulers. Agree the set with the user. | M |
| Ctrl+Shift+N | `openSelReadOnly`: open the selected instance's master (its schematic if it has one) read-only | Layout: open the master cell in a new tab (`edt::descend` variant, or a new view of the same layout with that top cell). Schematic: ask Xschem to open it (needs WO-003). | M |
| Ctrl+Alt+N | `CreateLibManSelInst`: place the cell selected in the Library Manager | Start the Instance tool with the cell selected in the Libraries/Cells panel | M |
| Ctrl+Alt+S / Alt+Shift+S | select the selected instance's master in the Library Manager (CCS / ICM variants) | Select its cell in the Cells panel (library cells: in the Libraries panel). KLayout has no Library Manager, so there is one KLayout command for both keys. | M |
| Alt+wheel | `inc_spc`: on paths, change width by ±10 % (grid-snapped); otherwise change spacing between the selected objects along their alignment direction | `pya.Plugin.wheel_event` with the Alt modifier. **Step 0:** check that wheel events reach a plugin that isn't the active tool. Fallback: Alt+PgUp/PgDn. | M |
| Ctrl+Shift+wheel, Ctrl+Alt+wheel, Ctrl+Alt+Shift+wheel | `CCSviaColRow`: add/remove via rows, columns, or both | Same wheel mechanism. Change the rows/columns parameters of a selected via PCell. gf180's `vias_gen` PCell is only in the gdsfactory library, so this needs a via PCell in `gf180mcu_klayoutapi` or our own. | L |
| Ctrl+Alt+D | `toglInstMstrDisplay`: instance labels show instance name or master name | GDS instances have no names. Once Generate-from-Xschem stores the instance name as a property, toggle between cell name and instance name in the instance box. Needs a custom label overlay. | L |

### Phase 3: Layout XL features (after "Generate from Xschem" and WO-003 cross-probe)

| Key | Virtuoso function | KLayout plan |
|---|---|---|
| Alt+X | `lxHiProbe`: probe, cross-highlight in the schematic | Cross-probe to Xschem over loopback TCP (WO-003) |
| Alt+H | raise the schematic window used as the XL source | Send Xschem a raise-window command over the same link |
| Ctrl+Shift+I | `lxHiCreateInstFromSch`: create layout for the devices selected in the schematic | Generate from Xschem, restricted to Xschem's current selection |
| Ctrl+M | `toglImportSplitRseg`: toggle importing resistors split into segments | An option of Generate from Xschem: resistor as one PCell or as N series segments, for interdigitation |

## Step 0 (half a day)

1. Alt+V/T/H: remove the mnemonics and confirm the shortcuts fire, including on WSLg.
2. Wheel events with modifiers: confirm a `pya.Plugin` gets them while another tool (Select, Box) is active.
3. Confirm `sel_flip_x` = Virtuoso MY.
4. NetTracer on a gf180 layout using the tech connectivity, from Python.

## Acceptance (Phase 1)

- [ ] Each Phase 1 key does its job on a gf180 layout and is one undo step where it edits.
- [ ] Every binding appears in the Layout XL menu and can be rebound in Setup. A rebinding survives restart.
- [ ] Changing a layer alias in the table (e.g. MET1 → another layer) works without code changes.
- [ ] Nothing in KLayout loses its only shortcut without a replacement listed in "Key conflicts".
