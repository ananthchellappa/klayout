# Layout-XL kit for KLayout (gf180mcuD)

```sh
doc/claude/kit/install.sh                       # PDK into ~/pdk + startup package into ~/.klayout/salt
source ~/pdk/gf180mcuD.env && klayout -e
```

- **PDK:** gf180mcuD KLayout tech, the `gf180mcu_klayoutapi` PCells, and DRC/LVS decks, about 2 MB. See `../gf180_pdk.md`.
- **Startup package** (`layout_xl/`), Cadence-style:
  - black background;
  - `f`: Zoom Fit, instead of F2;
  - Ctrl+F: toggles all hierarchy levels / top level only. It's Display → Toggle Hierarchy Display.

  Each setting is applied only while it's still at KLayout's default, so later changes in File → Setup stick.
- **Command palette: Ctrl+Shift+P** (Layout XL → Command Palette). One searchable list of the Layout XL commands (with the phrase that says each one) and every KLayout menu action (with its shortcut). Type words to filter, arrows to move, Enter to run; your last five come first.
  - Type a whole command ("up to metal 4 using 2x2 vias") and it is offered as the first row.
  - Features that need something installed are listed greyed, with what to install (voice, LVS's netlist, the gdsfactory via stack).
- **Commands:** short phrases that name an action, the same grammar typed or spoken (`layout_xl/python/layout_xl/commands.py`).

  | Say or type | Does |
  |---|---|
  | `run drc`, `launch lvs` | runs the gf180mcu PDK's DRC / LVS on the saved layout; results open in the marker browser |
  | `flip`, `flip vertical` | flips the selection: horizontally by default (Virtuoso MY), `vertical` for MX; `flip horizontal` also works |
  | `metal 2`, `switch to met3`, `poly`, `via 1` | makes that layer current, adding it to the layer list if missing |
  | `start wire min width`, `route on metal 3 width 0.5` | wire (path) tool at the layer's min width (M1 0.23, M2–M4 0.28, M5 0.44, poly 0.18) or the given width |
  | `up to metal 4 using 2x2 vias`, `via down`, `go up` | while drawing a wire: drops vias and continues on the new metal |
  | `fit`, `undo`, `redo`, `save` | as named |

  Numbers can be words ("two by two", "zero point five").
- **gf180mcu vias** (`gf180mcu_vias` library): Via1–Via4 for KLayout's wire tool. While drawing a wire, "O" (or the command above) drops a DRC-clean via array.
- **Voice:** tap **Ctrl+Shift** (press both, release, no other key) with the KLayout window focused, say a command from the table, stop talking. The result shows in the status bar. Also Layout XL → Voice Command.
  - One-time setup: `doc/claude/kit/voice/setup.sh` (Vosk + its small English model, 40 MB, offline, into `~/.local/share/layout-xl`). Without it, a tap just says so.
  - The recogniser knows only the command words; an utterance with any other word in it is rejected, not guessed at.
  - It runs in a helper process (`voice/server.py`); if that dies, the next tap restarts it. Log: `~/.local/share/layout-xl/voice-helper.log`.
  - `voice/listen.py --test` reads the commands aloud outside KLayout and scores them.
- **Planned:** the rest of the Virtuoso Layout bindkeys, see `../work_orders/WO-008_virtuoso_bindkeys.md`.

Uninstall the startup package with `rm ~/.klayout/salt/layout_xl`.
