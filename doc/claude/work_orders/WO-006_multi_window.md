# WO-006: Multiple windows / multiple monitors in one KLayout process

| | |
|---|---|
| Status | **Plan**: not started, needs user review |
| Written | 2026-10-27 |
| Effort | Phase A ~1 week, Phase B ~1 week, Phase C optional |
| Touches | `src/lay/lay/layMainWindow.{h,cc}`, new `src/lay/lay/layViewWindow.{h,cc}`, `src/laybasic/laybasic/layAbstractMenu.cc`, session save/restore |

## Goal

Two layouts (or two views of one layout) visible at the same time, each in its own top-level window, each on its own monitor, in **one** process. Like Virtuoso, where every cellview is its own window and the CIW is shared. Multi-window and multi-monitor are the same feature: once a view is a top-level window, the window manager puts it on whatever screen you drag it to.

## Why it doesn't work today (source-verified)

- `MainWindow` is a hard singleton: the constructor throws "Only one instance of MainWindow may be created" (`layMainWindow.cc:202`).
- Layouts are `LayoutViewWidget`s stacked in a `ViewWidgetStack` (`layViewWidgetStack.h`) with only one raised at a time, selected by a `QTabBar` (`mp_tab_bar`). Tabs can't be torn off.
- The good news: each view already owns its side panels. `LayoutViewWidget::layer_control_frame ()`, `hierarchy_control_frame ()`, `libraries_frame ()`, `bookmarks_frame ()` and `editor_options_frame ()` (`layLayoutView_qt.h:668`) are per-view widgets that MainWindow puts into stacked docks (`mp_lp_stack->add_widget (view_widget->layer_control_frame ())`, line ~2695). A detached view can carry its own layer and cell panels with it.
- The undo manager (`m_manager`) is shared across views. That's fine and stays shared.

## Design: detachable "view windows"

Don't create a second `MainWindow`. Keep one MainWindow as the owner of all views (so all 128 `current_view ()` call sites and the 30 `MainWindow::instance ()` users keep working) and add `lay::ViewWindow`, a lightweight `QMainWindow` that can host one view.

- **Detach:** tab context menu "Move to New Window", plus dragging a tab out of the tab bar. The view's `LayoutViewWidget` is reparented from `ViewWidgetStack` into a `ViewWindow`, and its layer/cell frames go into that window's own docks. The view stays in MainWindow's view list with the same index, so scripts (`mw.view(i)`) are unaffected; its tab is shown as "detached" (italic, click = raise that window).
- **Re-attach:** closing the ViewWindow, or "Move Back to Main Window", reparents it back. Closing the *view* inside it closes the window.
- **Current view follows focus.** Install a handler on `QApplication::focusChanged` / `QEvent::WindowActivate`: when a ViewWindow becomes active, MainWindow sets that view as current (emitting `current_view_changed_event` as today). Menu commands, the journal (WO-005) and cross-probing (WO-003) then act on the window you last clicked in, which is what a Virtuoso user expects.
- **Menus and shortcuts.**
  - Phase A: ViewWindows have no menu bar; the shared menu lives in the main window. Shortcuts are the problem. No `setShortcutContext` call exists in `layAbstractMenu.cc`, so all QActions use Qt's default `Qt::WindowShortcut` and **won't fire while a ViewWindow has focus**. Fix by adding every menu QAction to each ViewWindow with `QWidget::addActions` (a QAction may belong to several widgets), or by switching them to `Qt::ApplicationShortcut`. Prefer `addActions`: ApplicationShortcut would also fire inside modal dialogs.
  - Phase B: give each ViewWindow its own menu bar and toolbar. `AbstractMenu::build (QMenuBar *, QToolBar *)` (`layAbstractMenu.h:720`) already builds from the shared action tree, so calling it once per window is plausible. Check that `menu_changed ()` (line ~4321) rebuilds all of them.
- **Dialogs** parented to MainWindow pop up on the main monitor. Parent per-view dialogs (layer properties, cell browser, net browser) to the view's window.
- **Session save/restore:** store, per view, whether it's detached plus its window geometry and screen (`QWidget::saveGeometry`). Restore on the same monitor if it still exists.
- **Synchronized Views** (existing config `cfg_synchronized_views`) should also apply across windows. Optional, but makes "same area of layout A and layout B side by side" one setting.

## Phases

**Phase A — detach/attach, shortcuts, focus = current view.** The core.
**Phase B — per-window menu bar and toolbar, dialog parenting, session restore.**
**Phase C (optional)** — "New Window on this cell" (a second view of the same layout, like Virtuoso's open-in-new-window), and floating docks remembered per monitor.

Interim workaround (no code, already in the FAQ): two processes, second one started with `-t` so it doesn't overwrite `klayoutrc`.

## Risks / things to check first

- `ViewWidgetStack::raise_widget`, `remove_widget` and the tab-bar ↔ view-index mapping (31 sites in `layMainWindow.cc`) assume every view is in the stack. Audit each before reparenting. Probably cleanest to leave an empty placeholder in the stack for a detached view, so indices don't shift.
- The navigator dock follows the current view; check it updates on window activation.
- WSLg / VirtuaWin: window placement on Windows desktops is handled by WSLg's RDP client, not by KLayout. Test on the user's setup early (see the note below).
- Upstream: multi-window is a big enough change to raise with the KLayout maintainer first (github.com/KLayout/klayout discussions). Check for an existing issue before starting.

## Acceptance (Phase A)

- [ ] Open two GDS files; detach the second; drag it to monitor 2. Both render and are pannable independently.
- [ ] Click into window 2, press F2 → window 2 zooms fit, window 1 doesn't.
- [ ] Layer panel in window 2 controls window 2's layers.
- [ ] Undo after an edit in window 2 undoes that edit.
- [ ] Close window 2 → view returns to a tab (or closes, per the chosen action); no crash, no leaked dock.
- [ ] `mw.views()` and `mw.current_view()` from the Macro console report correctly throughout.
- [ ] `ut_runner` passes.
