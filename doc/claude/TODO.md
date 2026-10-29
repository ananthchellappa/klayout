# To do / open questions

Short findings so far. None of these has been started.

## Black background, Cadence-style, set once
- GUI: File → Setup → Display → Background. Settings persist automatically in `~/.klayout/klayoutrc` (XML), so it's a one-time step.
- Config key: `background-color` (`src/laybasic/laybasic/laybasicConfig.h:53`).
- **To do:** keep it in a version-controlled init file instead. Use an autorun Python macro, e.g. `~/.klayout/pymacros/cadence_init.lym`, that calls `pya.MainWindow.instance().set_config("background-color", "#000000")`. The same file can set grid, colors and other options.

## Custom keyboard shortcuts in an init file
- GUI: File → Setup → Application → Customize Menu. Saved as config key `key-bindings` in `klayoutrc`.
- Script API: `MainWindow.set_key_bindings({"<menu path>": "Ctrl+A", ...})`, plus `get_key_bindings` and `get_default_key_bindings` (`src/lay/lay/gsiDeclLayMainWindow.cc:395-408`). Any menu action can be bound, including our own macros.
- **To do:** a `cadence_keys` macro that applies a Virtuoso-style keymap at startup. That gives one file under version control, like the Xschem and Virtuoso init files. Map out which Virtuoso bindkeys have KLayout equivalents.

## Why the checkout is ~2 GB after building
- `build-release/`: 1.2 GB. About 750 MB of it is object files, and `gsiqt` (the generated Qt bindings) alone is 470 MB. This is safe to delete, at the cost of incremental rebuilds.
- `.git`: 356 MB. `bin-release/`: 209 MB (the actual install). `src`: 157 MB. `testdata`: 79 MB.
- ccache lives outside the repo (`~/.cache/ccache`).
- **To do (optional):** build with `-without-qtbinding` to save ~0.5 GB and a lot of build time. But that kills `pya.QTcpServer`, which the cross-probe plan uses, so not recommended.

## Parasitic extraction (Magic has R+C; what about KLayout?)
- Built in: the `pex` module (`src/pex/`, since 0.30.2) does **resistance** extraction only: `pex.RExtractor` (square-counting and triangulation), `RNetExtractor`, `RNetwork`.
- External: **KLayout-PEX (`kpex`)** from IIC-JKU (AUR package `klayout-pex`, 0.6.8, Oct 2026). It does R and C extraction on top of KLayout, with FasterCap, FastCap2 or Magic as optional backends. Its sky130 support and accuracy are **not yet verified**.
- **To do:** evaluate kpex on sky130 against Magic `ext2spice`/`extresist` on the inverter.

## PDK
- **gf180mcuD is the working PDK** (2026-10-29): installed in `~/pdk` and verified. See `gf180_pdk.md` for results and quirks.
- sky130A is the fallback: `sky130_pdk_plan.md`, WO-001 (not run).

## UI/UX work orders (plans, not started)
- `work_orders/WO-005_command_journal.md`: CIW-style command log and journal file, replayable as Python.
- `work_orders/WO-006_multi_window.md`: detach layout tabs into their own windows (multi-monitor) in one process.
- `work_orders/WO-007_voice_commands.md`: voice for forms and precise geometry (Groups 1–2): preview card + ghost before anything runs, one undo step per command, local and cloud speech-to-text with failover, deterministic grammar parser.
