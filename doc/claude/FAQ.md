# KLayout FAQ (from the Layout-XL-with-Xschem project)

The answers were checked against the KLayout 0.30.12 source tree or a real build in October 2026. The blog version is `doc/claude/blog_klayout_faq.html`. It is generated: edit `doc/claude/blog/faq_src.html` (plain HTML with classes), then run `python3 scripts/style_blog.py blog/faq_src.html blog_klayout_faq.html` from `doc/claude/`. That inlines all styles, because Blogger themes override `<style>` blocks. The palette is tuned for xschem.blogspot.com's dark "Awesome Inc." theme (post panel `#141414`); change it at the top of `style_blog.py` for a light theme. **This file is the source of truth. Update it first, then the blog source.**

## Building and the repo

### 1. What do I need to install to build KLayout?
Ubuntu with Qt 6:
```sh
sudo apt install build-essential git ccache python3-dev ruby-dev zlib1g-dev \
  qt6-base-dev qt6-tools-dev qt6-5compat-dev qt6-svg-dev qt6-multimedia-dev \
  libgit2-dev libcurl4-openssl-dev
./build.sh -qmake qmake6 -rpath $HOME/dev/klayout/bin-release -j8
```
- `qt6-5compat-dev` is easy to miss.
- Ruby is required, because DRC and LVS are Ruby DSLs.
- Ubuntu has no plain `qmake`, so name it.
- On 16 GB of RAM, use `-j8`; the generated Qt bindings are memory-hungry. `QMAKE_CCACHE=1` speeds up rebuilds.

### 2. How big is the code base?
About 3.2 M lines of C++, of which about 2.2 M are generated Qt bindings (`src/gsiqt`). The hand-written code is about 1 M lines:
- `db`: about 255k
- `laybasic`: about 196k
- `plugins`: about 144k
- C++ unit tests: about 128k
- DRC/LVS DSL: about 18k lines of Ruby

The core idea is GSI: one `gsiDecl*.cc` declaration produces the Ruby API, the Python API and the docs.

### 3. Should I run Doxygen?
Not at first. There's no Doxyfile, and the script API is already documented in Help → Class Index. If you run it later, use only `src/{tl,gsi,db,laybasic,layui,lay,edt}` and exclude `src/gsiqt`.

### 4. "error while loading shared libraries: libklayout_tl.so.0"
- Run `bin-release/klayout`, not `build-release/klayout`.
- Build with `-rpath <bin dir>`. Adding it later doesn't relink up-to-date targets: delete `*.so*`, `*.ut` and the executables in the build dir, then `make -j8 && make install`.
- Unit tests run from `build-release`:
  ```sh
  TESTTMP=testtmp TESTSRC=.. LD_LIBRARY_PATH=. ./ut_runner
  ```

### 5. Why is the checkout 2 GB after building?
| Part | Size |
|---|---|
| `build-release` | 1.2 GB (objects about 750 MB, `gsiqt` 470 MB) |
| `.git` | 356 MB |
| `bin-release` | 209 MB |
| `src` | 157 MB |
| `testdata` | 79 MB |

`-without-qtbinding` saves about 0.5 GB, but removes the Qt classes (such as `QTcpServer`) from scripts.

## Setup and customisation

### 6. Black background like Virtuoso, set once?
- **GUI:** File → Setup → Display → Background. The setting is saved to `~/.klayout/klayoutrc`.
- **Init file:** use `~/.klayout/pymacros/my_init.pym`:
  ```python
  pya.MainWindow.instance().set_config("background-color", "#000000")
  ```

### 7. Custom keyboard shortcuts in an init file?
- **GUI:** File → Setup → Application → Customize Menu.
- **Script:** `MainWindow.set_key_bindings({"zoom_menu.zoom_fit": "F"})`. Any menu path can be bound, including your own macros. `get_default_key_bindings()` lists them all.

### 8. R and C parasitic extraction like Magic?
- **Built in:** `pex` (0.30.2+) does R only (`RExtractor`, `RNetExtractor`).
- **Add-on:** for R and C, use **kpex** (KLayout-PEX, IIC-JKU), with FasterCap, FastCap2 or Magic backends. It hasn't yet been compared with Magic.

## Analog flow and sky130

