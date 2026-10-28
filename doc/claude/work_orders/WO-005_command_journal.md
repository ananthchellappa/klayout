# WO-005: Command journal ("CIW") — log every interaction as replayable script

| | |
|---|---|
| Status | **Plan**: not started, needs user review |
| Written | 2026-10-27 |
| Effort | Phase A ~1 day (Python macro), Phase B ~1–2 weeks (C++), Phase C open-ended |
| Touches | Phase A: `~/.klayout/pymacros/` only. Phase B/C: `src/laybasic`, `src/lay`, `src/db`, new `src/lay/lay/layJournal*` |

## Goal

The Virtuoso CIW + `CDS.log` experience:
1. Every user action appears in a dockable **Command Log** panel as a line of Python that would redo it.
2. The same lines go to a journal file (`~/.klayout/journal/klayout.log.py`, rotated like `CDS.log`, `CDS.log.1` …), so a crash or a weird state can be debugged afterwards.
3. Lines can be selected in the panel → **Copy** or **Save as macro** → edited in the Macro IDE → replayed. That is how users "build up scripts".
4. A one-line Python entry at the bottom of the panel (like typing SKILL into the CIW).
5. Verbosity levels, like Virtuoso's log filter: commands only / + settings / + view changes / + mouse points.

## What exists today (source-verified)

| Event source | Where | Visible to scripts today? |
|---|---|---|
| Menu/toolbar/shortcut commands | `MainWindow::menu_activated (symbol)` `src/lay/lay/layMainWindow.cc:4026`. A long `if` chain handles 49 symbols itself (`cm_open`, `cm_save`, `cm_undo`, …); the rest fall through to `PluginDeclaration::menu_activated` (line ~4132), then to the current view | **Partly.** A Python `pya.PluginFactory` gets `menu_activated(symbol)` callbacks, but only for the fall-through symbols, not the ones in the `if` chain |
| Replay of a command | `MainWindow.call_menu(symbol)` (`gsiDeclLayMainWindow.cc:834`) | yes |
| Config changes (grid, background, layer visibility options, …) | `Dispatcher::config_set` → `PluginFactory.configure(name, value)` callback | **Yes** (all of them); replay with `MainWindow.set_config` |
| Edits (create box, move, delete, flatten …) | Every edit is a `db::Manager` transaction with a human name (`manager ()->transaction (tr ("Create instance"))`, 16 sites in `src/edt/edt/`). The undo ops inside hold the exact shapes/instances inserted or erased | No event; the Undo List dialog shows the names only |
| View changes (zoom, pan, cell switch, layer show/hide) | `LayoutView` events: `viewport_changed_event`, `active_cellview_changed_event`, `layer_list_changed_event` (exposed as `on_viewport_changed` etc.) | yes |
| Mouse points | `ViewService` mouse handlers | No (only within your own plugin) |

So roughly a third can be done from Python today; full coverage needs small C++ hooks.

## Design

One central object, `lay::Journal` (singleton, lives in `lay`), with:
- `void record (Level level, const std::string &python_line, const std::string &comment = "")`
- `tl::event<int, const std::string &> entry_recorded_event`, exposed in GSI as `Journal.instance().on_entry`, so scripts (and the voice plugin, WO-007) can watch or add entries.
- A writer to the journal file (flush per line; rotation at startup; keep N=5).
- A dock widget `JournalPanel` (a `QPlainTextEdit` with syntax colouring, a level filter combo, a Python entry line wired to the existing macro console interpreter, buttons Copy / Save as macro / Clear).

Feeding it:
1. **Commands.** One line at the top of `MainWindow::menu_activated`: `Journal::instance ().record (Command, "mw.call_menu(\"" + symbol + "\")")`. This catches menus, toolbar and shortcuts alike, because they all funnel through here. Add a lookup from symbol to menu path/title for a readable comment: `# File > Save`.
2. **Settings.** Hook `Dispatcher::config_set` → `mw.set_config("grid-micron", "0.005")`. Debounce repeated writes of the same key; skip internal keys (window geometry, MRU lists) with a deny-list.
3. **Edits.** Hook `db::Manager::commit ()`. On commit, walk the ops of the just-closed transaction and translate the common ones:
   - shape insert/erase → `ly.cell(ci).shapes(ly.layer(68,20)).insert(pya.Box(…))`
   - instance insert/erase/replace
   - cell create/rename/delete
   - anything untranslated → a comment `# <transaction name> (not scriptable: <op type>)`, so the log is never silent.
   This is the part that makes the log *replayable*, not just descriptive. It's also the riskiest, since `db::Op` subclasses are templates (`db::layer_op<Sh, StableTag>`); do the translation in a visitor in `db`, unit-tested against the existing edit tests.
4. **View changes** (level 3): `view.zoom_box(pya.DBox(…))`, debounced 500 ms so a mouse-wheel zoom is one line.
5. **Mouse points** (level 4, off by default): `# click (12.345, 6.780) button=left`. Comment only; it's for debugging, not replay.

Generated lines use a fixed preamble (`mw = pya.MainWindow.instance(); view = mw.current_view(); ly = view.active_cellview().layout()`), which **Save as macro** writes at the top.

## Phases

**Phase A — Python prototype, no C++ (do first).** A `.lym` autorun macro: a `pya.PluginFactory` subclass logging `menu_activated` and `configure`, `on_viewport_changed` hooks, a `QDockWidget` with a text box. It shows what the UI feels like and which events matter, before touching C++. Known gap: the 49 commands in MainWindow's `if` chain (open, save, undo …) and all edits are invisible.

**Phase B — C++ core.** `lay::Journal`, the panel, hooks 1, 2, 4. Config keys `journal-level`, `journal-file`, `journal-keep`. Unit tests in `src/lay/unit_tests`. GSI declaration `gsiDeclLayJournal.cc` with doc strings.

**Phase C — replayable edits.** Hook 3, the op translator. Start with boxes/polygons/paths/texts and instances, which cover most layout work.

## Acceptance (Phase B)

- [ ] Open a GDS, zoom fit (F2), toggle a layer, change grid, save → each appears in the panel and in `klayout.log.py` as a Python line.
- [ ] Select lines → Save as macro → run it on a fresh session → same end state for commands and settings.
- [ ] Journal survives a `kill -9` (flushed per line).
- [ ] Level filter hides/shows view-change lines.
- [ ] No measurable slowdown when dragging/zooming (debounce works).
- [ ] `ut_runner` passes.

## Notes

- Upstream: worth opening a discussion on github.com/KLayout/klayout before Phase B. A journal hook in `menu_activated` and `commit` is small and generally useful, so it has a chance of being accepted, which saves carrying a fork.
- The voice plugin (WO-007) should write its recognised commands into this journal: "voice: zoom fit" → `mw.call_menu("cm_zoom_fit")`.
