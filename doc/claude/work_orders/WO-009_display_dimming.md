# WO-009: Cadence-style display dimming

| | |
|---|---|
| Status | **Plan**, not started |
| Written | 2026-11-03 |
| Goal | Fade what you are not working on, so what you are working on stands out (Virtuoso "dimming") |
| Lives in | `doc/claude/kit/layout_xl/` (Phase 1, Python only); Phase 2 would change `src/laybasic` |

## What Virtuoso does

Everything outside the current focus is drawn dimmed, still visible as context:

- **Edit in Place:** the cell being edited stays bright.
- **Mark net / probe / cross-probe from the schematic:** the net's shapes stay bright.
- **Selection:** the selected objects stay bright.

The dimming amount is adjustable, and dimming switches on by itself in these situations. Exact form and menu names vary by Virtuoso version (from memory of IC6.1.x). Ask the user which modes they use; that sets the order of the work.

## What KLayout already has (checked in source, 0.30.12)

| Feature | Setting (klayoutrc) | Default | Where |
|---|---|---|---|
| **Context dimming:** Display → Descend (Ctrl+D) draws the parent cell dimmed around the cell you descended into; Ascend is Ctrl+A. This is the Edit in Place case. | `context-dimming` (percent), `context-color`, `context-hollow` | 50% | Setup → Background tab; `src/doc/doc/manual/descend.xml` |
| **Child-context dimming:** shapes in subcells drawn dimmed relative to the current cell's own shapes | `child-context-enabled`, `child-context-dimming`, `child-context-color`, `child-context-hollow` | off, 50% | `src/laybasic/laybasic/laybasicConfig.h:56-62` |
| **Per-layer brightness:** "Dark" / "Bright" in the layer colour panel | `LayerProperties` `fill_brightness=`, `frame_brightness=` | 0 | `src/laybasic/laybasic/gsiDeclLayLayers.cc:529,549` |

The renderer computes the dimmed colours at `src/laybasic/laybasic/layLayoutViewBase.cc` around line 4308 (`brightness_for_context`, `brightness_for_child_context`).

**Missing:** dim everything except a **net**, except the **selection**, or except the **current layer**, and one switch to turn dimming on and off.

## Phase 1: Python, in the kit

### 1. Dim to the current layer ("dim layers", for routing)

- Set fill and frame brightness on every layer except the current one. Use a negative value on a dark background and a positive one on a light background, as the renderer does.
- Save each layer's original brightness first and restore it when dimming goes off.
- Follow changes of the current layer: the layer view's current-layer event, or a check on the palette and voice layer commands.
- **Risk:** saving a session or `.lyp` file while dimmed stores the dimmed colours. Switch dimming off before File → Save Session / Save Layer Properties, by wrapping those menu actions or hooking the save, and restore afterwards.
- Layers added while dimmed (`commands._set_layer` adds missing ones) get dimmed or not to match.

### 2. Dim except the selection, and dim except a net

- Dim all layers as in 1, then draw the shapes to keep as **`pya.Marker`s** in their own layer's colour, frame colour and dither pattern (`color=`, `frame_color=`, `dither_pattern=`, `line_width=`; `gsiDeclLayMarker.cc`). The net tracer draws its highlights the same way.
- **Selection:** rebuild the markers on `LayoutView.on_selection_changed`. Shapes come from `view.each_object_selected()`, transformed into top-cell coordinates (`ObjectInstPath`), and instances are drawn by their shapes (or bounding box above a size limit).
- **Net:** shapes come from the net tracer, or from the LVS / `LayoutToNetlist` database when one is loaded. This is the Xschem cross-probe case: click a net in Xschem, and KLayout dims everything except that net. It depends on the cross-probe work, so build it after that exists.
- **Limits:** markers draw on top of everything, so the stacking order differs from normal drawing. Thousands of markers are fine; a large power net may be slow. Cap the count and say so in the status bar.

### 3. One setting and one switch

- The dimming amount is a one-time setting, like the black background: applied by `cadence_startup.lym` only while still at its default. Store it with `mw.set_config("layout-xl-dim", "70")`. First check that KLayout keeps unknown keys in `klayoutrc`; if it doesn't, use a small file in `~/.klayout/`.
- Commands, parsed in `commands.py` so the palette and voice get them: `dim layers`, `dim selection`, `dim net`, `dim off`, `dim <percent>` ("dim seventy").
- Palette rows carry the phrase to say, like the other commands.
- A key to toggle dimming off. Choose it together with WO-008's key table.
- Suggested defaults: raise `context-dimming` to about 70% for contrast on a black background. Leave child-context dimming off, but offer it in the palette ("dim subcells").

### Tests

- Grammar cases in `layout_xl/tests/test_commands.py`.
- With KLayout's window hidden (`klayout -z -e`, `QT_QPA_PLATFORM=offscreen`, isolated `KLAYOUT_HOME`, under a memory cap):
  - layer brightness is set and restored;
  - markers are created for a selection and cleared on `dim off`;
  - saving a session while dimmed writes the original colours.
- Visual check by the user on a real layout: these are judgements about looks.

### Effort

- Items 1 and 3: about a day.
- Item 2, the selection version: about a day.
- Item 2, the net version: after cross-probe exists.

## Phase 2: in KLayout's renderer, only if Phase 1 falls short

Do this if markers turn out too slow for big nets, or the stacking order or fill patterns look wrong.

- Add a **focus set** to `lay::LayoutViewBase`: a set of shapes or instance paths. When it isn't empty, draw everything at the context-dimmed brightness, then draw the focus shapes at full brightness in a second pass. That reuses the existing brightness calculation near `layLayoutViewBase.cc:4308`.
- Expose it through GSI (`LayoutView.set_focus`, `clear_focus`) so the kit's Phase 1 commands switch over without changing their interface.
- **Upstream: a feature request first, not code.** `AGENTS.md` (upstream, 2026-11) asks for feature requests that describe the problem and the workflow, not the implementation, and no pull request unless the maintainer asks for one. So: the user files an issue describing the dimming workflow (what they do in Virtuoso, why Descend's context dimming doesn't cover nets or the selection). Build the C++ only in our fork, or once upstream agrees. If it is built: follow the code conventions in `CLAUDE.md`, add a unit test in `src/laybasic/unit_tests/`.
- Effort: about a week, plus upstream review.
