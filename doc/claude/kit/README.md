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
- **Planned:** the rest of the Virtuoso Layout bindkeys, see `../work_orders/WO-008_virtuoso_bindkeys.md`.

Uninstall the startup package with `rm ~/.klayout/salt/layout_xl`.