### 9. Is there an Xschem ↔ KLayout cross-probe?
Not that I found. klink/klive pushes layouts into KLayout over TCP, and example projects pair the two tools through a Makefile LVS flow. Both tools have the pieces:
- **Xschem:** Tcl TCP server; `select_inst` and `probe_net` take hierarchical paths.
- **KLayout:** LVS cross-reference, scriptable netlist browser, selection events, `QTcpServer`.

Gotchas:
- KLayout's Python never releases the GIL, so use Qt timers and signals.
- Xschem's server evaluates any Tcl it receives, so keep it on localhost.

### 10. What does sky130 layout in KLayout need if I already use sky130 in Xschem?
- **Install:** ciel's `common` (6.6 MB) plus `sky130_fd_pr` (14.2 MB). That's about 105 MB on disk, and it contains the tech files, DRC/LVS decks and PCells.
- **The PCells need patching.** They're the Mabrains/gdsfactory PCells, library name `skywater130`. Unpatched with current gdsfactory 9 / kfactory 3, every PCell quietly produces an **empty cell**. IIC-OSIC-TOOLS' install script carries the fixes. Install them at its pinned open_pdks commit `1689ac3f`, in a venv pinned to gdsfactory 9.51.0 / kfactory 3.0.4.
- **Point KLayout at the venv:** its Python ignores `PYTHONPATH`. Use `KLAYOUT_PYTHONPATH`.
- **Verified on our build:**
  - PCells generate;
  - full DRC (`sky130A_mr.drc` with `feol/beol/offgrid=true`) shows 0 violations; the default `.lydrc` has FEOL off;
  - LVS against an Xschem netlist matches, with `-rd convert_subckts=true -rd scale=true`.
- **Mapping from Xschem:**
  - `w = W/nf`, since the PCell `w` is per finger;
  - pass `gate_con_pos` and `bulk` explicitly;
  - multi-finger PCells don't strap their fingers.

## UI/UX compared with Cadence Virtuoso

### 11. Is there a CIW that logs commands?
No.
- **What exists:**
  - Macro Development → **Console**: an interactive Python/Ruby prompt, like typing SKILL into the CIW;
  - File → **Log Viewer**: messages, warnings and errors; `-d <level>` adds detail.
- **What doesn't:** GUI actions are never echoed as replayable commands. There's no CDS.log-style journal and no macro recorder. A CIW-like dock that logs actions as script calls is buildable, but it doesn't exist today.

### 12. Is there a Library Manager?
Only a minimal one.
- **What exists:**
  - a **Libraries** panel that lists registered libraries and their cells and PCells, which you drag into the layout;
  - a **Cells** panel for the hierarchy within the open file.
- **What doesn't:** there's no library/cell/view browser, no `cds.lib`, no categories, and no copy/rename/delete or check-in. In KLayout one layout file = one library.

### 13. Two layouts in two windows on two monitors?
Not from one process. KLayout allows a single main window (`layMainWindow.cc`), and layouts open as tabs that can't be torn off. The side panels can be floated to another monitor.
- **Workaround: two processes.** Settings are written to `klayoutrc` on exit, and the last one closed wins, so start the second with `-t` (don't write the config).
- **In one window:**
  - overlay two layouts in one tab;
  - the XOR and Diff tools;
  - Display → Synchronized Views, which keeps the zoom when switching tabs.

### 14. What is the command language? Scripting?
- **Python and Ruby, both built in.** There's no single native language like SKILL. Both get the same complete API (database, views, menus, even Qt widgets), documented in Help → Class Index.
- **Macro IDE:** an editor and debugger.
- **Init files:** `.pym`/`.rbm` files in `~/.klayout/pymacros` and `macros` autorun, like `.cdsinit`.
- **Batch:** `klayout -b -r script.py`.
- **DRC and LVS** are Ruby DSLs.
- **The gap compared with SKILL** is visibility: the API is complete, but the GUI doesn't show you the command behind each action.

### 15. Zoom fit shortcut (Virtuoso: `f`)?
**F2**. Shift+F2 fits the selection; Ctrl++ and Ctrl+- zoom in and out. To get Virtuoso's `f`:
```python
set_key_bindings({"zoom_menu.zoom_fit": "F"})
```
