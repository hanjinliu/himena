from typing import Any
from app_model.types import (
    KeyBindingRule,
    KeyCode,
    KeyMod,
)
from himena.consts import MenuId
from himena.widgets import MainWindow
from himena.types import (
    WindowState,
    WindowRect,
)
from himena._app_model._context import AppContext as _ctx
from himena._app_model.actions._registry import ACTIONS

WINDOW_GROUP = "00_window"


@ACTIONS.append_from_fn(
    id="new-tab",
    title="New Tab",
    menus=[MenuId.VIEW],
    keybindings=[KeyBindingRule(primary=KeyMod.CtrlCmd | KeyCode.KeyT)],
)
def new_tab(ui: MainWindow) -> None:
    """Create a new tab."""
    ui.add_tab()


@ACTIONS.append_from_fn(
    id="close-tab",
    title="Close Tab",
    enablement=_ctx.num_tabs > 0,
    menus=[MenuId.VIEW],
    keybindings=[KeyBindingRule(primary=KeyMod.CtrlCmd | KeyMod.Shift | KeyCode.KeyW)],
)
def close_current_tab(ui: MainWindow) -> None:
    """Close the current tab."""
    idx = ui._backend_main_window._current_tab_index()
    if idx is None:
        return
    win_modified = [win for win in ui.tabs[idx] if win.is_modified]
    if len(win_modified) > 0:
        _modified_msg = "\n".join([f"- {win.title}" for win in win_modified])
        if not ui.exec_confirmation_dialog(
            f"Some windows in this tab are not saved yet:\n{_modified_msg}\n"
            "Close the tab without saving?"
        ):
            return None
    ui.tabs.pop(idx)


@ACTIONS.append_from_fn(
    id="goto-last-tab",
    title="Go to Last Tab",
    enablement=_ctx.num_tabs > 1,
    menus=[MenuId.VIEW],
    keybindings=[KeyBindingRule(primary=KeyMod.CtrlCmd | KeyCode.Tab)],
    recording=False,
)
def goto_last_tab(ui: MainWindow) -> None:
    """Go to the last tab."""
    if (idx := ui._history_tab.get_from_last(2)) is not None:
        ui.tabs.current_index = idx


@ACTIONS.append_from_fn(
    id="merge-tabs",
    title="Merge Tabs ...",
    enablement=_ctx.num_tabs > 1,
    menus=[MenuId.VIEW],
)
def merge_tabs(ui: MainWindow) -> None:
    """Select tabs and merge them."""
    # TODO: use `move_window`
    if len(ui.tabs) < 2:
        return
    names = ui._backend_main_window._open_selection_dialog(
        "Selects tab to merge", ui.tabs.names
    )
    if names is None:
        return
    all_window_info: list[tuple[Any, str, WindowState, WindowRect]] = []
    for name in names:
        for window in ui.tabs[name]:
            all_window_info.append(
                (window.widget, window.title, window.state, window.rect)
            )
    for name in names:
        del ui.tabs[name]
    new_tab = ui.add_tab(names[0])
    for widget, title, state, rect in all_window_info:
        new_window = new_tab.add_widget(widget, title=title)
        new_window.state = state
        if state is WindowState.NORMAL:
            new_window.rect = rect


@ACTIONS.append_from_fn(
    id="minimize-other-windows",
    title="Minimize other windows",
    menus=[
        {"id": MenuId.VIEW, "group": WINDOW_GROUP},
    ],
    enablement=_ctx.num_sub_windows > 1,
)
def minimize_others(ui: MainWindow):
    """Minimize all sub-windows except the current one."""
    if area := ui.tabs.current():
        cur_window = area.current()
        for window in area:
            if cur_window is window:
                continue
            window.state = WindowState.MIN


@ACTIONS.append_from_fn(
    id="show-all-windows",
    title="Show all windows",
    menus=[{"id": MenuId.VIEW, "group": WINDOW_GROUP}],
    enablement=_ctx.num_sub_windows > 0,
)
def show_all_windows(ui: MainWindow):
    """Show all sub-windows in the current tab."""
    if area := ui.tabs.current():
        for window in area:
            if window.state is WindowState.MIN:
                window.state = WindowState.NORMAL


@ACTIONS.append_from_fn(
    id="tile-windows",
    title="Tile windows",
    enablement=_ctx.num_sub_windows > 1,
    menus=[{"id": MenuId.VIEW, "group": WINDOW_GROUP}],
)
def tile_windows(ui: MainWindow) -> None:
    """Tile all the windows."""
    if area := ui.tabs.current():
        area.tile_windows()


@ACTIONS.append_from_fn(
    id="close-all-windows",
    title="Close all windows in tab",
    menus=[{"id": MenuId.VIEW, "group": WINDOW_GROUP}],
    enablement=_ctx.num_sub_windows > 0,
)
def close_all_windows_in_tab(ui: MainWindow) -> None:
    """Close all sub-windows in the current tab."""
    if area := ui.tabs.current():
        win_modified = [win for win in area if win.is_modified]
        if len(win_modified) > 0 and ui._instructions.confirm:
            _modified_msg = "\n".join([f"- {win.title}" for win in win_modified])
            if not ui.exec_confirmation_dialog(
                f"Some windows are modified:\n{_modified_msg}\nClose without saving?"
            ):
                return None
        area.clear()
    return None
