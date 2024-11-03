from typing import Any
from app_model.types import (
    Action,
    KeyBindingRule,
    KeyCode,
    KeyMod,
)
from royalapp.consts import MenuId
from royalapp.widgets import MainWindow
from royalapp.types import (
    SubWindowState,
    WindowRect,
)
from royalapp._app_model._context import AppContext as _ctx


def new_tab(ui: MainWindow) -> None:
    ui.add_tab()


def close_current_tab(ui: MainWindow) -> None:
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


def merge_tabs(ui: MainWindow) -> None:
    if len(ui.tabs.names) < 2:
        return
    names = ui._backend_main_window._open_selection_dialog(
        "Select tab to merge", ui.tabs.names
    )
    if names is None:
        return
    all_window_info: list[tuple[Any, str, SubWindowState, WindowRect]] = []
    for name in names:
        for window in ui.tabs[name]:
            all_window_info.append(
                (window.widget, window.title, window.state, window.window_rect)
            )
    for name in names:
        del ui.tabs[name]
    new_tab = ui.add_tab(names[0])
    for widget, title, state, rect in all_window_info:
        new_window = new_tab.add_widget(widget, title=title)
        new_window.state = state
        if state is SubWindowState.NORMAL:
            new_window.window_rect = rect


ACTIONS = [
    Action(
        id="new-tab",
        title="New Tab",
        callback=new_tab,
        menus=[MenuId.TAB],
        keybindings=[KeyBindingRule(primary=KeyMod.CtrlCmd | KeyCode.KeyT)],
        icon_visible_in_menu=False,
    ),
    Action(
        id="close-tab",
        title="Close Tab",
        callback=close_current_tab,
        menus=[MenuId.TAB],
        enablement=_ctx.has_tabs,
        icon_visible_in_menu=False,
    ),
    Action(
        id="merge-tabs",
        title="Merge Tabs",
        callback=merge_tabs,
        menus=[MenuId.TAB],
        enablement=_ctx.has_tabs,
        icon_visible_in_menu=False,
    ),
]
