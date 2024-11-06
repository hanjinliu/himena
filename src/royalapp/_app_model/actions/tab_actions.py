from typing import Any
from app_model.types import (
    KeyBindingRule,
    KeyCode,
    KeyMod,
)
from royalapp.consts import MenuId
from royalapp.widgets import MainWindow
from royalapp.types import (
    WindowState,
    WindowRect,
)
from royalapp._app_model._context import AppContext as _ctx
from royalapp._app_model.actions._registry import ACTIONS


@ACTIONS.append_from_fn(
    id="new-tab",
    title="New Tab",
    menus=[MenuId.TAB],
    keybindings=[KeyBindingRule(primary=KeyMod.CtrlCmd | KeyCode.KeyT)],
)
def new_tab(ui: MainWindow) -> None:
    """Create a new tab."""
    ui.add_tab()


@ACTIONS.append_from_fn(
    id="close-tab",
    title="Close Tab",
    enablement=_ctx.has_tabs,
    menus=[MenuId.TAB],
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
            f"Some windows in the tab are modified:\n{_modified_msg}\n"
            "Close without saving?"
        ):
            return None
    ui.tabs.pop(idx)


@ACTIONS.append_from_fn(
    id="merge-tabs",
    title="Merge Tabs ...",
    enablement=_ctx.has_tabs,
    menus=[MenuId.TAB],
)
def merge_tabs(ui: MainWindow) -> None:
    """Select tabs and merge them."""
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
