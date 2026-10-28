# Xschem ↔ KLayout cross-probing: toward an open "Layout XL"

Status: analysis and plan only, no code yet (2026-10-26).
- KLayout facts were checked against `master@7eb9a25b4`.
- Xschem facts come from the `xschem-private-da` session's survey of `~/private/xschem-private`. Its paths are relative to that repo.

## Goal

Get an early version of a schematic-driven layout (SDL) flow, in the style of Cadence Virtuoso Layout XL, running with Xschem and KLayout:

1. **Cross-probe**: select or highlight a net or instance in one tool, and the other tool selects, highlights and zooms to the same object.
2. **Generate from source**: place PDK PCells in KLayout from the Xschem schematic, with W/L/nf/m taken from the symbols.
3. **Connectivity awareness**: flylines/rats-nest for unrouted connections, and an LVS check that schematic and layout still match.

There is no existing open-source tool that does this (web search, Oct 2026). The closest prior art:
- **klink/klive** (`klayout-klink` on PyPI): a KLayout salt plugin with a TCP server on 127.0.0.1:8082/8765 that pushes GDS into a running KLayout. It's a good model for the IPC half.
- **mole99/klayout-sky130-inverter**: a manual Xschem + KLayout DRC/LVS flow driven by a Makefile.

## What each side already offers

### KLayout (no source changes needed for phases 0–2)

| Need | KLayout facility | Where |
|---|---|---|
| Run our code at startup | autorun `.lym`/`.pym` in `~/.klayout/pymacros` or a salt package | `src/lay/lay/layApplication.cc:545` (`init_app`), `src/lym/lym/lymMacro.cc` |
| Listen for commands | **none built in**. Use `pya.QTcpServer`/`QLocalServer` from gsiqt in an autorun macro | `src/gsiqt/qt6/QtNetwork/gsiDeclQTcpServer.cc` (needs a Qt-bindings build) |
| Threading | the GIL is **never released** by pya, so background Python threads starve and asyncio blocks the GUI. Use Qt signals or a `QTimer` | `src/pya/pya/pya.cc` (no `PyEval_SaveThread`) |
| Schematic netlist in | `Netlist.read(file, NetlistSpiceReader())` | `src/db/db/gsiDeclDbNetlist.cc:2274` |
| Layout netlist + net shapes | `LayoutToNetlist`: `probe_net`, `shapes_of_net`, `build_net`, `internal_layout` | `src/db/db/gsiDeclDbLayoutToNetlist.cc:982,1004,1094` |
| Schematic ↔ layout object mapping | `LayoutVsSchematic.xref` → `NetlistCrossReference.other_net_for/other_device_for/other_subcircuit_for` | `src/db/db/gsiDeclDbNetlistCrossReference.cc:534-560` |
| Highlight + zoom a net or device | `view.netlist_browser().current_path = NetlistObjectsPath…` (the browser must be open) | `src/layui/layui/gsiDeclLayNetlistBrowserDialog.cc:370` |
| Browser events | `on_selection_changed`, `on_probe(first, second)` | same file, :338-342 |
| Free-form highlight | `lay.Marker(view)`, `set_polygon/set_box`, colors, halo | `src/laybasic/laybasic/gsiDeclLayMarker.cc` |
| Layout selection ↔ script | `view.object_selection`, `select_object`, event `on_selection_changed` | `src/edt/edt/gsiDeclEdt.cc:447-489`, `gsiDeclLayLayoutViewBase.cc:1804` |
| Zoom | `view.zoom_box(DBox)`, `zoom_fit_sel` | `gsiDeclLayLayoutViewBase.cc:919-924` |
| Place PCells | `layout.create_cell(pcell, lib, params)` + `cell.insert(CellInstArray)` | `src/db/db/gsiDeclDbLayout.cc:1732` |
| Tag instances with schematic identity | `Instance.set_property(key, value)` (persisted in GDS with integer keys, or OASIS with string keys) | `src/db/db/gsiDeclDbCell.cc:4236` |
| Custom mouse tools, menus, docks | `lay.PluginFactory`/`lay.Plugin`, `MainWindow.menu`, `addDockWidget` | `src/layview/layview/gsiDeclLayPluginFactory.cc`, `src/lay/lay/gsiDeclLayMainWindow.cc` |
| Net tracing without LVS | `NetTracer.trace(...)` (database side scriptable; dialog is not) | `src/plugins/tools/net_tracer/db_plugin/gsiDeclDbNetTracer.cc` |

### Xschem

