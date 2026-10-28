# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

KLayout is a C++/Qt layout viewer and editor for IC mask layouts (GDS2, OASIS, etc.), with Ruby and Python scripting, DRC/LVS engines, and a standalone Python module (`klayout` on PyPI).

## Build

qmake-based. `build.sh` (Linux/MSYS2/macOS) and `build.bat` (MSVC) wrap qmake + make. Ruby, Python and Qt are auto-detected.

```sh
./build.sh -j8                  # release: objects in build-release/, install in bin-release/
./build.sh -debug -j8           # debug: build-debug/, bin-debug/
./build.sh -without-qtbinding   # much faster build, no Qt classes for scripts
./build.sh -without-qt          # Qt-less core libs + Python module only
./build.sh -noruby / -nopython  # disable a scripting language
./build.sh -dry-run             # run qmake only
./build.sh -h                   # all options
```

Run the installed app from `bin-release/` (the `klayout` in `build-release/` is an intermediate copy). This checkout is built with `./build.sh -qmake qmake6 -rpath $HOME/dev/klayout/bin-release -j8`; without `-rpath` the binaries carry no RPATH and need `LD_LIBRARY_PATH=<bin dir>`. Changing only linker flags doesn't relink up-to-date targets: delete the `*.so*`/`*.ut`/executables in the build dir, then `make -j8 && make install`.

Incremental rebuild after the first run: `make -j8 install` inside `build-release/` (or `build-debug/`). `QMAKE_CCACHE=1` enables ccache.

The Python wheel is built separately through `setup.py` (`python setup.py bdist_wheel`, `pip install .`); it compiles the Qt-less core via distutils, not qmake.

macOS uses `build4mac.py` (see `macbuild/`), Makefile targets are macOS-only.

## Tests

The C++ test runner `ut_runner` loads every `*.ut` shared library sitting next to it (each module's `unit_tests/` dir builds one). With `build.sh` defaults these land in the **build** dir, not the bin dir (the README's "bin-release" is out of date):

```sh
cd build-release
export TESTTMP=testtmp   # scratch dir, created if needed
export TESTSRC=..        # repo root; test data is read from $TESTSRC/testdata
./ut_runner              # all tests
./ut_runner dbBoxTests   # tests matching a pattern; names are "<file basename>:<TEST name>", e.g. dbBoxTests:2
./ut_runner -l           # list tests
./ut_runner -c           # continue after failures
./ut_runner -i           # debug mode: on golden-file mismatch, prints au/actual paths and stops
./ut_runner -s           # include slow tests
./ut_runner -x=pattern   # exclude tests
```

Depending on the platform you may need `LD_LIBRARY_PATH=.:db_plugins:lay_plugins` (macOS: `DYLD_LIBRARY_PATH`). For headless runs (no X server) set `QT_QPA_PLATFORM=offscreen`.

Run a script in batch mode against the built app: `bin-release/klayout -zz -r script.py` (the extension selects the interpreter: `.py`, `.rb`, `.lym`).

- C++ tests use `TEST(name) { EXPECT_EQ (...); }` from `tlUnitTest.h`.
- Ruby tests (`testdata/ruby/*.rb`) and Python tests (`testdata/python/*.py`) are run *through* `ut_runner` — they're registered in `src/rba/unit_tests/rbaTests.cc` (`RUBYTEST(...)`) and `src/pya/unit_tests/pyaTests.cc`. A new script test must be added there.
- Python-module tests live in `testdata/pymod/` and run against the installed `klayout` package.
- Many tests compare output with golden ("au") files in `testdata/` via `db::compare_layouts` / `compare_netlist` (`src/db/db/dbTestSupport.h`). Behavior changes often require re-generating these golden files — commits titled "Re-referencing test data" do exactly that.
- `tl::testdata_private()` tests are skipped when the private test data repo is absent.

## Architecture

All sources are under `src/`, one directory per module; each is a shared library with `<mod>/<mod>/` (sources), `<mod>/unit_tests/`, and a `.pro` file. `src/klayout.pro` defines the module list and dependency order:

- `tl` — tool library: strings, streams, files, XML, expressions, threads, unit-test framework. No Qt dependency required.
- `gsi` — Generic Scripting Interface: the reflection layer that exposes C++ classes to Ruby and Python. **Script APIs are not written per language** — `gsiDecl*.cc` files (e.g. `src/db/db/gsiDeclDbBox.cc`) declare classes/methods once with `gsi::Class<>`, `gsi::method(...)` plus inline doc strings, and `rba` (Ruby) / `pya` (Python) bind them generically. The doc strings become the API reference documentation.
- `db` — layout database core: geometry primitives (`db::Box`, `db::Polygon`, …), `db::Layout`/`db::Cell`, shapes, `Region`/`Edges`/`EdgePairs`/`Texts` (flat and deep/hierarchical implementations), boolean ops, netlist extraction (`LayoutToNetlist`, `LayoutVsSchematic`), stream reader/writer framework.
- `rdb` (report/marker database), `pex`, `lib` (built-in libraries/PCells), `lym` (macro management).
- `laybasic` / `layview` / `layui` / `lay` — view, rendering and UI layers (Qt); `lay` is the main application framework; `klayout_main` is the executable.
- `ant` (rulers), `img` (images), `edt` (editing) — view plugins.
- `drc`, `lvs` — DRC/LVS engines implemented as Ruby DSLs on top of the `db` GSI API (only built with Ruby).
- `rba` / `pya` — Ruby/Python interpreters; `rbastub` / `pyastub` replace them when a language is disabled.
- `gsiqt` — generated Qt bindings for scripts (large, slow to build).
- `pymod` — the standalone Python package (`klayout.db`, `klayout.tl`, …).
- `buddies` — command-line tools (`strmcmp`, `strm2gds`, `strmxor`, …).
- `plugins/streamers/*` — file format readers/writers (gds2, oasis, lefdef, dxf, cif, magic, …), each split into `db_plugin` (format, no UI) and `lay_plugin` (UI options). `plugins/tools/*` — UI tools (xor, diff, net_tracer, …). These are loaded dynamically at runtime from `db_plugins/` and `lay_plugins/`.

Plugins and extension points register themselves through static `tl::RegisteredClass<>` instances; GSI classes register through static `gsi::Class` declarations.

Code conventions: namespaces match module (`db::`, `tl::`, `lay::`, `gsi::`); files prefixed with the module (`dbRegion.cc`, `tlString.h`); exported symbols use `<MOD>_PUBLIC` macros (`DB_PUBLIC`, `TL_PUBLIC`, …) from `<mod>Common.h`; space before parentheses in calls (`foo (x)`), two-space indent.

Documentation sources (HTML-like XML) are under `src/doc/`; `Changelog` records user-visible changes per release.