| Need | Xschem facility |
|---|---|
| Accept commands | Tcl TCP server, **off by default**. Enable it with `--tcp_port <n>` / `xschem_listen_port` / `setup_tcp_xschem <port>` (`src/xschem.tcl`). It handles one request per connection: Tcl text is eval'd and the result written back with no error flag, so wrap requests as `list [catch {...} r] $r`. It binds all interfaces with no auth, so restrict it to `127.0.0.1`. |
| Select/highlight by hierarchical path | Tcl procs `select_inst {x1.x2.m4}`, `probe_net {x1.x2.net5}` (retries `#netN`), `descend_hierarchy`. Also `xschem hilight_netname`, `hilight_instname`, `zoom_selected`, `unhilight_all`. |
| Read the selection | `xschem selected_set` (instances), `selected_wire` (net labels), `get sch_path` (`.x1.x2.`) |
| Selection events | **none**. The cheapest hook is wrapping the Tcl proc `infowindow`, which non-fast selects call from `src/select.c`. A canvas `bind +` on button release is the alternative. |
| Export for layout | per level: `instance_list`, `getprop instance`, `translate <inst> {@W @L @nf}`, `instance_nodemap`, `pinlist`. Full hierarchy: the `traversal`/`hier_traversal` templates. The best single artifact today is the **LVS netlist** (`lvs_netlist=1`, uses each symbol's `lvs_format`). |
| PDK params | sky130 `W L nf mult`; gf180 `L W nf m`; IHP `w l ng m`. Names differ, so a **per-PDK mapping table** is needed. |

### Naming rules to reconcile

| Concept | Xschem | KLayout LVS |
|---|---|---|
| Hierarchy separator | `.` (`x1.x2.net5`). A flat netlist uses `_` | `NetlistObjectPath` = root circuit + list of subcircuits. Strings are built from `expanded_name`s |
| Auto-named net | `#net5` internally, printed `net5` in SPICE | extracted nets without labels are `$<id>`. Match only through the LVS xref |
| Buses | `A[3:0]` → `A[3],A[2],…`. `bus_replacement_char` may rewrite the brackets | names as read from SPICE |
| Persistent object ID | none (ids are per session) | none, unless we stamp instance properties |

**Rule:** the hierarchical name path is the identity. Cross-probing between a schematic name and layout geometry always goes through either (a) an LVS cross-reference, or (b) a property we stamp on generated instances.

## Proposed architecture

```
 Xschem (Tcl)                                     KLayout (Python autorun macro "sdl")
 ┌───────────────────────────┐   probe msgs   ┌─────────────────────────────────────┐
 │ hook: infowindow wrapper  │ ─────────────► │ QTcpServer 127.0.0.1:<kport>        │
 │   → sends JSON line       │  (TCP, JSON)   │   dispatch on GUI thread            │
 │                           │                │ name map:                           │
 │ tcp server 127.0.0.1:<xp> │ ◄───────────── │   LVS xref  |  instance properties  │
 │   select_inst / probe_net │  Tcl strings   │ highlight: netlist_browser.path or  │
 │   + zoom_selected         │                │   lay.Marker; select_object; zoom   │
 └───────────────────────────┘                │ hooks: on_selection_changed,        │
         │ layout_export (JSON)               │   netlist_browser.on_probe          │
         └──────────────────────────────────► │ generator: PCells + set_property    │
                                              └─────────────────────────────────────┘
```

- **KLayout side** ships as a salt package (`~/.klayout/salt/xschem_sdl/`) with an autorun `.lym`, so it needs no C++ changes. Commands are newline-delimited JSON: `{"cmd":"probe","kind":"net","path":"x1.x2.net5"}`.
- **Xschem side** is ~100 lines of Tcl in xschemrc or a sourced file:
  - a loopback listener;
  - an `infowindow` wrapper that sends the current selection plus `sch_path`;
  - a `layout_export` proc.
- **Both directions are loopback only.** The Xschem server must be bound to `127.0.0.1`.

## Phased plan

**Phase 0: LVS-backed cross-probe on an existing layout.** This proves the loop with zero generation.
1. In Xschem, `lvs_netlist=1` writes the reference netlist.
2. A KLayout LVS run (PDK LVS deck, e.g. sky130/gf180 KLayout LVS) produces a `.lvsdb`, which is loaded into the netlist browser.
3. Schematic → layout: the probe path goes through `xref.other_net_for`, then `netlist_browser.current_path = …` highlights and zooms.
4. Layout → schematic: `netlist_browser.on_selection_changed`/`on_probe`, then the schematic-side path is sent to Xschem as `probe_net {…}` / `select_inst {…}`.
5. Exit criterion: clicking a net in either tool highlights it in the other, for the sky130 inverter example.

**Phase 1: instance cross-probe without LVS.**
- Stamp each placed instance with property `"xschem_path" = "x1.x2.m4"`. Use OASIS for string keys; with GDS, use an integer key and a fixed-key convention.
- `on_selection_changed` reads the property and sends `select_inst`. The reverse direction looks up instances by property and calls `select_object` + `zoom_fit_sel`.

**Phase 2: schematic-driven generation.**
- Xschem `layout_export` produces JSON: instances with hierarchical path, symbol, evaluated params and pin→net.
- The KLayout generator does three things:
  - places PDK PCells via a per-PDK param map;
  - stamps the properties from phase 1;
  - draws **flylines** as `lay.Marker` edges between pin shapes of the same net, refreshed on edit.
- ECO/update: diff the new export against the stamped instances, then add, delete or re-parameterize instances while leaving placement alone.

**Phase 3: polish, and native code if needed.**
- Possible additions: a dock panel listing nets/instances, a "show unrouted" check, incremental LVS.
- If Python marker performance or the netlist browser's "must be open" limitation hurts, move the hot path into a C++ `lay::Plugin` in `src/plugins/tools/`. The architecture stays the same.

## Risks and open questions

- **Builds without Qt bindings** (`-without-qtbinding`, the pip `klayout` module) lack `QTcpServer`. The fallback is polling a non-blocking Python `socket` from a `QTimer`, which needs QtCore bindings anyway, or a small C++ plugin.
- **Netlist browser highlights vanish when the browser is closed.** For always-on highlighting, draw our own Markers from `shapes_of_net`. Those shapes are in the LVS *internal* layout, so map them back with `cell_mapping_into`/transforms.
- **Device naming across the flow.** The SPICE prefix differs from the instance name (e.g. sky130 MOS symbols emit `X…` subckt calls via `spiceprefix`), and KLayout's SPICE reader may produce different device or subcircuit names. Verify on the first real design.
- **Per-PDK parameter names** (W/L/nf/m vs w/l/ng/m) and PCell library names must come from one mapping table.
- **Security:** the Xschem TCP server evaluates arbitrary Tcl. Never expose it beyond loopback (relevant for AWS/Docker setups).
